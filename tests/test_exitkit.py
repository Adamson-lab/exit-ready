import json, os, re, tempfile, unittest
import xml.dom.minidom as minidom

from exitkit import assess, plan as planmod, report, scoring
from exitkit.catalog import CATALOG, CATEGORY_PHASE, DATA_CATEGORIES
from exitkit.cli import analyse, main
from exitkit.model import Estate, Resource
from exitkit.scanner import _body, load_estate, scan_terraform

NW, PE = "examples/northwind-bank", "examples/portable-estate"


def est(*rs, calls=None, settings=None):
    return Estate("t", list(rs), calls or {}, 0, settings or {})


def res(rtype, tier="tier2", data=0.0, monthly=100.0):
    return Resource(f"{rtype}.x", rtype, "x", "aws", tier, data, monthly, False)


class Catalog(unittest.TestCase):
    def test_every_entry_valid(self):
        for k, v in CATALOG.items():
            self.assertIn(v["class"], (1, 2, 3, 4, 5), k)
            self.assertIn(v["category"], CATEGORY_PHASE, k)
            self.assertTrue(v["target"] and v["playbook"], k)
        self.assertTrue(DATA_CATEGORIES <= set(CATEGORY_PHASE))


class Scanner(unittest.TestCase):
    def test_brace_matching_ignores_braces_in_strings(self):
        t = 'x { a = "}" tags = { k = "v" } } trailing'
        self.assertEqual(_body(t, 4).strip(), 'a = "}" tags = { k = "v" }')

    def test_northwind_scan(self):
        r = scan_terraform(NW)
        self.assertEqual(len(r), 32)
        led = next(x for x in r if x.address == "aws_dynamodb_table.ledger")
        self.assertEqual((led.tier, led.data_gb, led.monthly_usd), ("tier1", 40000.0, 22000.0))
        lam = next(x for x in r if x.address == "aws_lambda_function.notify")
        self.assertIn("aws_iam_role.lambda_exec", lam.deps)

    def test_code_coupling_counted(self):
        e = load_estate(NW)
        self.assertGreaterEqual(e.code_calls["aws_dynamodb_table"], 38)

    def test_unknown_type_flagged_conservative(self):
        d = tempfile.mkdtemp()
        open(os.path.join(d, "m.tf"), "w").write('resource "aws_quantum_thing" "q" {\n}\n')
        e = load_estate(d)
        self.assertFalse(e.resources[0].catalogued)
        self.assertEqual(scoring.lockin(e)["uncatalogued"], ["aws_quantum_thing.q"])
        self.assertGreaterEqual(scoring.lockin(e)["overall"], 75)


class Scoring(unittest.TestCase):
    def test_proprietary_scores_higher_than_portable(self):
        self.assertGreater(scoring.lockin(est(res("aws_dynamodb_table")))["overall"],
                           scoring.lockin(est(res("aws_db_instance")))["overall"])

    def test_data_gravity_and_tier_raise_impact(self):
        small = scoring.lockin(est(res("aws_dynamodb_table", data=1)))["hotspots"][0]["impact"]
        big = scoring.lockin(est(res("aws_dynamodb_table", data=100000)))["hotspots"][0]["impact"]
        t1 = scoring.lockin(est(res("aws_dynamodb_table", "tier1")))["hotspots"][0]["impact"]
        t3 = scoring.lockin(est(res("aws_dynamodb_table", "tier3")))["hotspots"][0]["impact"]
        self.assertGreater(big, small); self.assertGreater(t1, t3)

    def test_code_coupling_raises_score(self):
        base = scoring.lockin(est(res("aws_sqs_queue")))["overall"]
        coupled = scoring.lockin(est(res("aws_sqs_queue"), calls={"aws_sqs_queue": 90}))["overall"]
        self.assertGreater(coupled, base)

    def test_examples_ordered(self):
        self.assertGreater(scoring.lockin(load_estate(NW))["overall"], scoring.lockin(load_estate(PE))["overall"] + 25)


