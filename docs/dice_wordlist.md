# Dice-based mnemonic via wordlist index

This document specifies a **new** way to generate a BIP-39 mnemonic seed in SeedSigner
using physical dice. Unlike the existing "Dice Roll" tool (which concatenates 50/99
rolls and hashes them with SHA-256), this method turns **each roll of six dice
directly into one wordlist word**, with no hashing in between. The result is a seed
that can be **verified by hand**, word by word.

> **Note:**
> **Do NOT use the verification examples in this document for a seed you will later
> use with real funds. This exercise is only to check that the independent tools
> produce the same result as SeedSigner.**
> **If you want to verify a real seed, do it on an air-gapped, ephemeral machine
> (e.g. Tails-OS) and abandon that environment afterwards. Never type seed phrases
> you intend to store real funds with into an internet-connected computer.**

> **Wordlist:** the method indexes into the BIP-39 wordlist configured in Settings.
> SeedSigner currently ships only the English wordlist, so every example in this
> document uses it.

---

## Why this method

The current dice tool is cryptographically sound (SHA-256 over the roll string) but
the entropy-to-mnemonic step is a black box: there is no practical way for a user to
confirm, by hand, that the words shown on the device really follow from the dice they
rolled. This new method removes the hash from the per-word step. Each word is a
simple, deterministic function of six dice that can be recomputed with paper and a
pen (or any calculator). Only the final BIP-39 checksum (see below) still requires a
hash, and even that is a standard, independently-checkable value.

### Design decisions

| Decision | Choice |
|---|---|
| Dice per roll | 6 six-sided dice |
| Base-6 digit mapping | die face `f` → digit `f - 1` (so 1→0 … 6→5) |
| Digit order | first die = most significant digit |
| Value range | `0 .. 6^6 - 1` = `0 .. 46655` |
| Word index | `index = value // 22` |
| Rejection | reject (re-roll) when `index >= 2048` |
| Words needed | 12 or 24 |
| Checksum | final word auto-corrected via `calculate_checksum()` |

---

## The algorithm

For each word, roll **six** fair dice and do the following:

1. **Convert to a base-6 number.** Treat the six dice, in the order they were rolled,
   as the six digits of a base-6 number. A die showing face `f` is the base-6 digit
   `f - 1` (i.e. `1→0, 2→1, …, 6→5`). The **first** die is the most significant digit.
