import json
from pathlib import Path

from ai.notation import (
    format_compact_hand,
    format_unicode_hand,
    next_dora,
    parse_compact_hand,
    summarize_hand,
    validate_hand,
)

CORPUS_DIR = Path(__file__).parent / "fixtures" / "notation_corpus"


def _load_cases():
    for path in sorted(CORPUS_DIR.glob("batch-*.jsonl")):
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if line.strip():
                yield path.name, line_number, json.loads(line)


def test_generated_notation_roundtrip_corpus():
    case_count = 0
    for filename, line_number, case in _load_cases():
        location = f"{filename}:{line_number} ({case['id']})"
        parsed = parse_compact_hand(case["notation"])

        assert parsed == case["tiles"], location
        assert format_compact_hand(parsed) == case["notation"], location
        assert format_unicode_hand(parsed) == case["unicode"], location
        assert parse_compact_hand(case["unicode"]) == parsed, location

        validation = validate_hand(parsed)
        assert validation.valid, f"{location}: {validation.errors}"

        summary = summarize_hand(parsed)
        assert summary.total == 14, location
        assert summary.unique == case["summary"]["unique"], location
        assert list(summary.pairs) == case["summary"]["pairs"], location
        assert list(summary.triplets) == case["summary"]["triplets"], location
        assert list(summary.quads) == case["summary"]["quads"], location
        assert summary.honors == case["summary"]["honors"], location
        assert summary.terminals == case["summary"]["terminals"], location

        assert next_dora(case["indicator"]) == case["dora"], location
        case_count += 1

    assert case_count > 0
