# Dice-based mnemonic via wordlist index

This document specifies a **new** way to generate a BIP-39 mnemonic seed in SeedSigner
using physical dice. Unlike the existing "Dice Roll" tool (which concatenates 50/99
rolls and hashes them with SHA-256), this method turns **each roll of five dice
directly into one wordlist word**, with no hashing in between. The result is a seed
that can be **verified by hand**, word by word.

> **Note:**
> **Do NOT use the verification examples in this document for a seed you will later
> use with real funds. This exercise is only to check that the independent tools
> produce the same result as SeedSigner.**
> **If you want to verify a real seed, do it on an air-gapped, ephemeral machine
> (e.g. Tails-OS) and abandon that environment afterwards. Never type seed phrases
> you intend to store real funds with into an internet-connected computer.**

---

## Why this method

The current dice tool is cryptographically sound (SHA-256 over the roll string) but
the entropy-to-mnemonic step is a black box: there is no practical way for a user to
confirm, by hand, that the words shown on the device really follow from the dice they
rolled. This new method removes the hash from the per-word step. Each word is a
simple, deterministic function of five dice that can be recomputed with paper and a
pen (or any calculator). Only the final BIP-39 checksum (see below) still requires a
hash, and even that is a standard, independently-checkable value.

### Design decisions

| Decision | Choice |
|---|---|
| Dice per roll | 5 six-sided dice |
| Base-6 digit mapping | die face `f` → digit `f - 1` (so 1→0 … 6→5) |
| Digit order | first die = most significant digit |
| Value range | `0 .. 6^5 - 1` = `0 .. 7775` |
| Word index | `index = value // 3` |
| Rejection | reject (re-roll) when `index >= 2048` |
| Words needed | 12 or 24 |
| Checksum | final word auto-corrected via `calculate_checksum()` |

---

## The algorithm

For each word, roll **five** fair dice and do the following:

1. **Convert to a base-6 number.** Treat the five dice, in the order they were rolled,
   as the five digits of a base-6 number. A die showing face `f` is the base-6 digit
   `f - 1` (i.e. `1→0, 2→1, …, 6→5`). The **first** die is the most significant digit.
