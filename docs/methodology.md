# Methodology

## 1. Portability classes (every catalogued service is assigned one)

| Class | Meaning | Example | Base effort (person-days) |
|---|---|---|---|
| 1 | Lift-and-shift: standard VM/disk | `aws_instance` | 2 |
| 2 | Open-standard managed service | RDS Postgres, EKS, S3 (S3 API), MSK | 5 |
| 3 | Re-platform: same idea, different API | ALB, Azure Blob, CloudWatch | 15 |
| 4 | Re-architect: proprietary model | Lambda, SQS, KMS, IAM | 40 |
| 5 | Proprietary, no real equivalent | DynamoDB, Kinesis, Step Functions, Cognito | 90 |

Unknown resource types default to class 4 and are listed as **uncatalogued** so nothing is silently scored as portable.

## 2. Lock-in score (0–100)

`score = class_score + min(code_call_sites/10, 10)` capped at 100, weighted by
`tier_weight × (1 + min(log10(1+data_GB)/4, 1))` — a petabyte table counts more than an empty one.
Levels: <25 LOW · <50 MODERATE · <70 HIGH · ≥70 SEVERE.

## 3. Timeline

Work is grouped into six waves (foundations → data → messaging → compute → ML/observability → edge cutover).
Each wave lasts `max(effort ÷ capacity, data transfer, change-control floor)`.
- **Capacity** is `team^0.85` — adding people has diminishing returns.
- **Data transfer** shares one link (default 5 Gbps at 50% utilisation) plus verification days.
- **Floor**: 21 days (planned) / 10 days (stressed) for any wave touching tier-1, for change control and evidence.
- Waves overlap by 30%; a 14-day parallel run closes the plan.
- `min_team` finds the smallest team that meets the window; if none does (≤500), it reports **unreachable**.

## 4. Cost

`egress + labour + dual-running + contingency`. Labour = effort × day rate × surge premium (1.5× stressed).
Dual-running = monthly spend × 0.9 × (½ × migration months + parallel-run period).
Everything is a setting in `estate.json`; defaults are in `exitkit/plan.py`.

## 5. Exit Readiness Index

`ERI = 50% × (100 − lock-in) + 50% × organisational readiness`. RAG: ≥70 GREEN, ≥45 AMBER, else RED.
Overrides: stressed exit infeasible ⇒ max AMBER · portability < 30 ⇒ RED · five or more critical gaps ⇒ max AMBER.
A beautiful architecture with no tested runbook, or a great runbook on a captive architecture, should not score green.

## 6. Honest limits

- Rates and throughput are **assumptions to validate**, not quotes. Run a real transfer test (DAT-6).
- It sees what is in Terraform and source code. Click-ops resources and SaaS dependencies need `estate.json` entries.
- Class assignments are opinionated; edit `exitkit/data/catalog.json` to match your reality — that's a feature.
- Business-process, vendor-contract and people risks are covered by the questionnaire, not by scanning.