2. **Compute the value** in the range `0 .. 46655`:
   ```
   value = d1*6^5 + d2*6^4 + d3*6^3 + d4*6^2 + d5*6^1 + d6*6^0
   ```
   (equivalently, Horner's method: fold left with `v = v*6 + digit`).
3. **Derive the word index:** `index = value // 22` (integer division).
4. **Check the range.** The BIP-39 English wordlist has exactly **2048** words
   (indices `0 .. 2047`). If `index >= 2048`, the roll is **INVALID**: discard it and
   roll six new dice (repeat from step 1). Otherwise the word is
   `WORDLIST[index]`.
5. **Repeat** until you have **12** (or **24**) words.
6. **Apply the BIP-39 checksum.** Pass the 12/24 words through `calculate_checksum()`,
   which rewrites the low 4 bits (12 words) / 8 bits (24 words) of the **final** word
   so the phrase is a valid BIP-39 mnemonic. (See [Checksum](#the-bip-39-checksum).)

### Worked single-roll example

Roll: `1 6 2 2 5 2`

- base-6 digits: `0 5 1 1 4 1`
- value (Horner): `0 → ×6+0 = 0 → ×6+5 = 5 → ×6+1 = 31 → ×6+1 = 187 → ×6+4 = 1126 → ×6+1 = 6757`
- index: `6757 // 22 = 307`
- `307 < 2048` → **valid**, word = `WORDLIST[307]` = **`chapter`**

---

## Why the distribution is uniform (the math)

- Six fair dice produce `6^6 = 46656` outcomes, all equally likely.
- Each outcome maps to a unique `value` in `[0, 46655]`, so every value is equally
  likely (probability `1/46656`).
- `index = value // 22` ranges over `[0, 2120]` (since `46655 // 22 = 2120`).
- A roll is accepted iff `index <= 2047`, i.e. `value <= 2047*22 + 21 = 45055`.
  - Accepted values: `0 .. 45055` → **45056** values.
  - Rejected values: `45056 .. 46655` → **1600** values (≈ **3.4 %**).
  - Accept probability: `45056 / 46656 = 0.9657` (≈ **96.6 %**).
- For any valid `index` `i` in `[0, 2047]`, the set of values that map to it is
  `{22i, 22i + 1, …, 22i + 21}`. Because `22*2047 + 21 = 45055`, **all twenty-two**
  of these values are accepted. So every valid word index has **exactly 22
  equally-likely preimages**.

Therefore, conditional on a roll being accepted:

```
P(word = i | accepted) = 22 / 45056 = 1 / 2048     for every i in [0, 2047]
```

**The per-word distribution is exactly uniform over the 2048 wordlist.** This is a
standard rejection-sampling construction, so the method is cryptographically sound
given fair dice.

**Entropy.** Each accepted word contributes `log2(2048) = 11` bits. A 12-word phrase
holds 132 bits; 128 of those are true entropy (all from the dice) and the final 4 are
the BIP-39 checksum. A 24-word phrase holds 264 bits: 256 entropy + 8 checksum.

**Expected physical rolls** (at 96.6 % acceptance): ~**12.4** rolls for a 12-word
seed, ~**24.9** rolls for a 24-word seed.

### Why six dice (and why the residual rejection is fine)

Using six dice rather than five is what keeps the re-roll rate low. With five dice the
floor for a single exactly-uniform rule was `7776 mod 2048 = 1632` rejected outcomes
(~21 %, a re-roll about once in five). Six dice drop that to
`46656 mod 2048 = 1600` rejected outcomes out of `46656` (~3.4 %, a re-roll about once
in twenty-nine) while still leaving every accepted index with an equal number of
preimages (22), so the per-word distribution stays exactly uniform. In exchange each
physical roll uses one more die, but because re-rolls become rare the net dice spent
per seed actually goes *down* (see the table below).

A "fold" (when a roll is high, `value ≥ 45056`, roll one extra die and remap) could
push acceptance from ~96.6 % to ~99.3 %, but at that point it buys almost nothing:
the method already re-rolls only about once per seed, and a fold turns one uniform
rule into a two-case rule and adds a second computation to verify by hand. We
deliberately do **not** use it.

**Efficiency trade-off (for the record).** Because a die's entropy is base-mixed
(`6 = 2·3`) while BIP-39 words are pure powers of two, a verifiable method must reject
the factor 3. This makes it less dice-efficient than the SHA-256 dice tool:

| Method | dice / 128 bits | dice / 256 bits | real bits per die | hand-verifiable |
|---|---:|---:|---:|---|
| SHA-256 dice (50/99) | 50 | 99 | 2.56 | no |
| This method (6 dice ÷22) | ~75 | ~149 | 1.72 | **yes** |
| (fold variant, not used) | ~71 | ~142 | 1.81 | yes |

The ~30% extra dice over the hash tool is the price of hand-verifiability.

---

## Assumptions and threat model

- **Fair dice.** The exact-uniformity proof assumes each die is fair and independent.
  Because the mapping is direct (not hashed), a biased die shifts the word distribution
  in a structured way rather than diffusing across the output. The rejection rate is a
  built-in sanity check: with fair dice you re-roll about 1 time in 29. If you re-roll
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

The vectors below are the reference for this algorithm and are encoded as pytest cases
in `tests/test_mnemonic_generation.py`.

### Canonical 12-word example

| # | dice | base-6 value | index | rolled word |
|---|------|-------------:|------:|-------------|
| 1 | 1 6 2 2 5 2 | 6757 | 307 | chapter |
| 2 | 4 5 2 1 5 2 | 28753 | 1306 | person |
| 3 | 2 5 6 2 3 1 | 14088 | 640 | exotic |
| 4 | 4 2 3 5 6 5 | 25234 | 1147 | month |
| 5 | 6 2 2 4 1 4 | 40503 | 1841 | tower |
| 6 | 5 2 5 1 3 2 | 33277 | 1512 | rug |
| 7 | 6 4 1 4 4 1 | 42894 | 1949 | victory |
| 8 | 3 1 2 2 6 1 | 15834 | 719 | fly |
| 9 | 5 1 3 1 6 1 | 31566 | 1434 | rebuild |
| 10 | 5 1 4 5 2 2 | 31903 | 1450 | relief |
| 11 | 3 4 4 5 1 3 | 20234 | 919 | indicate |
| 12 | 3 3 5 1 5 4 | 19035 | 865 | history |

- Rolled words: `chapter person exotic month tower rug victory fly rebuild relief indicate history`
- **Final mnemonic:** `chapter person exotic month tower rug victory fly rebuild relief indicate horse`
- (word 12 changes `history` → `horse` to satisfy the checksum)

### Canonical 24-word example

The 12 rolls above, plus:

| # | dice | base-6 value | index | rolled word |
|---|------|-------------:|------:|-------------|
| 13 | 6 2 3 3 3 3 | 40694 | 1849 | transfer |
| 14 | 2 6 2 2 1 3 | 14510 | 659 | fame |
| 15 | 6 4 5 2 5 6 | 43697 | 1986 | weapon |
| 16 | 6 2 1 6 3 6 | 40373 | 1835 | tornado |
| 17 | 6 1 2 3 3 1 | 39180 | 1780 | teach |
| 18 | 3 2 5 2 5 4 | 17775 | 807 | gossip |
| 19 | 4 1 4 2 3 3 | 24026 | 1092 | mass |
| 20 | 1 1 1 1 5 5 | 28 | 1 | ability |
| 21 | 5 2 2 2 1 1 | 32652 | 1484 | ridge |
| 22 | 1 3 3 4 6 3 | 3164 | 143 | ball |
| 23 | 1 3 3 6 1 6 | 3209 | 145 | banana |
| 24 | 2 1 5 2 6 6 | 8711 | 395 | cousin |

- **Final mnemonic:** `chapter person exotic month tower rug victory fly rebuild relief indicate history transfer fame weapon tornado teach gossip mass ability ridge ball banana choose`
- (word 24 changes `cousin` → `choose` to satisfy the checksum)

### Edge cases (single rolls)

| dice | base-6 value | index | result |
|------|-------------:|------:|--------|
| 1 1 1 1 1 1 | 0 | 0 | `abandon` (minimum valid) |
| 6 5 5 4 4 2 | 45055 | 2047 | `zoo` (maximum valid) |
| 6 5 5 4 4 3 | 45056 | 2048 | **INVALID** (minimum rejected) |
| 6 6 6 6 6 6 | 46655 | 2120 | **INVALID** (maximum roll) |

The rejection boundary is exact: value `45055` → index `2047` (accepted), value
`45056` → index `2048` (rejected).

---

## How to verify

### By hand
For each of the first `N - 1` words: read the six dice as a base-6 number (first die =
most significant, die face `f` = digit `f - 1`), divide by 22, and look up that index
in the BIP-39 English wordlist. It must match the word shown. Only the final word
requires the checksum.

### Cross-checking the final word
The full 128/256-bit entropy is exactly the bit concatenation of the first `N - 1`
rolled words plus the top 7/3 bits of the final rolled word. Paste that into
[iancoleman.io/bip39](https://iancoleman.io/bip39) (Hex mode, "12/24 Words") to
independently reproduce the entire mnemonic, checksum included.

---

## Implementation

The feature is built following the project's existing structure.

- **Helper** (`seedsigner/helpers/mnemonic_generation.py`): pure functions
  `dice_wordlist_roll_value(roll)`, `dice_wordlist_roll_index(roll)`,
  `dice_wordlist_roll_word(roll, lang)`, and
  `generate_mnemonic_from_dice_wordlist(rolls, num_words, lang)`, which reuses the
  existing `calculate_checksum` for the final word. Constants `DICE_WORDLIST__*`.
  The divisor (22) is computed as `(6 ** DICE_PER_WORD) // WORDLIST_SIZE` so it can
  never drift from the number of dice.
- **UI flow** (`seedsigner/views/tools_views.py`): a Tools sub-flow —
  `ToolsDiceWordlistMnemonicLengthView` (12/24) → `ToolsDiceWordlistEntryView`, which
  enters **six dice at a time** via `ToolsDiceWordlistRollScreen` (a `KeyboardScreen`),
  shows each accepted word (or prompts a re-roll when the roll is out of range) until
  12/24 words are collected, then stores the seed and routes to `SeedWordsWarningView`.
    On the **final** word the checksum is computed immediately: if it corrects the rolled
    word, the feedback screen shows **both** the final (stored) word — prominently, as the
    headline — and the word that was actually rolled, so the user sees the substitution
    while generating rather than only in the seed backup.
- **Menu/entry point:** a new `"New seed (dice words)"` option (icon `DICE_SIX`) in
  `ToolsMenuView`, alongside the existing image- and dice-entropy `"New seed"` options.
- **Tests:** the vectors above are pytest cases in `tests/test_mnemonic_generation.py`,
  plus a Tools flow test in `tests/test_flows_tools.py`.
