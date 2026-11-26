"""Evaluation harness.

    python -m civictexas_summarize.evaluate              # check the dataset's prepared candidates
    python -m civictexas_summarize.evaluate --provider X # score a real provider (once one is added)

For each case it reports:
- validation: whether the automated checks pass and which issues were found
- accuracy: share of required facts covered by statements that have valid citations
- expectation: whether the result matches the case's expected outcome
"""
import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List

from .prompt import build_prompt
from .providers import StaticProvider, get_provider
from .schema import SchemaError, parse_summary
from .sections import normalize
from .validate import validate_summary

ROOT = Path(__file__).resolve().parents[2]
DATASET = ROOT / "summarization" / "evals" / "cases.json"
sys.path.insert(0, str(ROOT / "ingestion"))
from civictexas_ingest.text import decode_html, html_to_text  # noqa: E402


def source_text(case: Dict) -> str:
    source = case["source"]
    if "fixture" in source:
        return html_to_text(decode_html((ROOT / source["fixture"]).read_bytes()))
    return source["synthetic_text"]


def fact_coverage(summary_json: Dict, required: List[Dict], invalid: set = frozenset()) -> Dict[str, bool]:
    """Only statements with valid citations count toward accuracy."""
    texts = []
    if summary_json["overview"]["citations"] and "overview" not in invalid:
        texts.append(summary_json["overview"]["text"])
    for key in ("key_provisions", "changes_to_existing_law", "effective_dates"):
        texts += [s["text"] for i, s in enumerate(summary_json[key])
                  if s["citations"] and f"{key}[{i}]" not in invalid]
    texts += [f"{g['group']} {g['effect']}" for i, g in enumerate(summary_json["affected_groups"])
              if f"affected_groups[{i}]" not in invalid]
    blob = normalize(" ".join(texts))
    covered = {}
    for fact in required:
        ok = any(p in blob for p in fact["any_of"])
        if ok and fact.get("and_any_of"):
            ok = any(p in blob for p in fact["and_any_of"])
        covered[fact["id"]] = ok
    return covered


def evaluate_output(case: Dict, raw: str) -> Dict:
    text = source_text(case)
    try:
        data = json.loads(raw)
        summary = parse_summary(data)
    except (json.JSONDecodeError, SchemaError) as error:
        return {"passed": False, "issues": ["invalid_output"], "accuracy": 0.0, "detail": str(error)}
    validation = validate_summary(summary, text, case["status"], has_fiscal_note=case["has_fiscal_note"])
    invalid = {i.where for i in validation.issues if i.severity == "error"}
    coverage = fact_coverage(summary.to_json(), case["required_facts"], invalid)
    return {
        "passed": validation.passed,
        "issues": sorted({i.code for i in validation.issues}),
        "accuracy": round(sum(coverage.values()) / len(coverage), 2) if coverage else None,
        "missing_facts": [k for k, v in coverage.items() if not v],
    }


def run_candidates(dataset: Dict) -> List[Dict]:
    rows = []
    for case in dataset["cases"]:
        for candidate in case["candidates"]:
            provider = StaticProvider({case["bill"]: candidate["output"]})
            prompt = build_prompt(case["bill"], "test", case["version"], case["status"], source_text(case))
            result = evaluate_output(case, provider.generate(prompt))
            expected_ok = (result["passed"] == candidate["expect_pass"]
                           and set(candidate["expect_issues"]) <= set(result["issues"]))
            rows.append({"case": case["id"], "candidate": candidate["label"], **result, "as_expected": expected_ok})
    return rows


def run_provider(dataset: Dict, provider_name: str) -> List[Dict]:
    provider = get_provider(provider_name)
    rows = []
    for case in dataset["cases"]:
        prompt = build_prompt(case["bill"], "", case["version"], case["status"], source_text(case))
        rows.append({"case": case["id"], "candidate": provider.model_id, **evaluate_output(case, provider.generate(prompt))})
    return rows


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", help="score a configured provider instead of the prepared candidates")
    args = parser.parse_args(argv)
    dataset = json.loads(DATASET.read_text())
    rows = run_provider(dataset, args.provider) if args.provider else run_candidates(dataset)
    for r in rows:
        mark = "" if r.get("as_expected", True) else "  <-- UNEXPECTED"
        print(f"{r['case']:<20} {r['candidate'][:48]:<48} pass={str(r['passed']):<5} "
              f"accuracy={r['accuracy']} issues={','.join(r['issues']) or '-'}{mark}")
    unexpected = [r for r in rows if not r.get("as_expected", True)]
    print(f"\n{len(rows)} results, {len(unexpected)} unexpected")
    return 1 if unexpected else 0


if __name__ == "__main__":
    sys.exit(main())