2. **Compute the value** in the range `0 .. 7775`:
   ```
   value = d1*6^4 + d2*6^3 + d3*6^2 + d4*6^1 + d5*6^0
   ```
   (equivalently, Horner's method: fold left with `v = v*6 + digit`).
3. **Derive the word index:** `index = value // 3` (integer division).
4. **Check the range.** The BIP-39 English wordlist has exactly **2048** words
   (indices `0 .. 2047`). If `index >= 2048`, the roll is **INVALID**: discard it and
   roll five new dice (repeat from step 1). Otherwise the word is
   `WORDLIST[index]`.
5. **Repeat** until you have **12** (or **24**) words.
6. **Apply the BIP-39 checksum.** Pass the 12/24 words through `calculate_checksum()`,
   which rewrites the low 4 bits (12 words) / 8 bits (24 words) of the **final** word
   so the phrase is a valid BIP-39 mnemonic. (See [Checksum](#the-bip-39-checksum).)

### Worked single-roll example

Roll: `4 1 1 1 5`

- base-6 digits: `3 0 0 0 4`
- value (Horner): `0 → ×6+3 = 3 → ×6+0 = 18 → ×6+0 = 108 → ×6+0 = 648 → ×6+4 = 3892`
- index: `3892 // 3 = 1297`
- `1297 < 2048` → **valid**, word = `WORDLIST[1297]` = **`peasant`**

---

## Why the distribution is uniform (the math)

- Five fair dice produce `6^5 = 7776` outcomes, all equally likely.
- Each outcome maps to a unique `value` in `[0, 7775]`, so every value is equally
  likely (probability `1/7776`).
- `index = value // 3` ranges over `[0, 2591]` (since `7775 // 3 = 2591`).
- A roll is accepted iff `index <= 2047`, i.e. `value <= 2047*3 + 2 = 6143`.
  - Accepted values: `0 .. 6143` → **6144** values.
  - Rejected values: `6144 .. 7775` → **1632** values (≈ **21.0 %**).
  - Accept probability: `6144 / 7776 = 0.7901` (≈ **79.0 %**).
- For any valid `index` `i` in `[0, 2047]`, the set of values that map to it is
  `{3i, 3i + 1, 3i + 2}`. Because `3*2047 + 2 = 6143`, **all three** of these values
  are accepted. So every valid word index has **exactly 3 equally-likely preimages**.

Therefore, conditional on a roll being accepted:

```
P(word = i | accepted) = 3 / 6144 = 1 / 2048     for every i in [0, 2047]
```

**The per-word distribution is exactly uniform over the 2048 wordlist.** This is a
standard rejection-sampling construction, so the method is cryptographically sound
given fair dice.

**Entropy.** Each accepted word contributes `log2(2048) = 11` bits. A 12-word phrase
holds 132 bits; 128 of those are true entropy (all from the dice) and the final 4 are
the BIP-39 checksum. A 24-word phrase holds 264 bits: 256 entropy + 8 checksum.

**Expected physical rolls** (at 79.0 % acceptance): ~**15** rolls for a 12-word seed,
~**30** rolls for a 24-word seed.

### Why we don't try to raise the acceptance ratio

The 79% acceptance (≈ 1-in-5 re-roll) is the mathematical floor for a **single**
five-dice rule that is exactly uniform: `7776 mod 2048 = 1632`, so no single rule can
use more than `2048·3 = 6144` of the 7776 outcomes.

It *can* be raised. A "fold" — when a roll is high (`value ≥ 6144`), roll **one** extra
die, compute `index = ((value − 6144)·6 + extra) // 4`, and accept if `< 2048` —
recovers ~84% of the rejected rolls and lifts acceptance to ~96.6% while remaining
**exactly** uniform (each word still lands on `1/2048`). We deliberately do **not**
use it: it turns one uniform rule into a two-case rule and adds a second computation to
verify by hand. The cost of the simpler rule is only an occasional full re-roll, which
is cheap to do physically, and the entire point of the method is that each word stays
trivially verifiable by hand.

**Efficiency trade-off (for the record).** Because a die's entropy is base-mixed
(`6 = 2·3`) while BIP-39 words are pure powers of two, a verifiable method must reject
the factor 3. This makes it less dice-efficient than the SHA-256 dice tool:

| Method | dice / 128 bits | dice / 256 bits | real bits per die | hand-verifiable |
|---|---:|---:|---:|---|
| SHA-256 dice (50/99) | 50 | 99 | 2.56 | no |
| This method (5 dice ÷3) | ~76 | ~152 | 1.69 | **yes** |
| (fold variant, not used) | ~65 | ~129 | 1.98 | yes |

The ~30% extra dice over the hash tool is the price of hand-verifiability.

---

## Assumptions and threat model

- **Fair dice.** The exact-uniformity proof assumes each die is fair and independent.
  Because the mapping is direct (not hashed), a biased die shifts the word distribution
  in a structured way rather than diffusing across the output. The rejection rate is a
  built-in sanity check: with fair dice you re-roll about 1 time in 5. If you re-roll
  much more often, suspect the dice. (The existing SHA-256 dice tool also cannot detect
  biased dice; it at least diffuses any bias pseudorandomly.)
- **No one else sees or dictates your rolls.** Because the mapping is direct, anyone
  who observes or controls *part* of your physical rolls learns the corresponding words
  directly (k observed rolls -> k known words, ~11k bits). With the SHA-256 tool,
  partial roll disclosure reveals no words (preimage resistance). This is an inherent
  trade-off of hand-verifiability, not a bug: keep the rolls private. If *all* rolls are
  disclosed, both methods fail equally (the algorithm is public).

---

## The BIP-39 checksum

**Why it is needed.** A BIP-39 mnemonic of N words is not N arbitrary words: the last
`N/32` bits are a checksum derived from the rest. Specifically, for 12 words the final
4 bits must equal the first 4 bits of `SHA-256` of the leading 128 entropy bits; for
24 words the final 8 bits must equal the first 8 bits of `SHA-256` of the leading 256
bits. If you simply pick 12 (or 24) uniform random words, the checksum only matches
by chance — **1/16** of the time for 12 words, **1/256** for 24. So N directly-rolled
words are *not* a valid mnemonic on their own.

**How SeedSigner handles it.** The N rolled words are passed through the existing
`calculate_checksum()` helper (`seedsigner/helpers/mnemonic_generation.py`), which:

1. takes the N words as a mnemonic *ignoring* its (likely wrong) checksum,
2. reduces them to the 128/256-bit entropy,
3. recomputes the correct BIP-39 checksum, and
4. returns the corrected N-word mnemonic.

**Consequence for the user.** The first `N - 1` words are exactly the words you rolled
and can be verified by hand. **Only the final word may change** — its low 4/8 bits are
overwritten with the correct checksum. This is the same pattern already used by the
existing "Calculate Final Word" tool. The final word is still verifiable against any
standard BIP-39 reference (see below), it just can't be reproduced from a single dice
roll alone because it encodes a hash.

---

## Test vectors

The vectors below are the reference for this algorithm. They are reproduced by the
command-line tool (`tools/dice_wordlist.py`, run its `--selftest`) and are encoded as
pytest cases in `tests/test_mnemonic_generation.py`.

### Canonical 12-word example

| # | dice | base-6 value | index | rolled word |
|---|------|-------------:|------:|-------------|
| 1 | 4 1 1 1 5 | 3892 | 1297 | peasant |
| 2 | 1 6 6 1 1 | 1260 | 420 | cruel |
| 3 | 3 2 1 1 1 | 2808 | 936 | insect |
| 4 | 3 6 5 4 5 | 3838 | 1279 | paper |
| 5 | 4 2 1 2 6 | 4115 | 1371 | problem |
| 6 | 1 1 5 4 2 | 163 | 54 | almost |
| 7 | 1 6 5 4 1 | 1242 | 414 | critic |
| 8 | 1 3 5 1 6 | 581 | 193 | blouse |
| 9 | 3 4 3 3 2 | 3325 | 1108 | melody |
| 10 | 1 5 1 1 3 | 866 | 288 | catch |
| 11 | 2 6 4 6 4 | 2517 | 839 | happy |
| 12 | 2 1 1 5 4 | 1323 | 441 | damp |

- Rolled words: `peasant cruel insect paper problem almost critic blouse melody catch happy damp`
- **Final mnemonic:** `peasant cruel insect paper problem almost critic blouse melody catch happy dash`
- (word 12 changes `damp` → `dash` to satisfy the checksum)

### Canonical 24-word example

The 12 rolls above, plus:

| # | dice | base-6 value | index | rolled word |
|---|------|-------------:|------:|-------------|
| 13 | 2 1 5 2 2 | 1447 | 482 | detail |
| 14 | 1 3 1 5 2 | 457 | 152 | basic |
| 15 | 3 6 1 2 3 | 3680 | 1226 | off |
| 16 | 2 3 2 4 1 | 1782 | 594 | engage |
| 17 | 5 4 3 4 3 | 5924 | 1974 | walnut |
| 18 | 5 4 4 1 4 | 5943 | 1981 | waste |
| 19 | 5 2 4 6 5 | 5542 | 1847 | tragic |
| 20 | 4 3 3 1 2 | 4393 | 1464 | require |
| 21 | 4 4 1 5 1 | 4560 | 1520 | safe |
| 22 | 4 4 6 3 6 | 4733 | 1577 | share |
| 23 | 2 3 1 6 6 | 1763 | 587 | enact |
| 24 | 2 5 3 2 6 | 2243 | 747 | frost |

- **Final mnemonic:** `peasant cruel insect paper problem almost critic blouse melody catch happy damp detail basic off engage walnut waste tragic require safe share enact divorce`
- (word 24 changes `frost` → `divorce` to satisfy the checksum)

### Edge cases (single rolls)

| dice | base-6 value | index | result |
|------|-------------:|------:|--------|
| 1 1 1 1 1 | 0 | 0 | `abandon` (minimum valid) |
| 2 2 2 2 2 | 1555 | 518 | `dolphin` |
| 3 3 3 3 3 | 3110 | 1036 | `light` |
| 5 5 3 4 6 | 6143 | 2047 | `zoo` (maximum valid) |
| 5 5 3 5 1 | 6144 | 2048 | **INVALID** (minimum rejected) |
| 6 6 6 6 6 | 7775 | 2591 | **INVALID** (maximum roll) |

The rejection boundary is exact: value `6143` → index `2047` (accepted), value `6144`
→ index `2048` (rejected).

---

## How to verify

### By hand
For each of the first `N - 1` words: read the five dice as a base-6 number (first die =
most significant, die face `f` = digit `f - 1`), divide by 3, and look up that index
in the BIP-39 English wordlist. It must match the word shown. Only the final word
requires the checksum.

### With the command-line tool
```bash
pip3 install embit
pip3 install -e .
cd tools
python3 dice_wordlist.py -h
```
- **Check the built-in test vectors + uniformity:** `python3 dice_wordlist.py --selftest`
- **Verify a specific roll sequence** (digits 1-6, whitespace ignored, grouped by 5):
  ```bash
  # 12 rolls / 12-word mnemonic
  python3 dice_wordlist.py 41115166113211136545...
  ```
  The tool prints the per-roll breakdown (value, index, word), the rolled words, and
  the final checksum-corrected mnemonic. An invalid roll is reported and rejected.
- **Generate a random demo** (rejection-sampled, *not* cryptographically secure — demo
  only): `python3 dice_wordlist.py rand12` or `rand24`.

> Note: `dice_wordlist.py` imports the same functions the device runs
> (`seedsigner.helpers.mnemonic_generation`), mirroring `tools/mnemonic.py`, so its
> results always match the firmware. It needs the SeedSigner source
> (`pip3 install -e .`) to import that helper.

### Cross-checking the final word
The full 128/256-bit entropy is exactly the bit concatenation of the first `N - 1`
rolled words plus the top 7/3 bits of the final rolled word. Paste that into
[iancoleman.io/bip39](https://iancoleman.io/bip39) (Hex mode, "12/24 Words") to
independently reproduce the entire mnemonic, checksum included.

---

## Implementation

This document establishes the algorithm and its test vectors. The feature is built
following the project's existing structure; the task-by-task plan and verification
results are in `docs/dice_wordlist_implementation.md`.

- **Helper** (`seedsigner/helpers/mnemonic_generation.py`): pure functions
  `dice_wordlist_roll_value(roll)`, `dice_wordlist_roll_index(roll)`,
  `dice_wordlist_roll_word(roll, lang)`, and
  `generate_mnemonic_from_dice_wordlist(rolls, num_words, lang)`, which reuses the
  existing `calculate_checksum` for the final word. Constants `DICE_WORDLIST__*`.
- **UI flow** (`seedsigner/views/tools_views.py`): a Tools sub-flow —
  `ToolsDiceWordlistMnemonicLengthView` (12/24) → `ToolsDiceWordlistEntryView`, which
  enters **five dice at a time** via `ToolsDiceWordlistRollScreen` (a `KeyboardScreen`),
  shows each accepted word (or prompts a re-roll when the roll is out of range) until
  12/24 words are collected, then stores the seed and routes to `SeedWordsWarningView`.
- **Menu/entry point:** a new `"New seed (dice words)"` option (icon `DICE_FIVE`) in
  `ToolsMenuView`, alongside the image (`"New seed (image)"`) and dice
  (`"New seed (dice)"`) seed-generation options. The three labels are kept distinct
  because each method produces an incompatible seed.
- **Tests:** the vectors above are pytest cases in `tests/test_mnemonic_generation.py`,
  plus a Tools flow test in `tests/test_flows_tools.py`.
