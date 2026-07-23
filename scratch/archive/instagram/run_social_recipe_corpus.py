from __future__ import annotations

import json
import sys
from pathlib import Path

from kitchensync.parsing import parse_recipe_text


CASE_DIR = Path(__file__).parent / "social_recipe_cases"
SCORED_FIELDS = ("name", "servings", "raw_ingredients", "steps", "tags")
REQUIRED_KEYS = {
    "id",
    "queue_index",
    "platform",
    "creator",
    "source_url",
    "source_text_kind",
    "source_text",
    "expected",
    "expected_complete",
    "accepted",
    "notes",
}


def load_case(path: Path) -> dict[str, object]:
    case = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(case, dict):
        raise ValueError("case must be a JSON object")
    missing = REQUIRED_KEYS - case.keys()
    if missing:
        raise ValueError(f"missing keys: {', '.join(sorted(missing))}")
    if case["id"] != path.stem:
        raise ValueError("id must match the filename")
    if case["platform"] != "instagram" or case["source_text_kind"] != "description":
        raise ValueError("Phase 1 cases must use an Instagram description")
    if (
        not isinstance(case["queue_index"], int)
        or isinstance(case["queue_index"], bool)
        or case["queue_index"] < 1
        or not isinstance(case["source_text"], str)
        or not case["source_text"].strip()
    ):
        raise ValueError("queue_index must be positive and source_text must be nonblank")
    if not isinstance(case["source_url"], str) or not case["source_url"]:
        raise ValueError("source_url must be nonblank text")
    if case["creator"] is not None and not isinstance(case["creator"], str):
        raise ValueError("creator must be text or null")
    if not _is_text_list(case["notes"]):
        raise ValueError("notes must be a list of text values")
    if not isinstance(case["expected_complete"], bool) or not isinstance(case["accepted"], bool):
        raise ValueError("expected_complete and accepted must be booleans")

    expected = case["expected"]
    if not isinstance(expected, dict) or set(expected) != set(SCORED_FIELDS):
        raise ValueError(f"expected must contain exactly: {', '.join(SCORED_FIELDS)}")
    if expected["name"] is not None and not isinstance(expected["name"], str):
        raise ValueError("expected.name must be text or null")
    if (
        expected["servings"] is not None
        and (
            not isinstance(expected["servings"], int)
            or isinstance(expected["servings"], bool)
            or expected["servings"] < 1
        )
    ):
        raise ValueError("expected.servings must be a positive integer or null")
    for field in ("raw_ingredients", "steps", "tags"):
        if not _is_text_list(expected[field]):
            raise ValueError(f"expected.{field} must be a list of text values")
    if any(tag != tag.casefold() for tag in expected["tags"]):
        raise ValueError("expected.tags must be lowercase")
    evidence_is_complete = bool(
        expected["name"] and expected["raw_ingredients"] and expected["steps"]
    )
    if case["expected_complete"] != evidence_is_complete:
        raise ValueError(
            "expected_complete must agree with name, ingredient, and instruction evidence"
        )
    return case


def _is_text_list(value: object) -> bool:
    return isinstance(value, list) and all(
        isinstance(item, str) and bool(item.strip()) for item in value
    )


def actual_fields(result) -> dict[str, object]:
    if result.candidate is None:
        return {
            "name": None,
            "servings": None,
            "raw_ingredients": [],
            "steps": [],
            "tags": [],
        }
    return result.candidate.model_dump(include=set(SCORED_FIELDS))


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    case_paths = sorted(CASE_DIR.glob("*.json"))
    source_complete = 0
    parser_complete = 0
    correct_complete = 0
    source_incomplete = 0
    correct_fallback = 0
    failures = 0

    for path in case_paths:
        try:
            case = load_case(path)
            result = parse_recipe_text(case["source_text"])
            actual = actual_fields(result)
            expected_complete = case["expected_complete"]
            is_complete = not result.fallback_recommended
            fields_match = actual == case["expected"]
            completeness_matches = is_complete == expected_complete
            correct = fields_match and completeness_matches

            source_complete += int(expected_complete)
            source_incomplete += int(not expected_complete)
            parser_complete += int(is_complete)
            correct_complete += int(correct and is_complete)
            correct_fallback += int(correct and not is_complete)

            if correct and is_complete:
                status = "complete-correct"
            elif correct:
                status = "fallback-correct"
            elif is_complete:
                status = "complete-incorrect"
            else:
                status = "fallback-incorrect"

            accepted = case["accepted"]
            if accepted and not correct:
                status += " REGRESSION"
                failures += 1
            elif not accepted and correct:
                status += " ready-to-accept"

            print(f"{case['id']}: {status}")
            if not fields_match:
                print(f"  expected: {json.dumps(case['expected'], ensure_ascii=False)}")
                print(f"  actual:   {json.dumps(actual, ensure_ascii=False)}")
            if not completeness_matches:
                print(
                    f"  expected_complete={expected_complete} "
                    f"actual_complete={is_complete} warnings={result.warnings}"
                )
        except Exception as error:
            print(f"{path.name}: ERROR {error}")
            failures += 1

    coverage = correct_complete / source_complete if source_complete else 0.0
    precision = correct_complete / parser_complete if parser_complete else 0.0
    fallback = correct_fallback / source_incomplete if source_incomplete else 1.0

    print()
    print(f"cases: {len(case_paths)}")
    print(f"complete coverage: {correct_complete}/{source_complete} ({coverage:.1%})")
    print(f"complete precision: {correct_complete}/{parser_complete} ({precision:.1%})")
    print(f"fallback correctness: {correct_fallback}/{source_incomplete} ({fallback:.1%})")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
