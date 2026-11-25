"""Reads Terraform + application code + an optional estate.json. Stdlib only."""
from __future__ import annotations

import json
import os
import re

from .catalog import lookup
from .model import Estate, Resource

RES_RE = re.compile(r'^\s*resource\s+"([a-z0-9_]+)"\s+"([A-Za-z0-9_\-]+)"\s*\{', re.M)
REF_RE = re.compile(r'\b((?:aws|azurerm|azuread|google)_[a-z0-9_]+)\.([A-Za-z0-9_\-]+)\b')
KV_RE = r'\b{k}\s*=\s*"?([A-Za-z0-9_.\-]+)"?'

# call-site patterns -> catalog type they couple the code to
CODE_PATTERNS = {
    "aws_dynamodb_table": r"dynamodb|DynamoDB",
    "aws_sqs_queue": r"\bsqs\b|SQS",
    "aws_sns_topic": r"\bsns\b|SNS",
    "aws_kinesis_stream": r"kinesis",
    "aws_s3_bucket": r"(client|resource)\(\s*['\"]s3['\"]|s3\.(put|get|upload|download)",
    "aws_lambda_function": r"lambda_handler|exports\.handler",
    "aws_cognito_user_pool": r"cognito",
    "aws_kms_key": r"\bkms\b|KMS",
    "aws_sfn_state_machine": r"stepfunctions|\bsfn\b",
    "aws_sagemaker_endpoint": r"sagemaker",
    "aws_secretsmanager_secret": r"secretsmanager",
    "azurerm_cosmosdb_account": r"azure\.cosmos",
    "azurerm_servicebus_namespace": r"azure\.servicebus",
    "azurerm_storage_account": r"azure\.storage",
    "google_bigquery_dataset": r"google\.cloud\.bigquery|bigquery",
    "google_pubsub_topic": r"pubsub",
    "google_spanner_instance": r"spanner",
}
CODE_EXT = (".py", ".js", ".ts", ".java", ".go", ".cs")


def _body(text: str, start: int) -> str:
    """Return text of the {...} block starting at the '{' before `start` (string-aware)."""
    depth, i, in_str = 1, start, False
    while i < len(text) and depth:
        c = text[i]
        if c == '"' and text[i - 1] != "\\":
            in_str = not in_str
        elif not in_str:
            depth += (c == "{") - (c == "}")
        i += 1
    return text[start:i - 1]


def _prov(rtype):
    return "aws" if rtype.startswith("aws_") else "azure" if rtype.startswith(("azurerm_", "azuread_")) else "gcp"


def scan_terraform(root: str):
    out = []
    for d, _, files in os.walk(root):
        for fn in files:
            if not fn.endswith(".tf"):
                continue
            p = os.path.join(d, fn)
            with open(p, encoding="utf-8", errors="ignore") as fh:
                txt = fh.read()
            for m in RES_RE.finditer(txt):
                rtype, name = m.group(1), m.group(2)
                body = _body(txt, m.end())
                r = Resource(f"{rtype}.{name}", rtype, name, _prov(rtype), file=os.path.relpath(p, root))
                _, r.catalogued = lookup(rtype)
                for key, attr in (("criticality", "tier"), ("data_gb", "data_gb"), ("monthly_usd", "monthly_usd")):
                    km = re.search(KV_RE.format(k=key), body)
                    if km:
                        val = km.group(1)
                        if attr == "tier":
                            r.tier = val.lower()
                        else:
                            setattr(r, attr, float(val))
                            if attr == "monthly_usd":
                                r.monthly_estimated = False
                r._body = body
                out.append(r)
    known = {r.address for r in out}
    for r in out:
        r.deps = sorted({f"{a}.{b}" for a, b in REF_RE.findall(r._body) if f"{a}.{b}" in known and f"{a}.{b}" != r.address})
        del r._body
    return out


def scan_code(root: str):
    calls, files = {k: 0 for k in CODE_PATTERNS}, 0
    pats = {k: re.compile(v) for k, v in CODE_PATTERNS.items()}
    for d, _, fs in os.walk(root):
        if any(s in d for s in (".git", "node_modules", "__pycache__")):
            continue
        for fn in fs:
            if fn.endswith(CODE_EXT):
                hit = False
                with open(os.path.join(d, fn), encoding="utf-8", errors="ignore") as fh:
                    lines = fh.readlines()
                for line in lines:
                    for k, rx in pats.items():
                        if rx.search(line):
                            calls[k] += 1
                            hit = True
                files += hit
    return {k: v for k, v in calls.items() if v}, files


def load_estate(root: str, name: str | None = None) -> Estate:
    res = scan_terraform(root)
    calls, files = scan_code(root)
    settings = {}
    ov = os.path.join(root, "estate.json")
    if os.path.exists(ov):
        with open(ov) as fh:
            cfg = json.load(fh)
        settings = cfg.get("settings", {})
        name = name or cfg.get("name")
        for addr, o in cfg.get("resources", {}).items():
            for r in res:
                if r.address == addr:
                    r.tier = o.get("criticality", r.tier)
                    r.data_gb = o.get("data_gb", r.data_gb)
                    if "monthly_usd" in o:
                        r.monthly_usd, r.monthly_estimated = o["monthly_usd"], False
    return Estate(name or os.path.basename(os.path.abspath(root)), res, calls, files, settings)
