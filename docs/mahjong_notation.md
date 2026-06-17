# Mahjong notation helpers

`ai.notation` is the shared boundary between human-readable tile input and the
canonical names used by recognition, shanten, ukeire, and advice code.

## Compact notation

The parser accepts the common suffix notation:

| Suffix | Tiles | Example |
| --- | --- | --- |
| `m` | characters / manzu | `123m` |
| `p` | dots / pinzu | `456p` |
| `s` | bamboo / souzu | `789s` |
| `z` | honors | `12344z` |

Honor digits use `east, south, west, north, white, green, red` for `1` through
`7`. A zero in a suited group is accepted as a red-five spelling and is
normalized to the project's regular rank-five tile because red-dora identity
is not yet represented by the core tile set.

```python
from ai.notation import format_compact_hand, parse_compact_hand

hand = parse_compact_hand("123m 456p 789s 12344z")
assert format_compact_hand(hand) == "123m456p789s12344z"
```

Separated aliases (`m1, m2, east`), canonical names, iterables of tile names,
and Unicode Mahjong Tile symbols are accepted as well. Parsing is strict: an
unknown token or an unconsumed character raises `NotationError` instead of
silently changing a hand.

## Ordering and display

- `sort_hand()` returns canonical playable tiles in characters, dots, bamboo,
  then honors order.
- `format_compact_hand()` groups a hand by suit.
- `format_unicode_hand()` is suitable for diagnostics and text-only previews.
- `tile_suit()`, `tile_rank()`, and the tile predicates expose metadata without
  duplicating string parsing in callers.

## Dora indicators

`next_dora()` implements the three cycles used by Japanese mahjong:

- suited tiles advance from 1 to 9 and wrap to 1;
- winds cycle east, south, west, north;
- dragons cycle white, green, red.

Use `dora_from_indicators()` when the screen recognizer returns multiple
indicators.

## Validation and summaries

```python
from ai.notation import summarize_hand, validate_hand

result = validate_hand(hand)
if result.valid:
    summary = summarize_hand(result.tiles)
    print(summary.suits, summary.pairs)
else:
    print(result.errors)
```

Validation reports unknown names, more than four physical copies, and
unexpected 13/14-tile counts. It returns canonicalized tiles separately from
errors so the UI can show useful diagnostics without feeding invalid input to
the advisor.

The data-driven contracts in `test/fixtures/notation_cases.json` cover every
playable tile, mixed hands, invalid inputs, dora cycles, and hand validation.