class Plan(unittest.TestCase):
    def test_more_people_never_slower(self):
        e = load_estate(NW); cfg = planmod.settings(e); items = planmod.work_items(e, cfg)
        d = [planmod.schedule(items, t, cfg)[1] for t in (5, 20, 80)]
        self.assertGreaterEqual(d[0], d[1]); self.assertGreaterEqual(d[1], d[2])

    def test_min_team_meets_window(self):
        e = load_estate(NW); p = planmod.build(e)
        s = p["scenarios"]["stressed"]
        self.assertFalse(s["feasible"]); self.assertIsNotNone(s["min_team"])
        cfg = p["cfg"]
        self.assertLessEqual(planmod.schedule(p["items"], s["min_team"], cfg, s["min_phase_days"])[1], s["window_days"])

    def test_impossible_window_returns_none(self):
        e = est(res("aws_dynamodb_table", "tier1", data=5_000_000))   # 5 PB over one shared link
        p = planmod.build(e, window=30)
        self.assertIsNone(p["scenarios"]["stressed"]["min_team"])

    def test_egress_waiver(self):
        e = est(res("aws_s3_bucket", data=1000), settings={"egress_waived": True})
        self.assertEqual(planmod.build(e)["scenarios"]["planned"]["cost"]["egress"], 0)
        e2 = est(res("aws_s3_bucket", data=1000))
        self.assertEqual(planmod.build(e2)["scenarios"]["planned"]["cost"]["egress"], 90)

    def test_phases_ordered_data_before_compute(self):
        p = planmod.build(load_estate(NW))
        ph = {i["address"]: i["phase"] for i in p["items"]}
        self.assertLess(ph["aws_kms_key.data"], ph["aws_dynamodb_table.ledger"])
        self.assertLess(ph["aws_dynamodb_table.ledger"], ph["aws_eks_cluster.payments"])
        self.assertLess(ph["aws_eks_cluster.payments"], ph["aws_route53_zone.bank"])


class Assess(unittest.TestCase):
    def test_bounds(self):
        with self.assertRaises(ValueError): assess.readiness({"GOV-1": 4})

    def test_empty_answers_all_gates_open(self):
        r = assess.readiness({})
        self.assertEqual(r["overall"], 0); self.assertTrue(len(r["critical_gaps"]) >= 10)

    def test_full_marks(self):
        ids = [q[0] for d in assess.Q["domains"].values() for q in d]
        r = assess.readiness({i: 3 for i in ids})
        self.assertEqual((r["overall"], r["maturity"], r["critical_gaps"]), (100.0, "Tested", []))

    def test_eri_caps(self):
        e, l, r, x, p = analyse(NW)
        self.assertEqual(x["rag"], "RED")
        ids = [q[0] for d in assess.Q["domains"].values() for q in d]
        full = assess.readiness({i: 3 for i in ids})
        fake_lock = {"overall": 10}
        p2 = json.loads(json.dumps({"scenarios": {"stressed": {"feasible": False}}}))
        self.assertEqual(assess.eri(fake_lock, full, p2)["rag"], "AMBER")
        self.assertEqual(assess.eri({"overall": 80}, full, {"scenarios": {"stressed": {"feasible": True}}})["rag"], "RED")


class Reports(unittest.TestCase):
    def test_html_svgs_are_valid_xml(self):
        h = report.html_report(*analyse(NW))
        svgs = re.findall(r"<svg.*?</svg>", h, re.S)
        self.assertGreaterEqual(len(svgs), 6)
        for s in svgs: minidom.parseString(s)
        self.assertIn("NOT FEASIBLE", h)

    def test_markdown_has_mermaid_and_runbook(self):
        m = report.markdown_plan(*analyse(NW))
        self.assertIn("```mermaid", m); self.assertIn("Play:", m); self.assertIn("ScyllaDB", m)

    def test_cli_assess_writes_outputs(self):
        out = tempfile.mkdtemp()
        main(["assess", NW, "--out", out])
        for f in ("exit-report.html", "exit-plan.md", "results.json"):
            self.assertTrue(os.path.exists(os.path.join(out, f)))
        self.assertIn("eri", json.load(open(os.path.join(out, "results.json"))))


if __name__ == "__main__":
    unittest.main()
