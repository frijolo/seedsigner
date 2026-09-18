#!/usr/bin/env python3
"""
Verification tool for SeedSigner's dice-wordlist mnemonic method:

    5 six-sided dice  ->  one BIP-39 wordlist index (0..2047, rejection-sampled)
    repeated 12 or 24 times, with the FINAL word's BIP-39 checksum auto-corrected.

It imports the SAME code the device runs (seedsigner.helpers.mnemonic_generation),
so its results always match the firmware. This mirrors how tools/mnemonic.py reuses
the app code instead of re-implementing it.

See: docs/dice_wordlist.md for the full algorithm, the math/proof, and test vectors.

tldr:
    pip3 install embit
    pip3 install -e .
    cd tools
    python3 dice_wordlist.py -h
"""

import argparse
import random

from embit import bip39
from embit.wordlists.bip39 import WORDLIST

from seedsigner.helpers import mnemonic_generation

# Reuse the device's constants so this tool can never drift from the firmware.
NUM_DICE = mnemonic_generation.DICE_WORDLIST__DICE_PER_WORD
BASE = mnemonic_generation.DICE_WORDLIST__FACES
NUM_WORDS = mnemonic_generation.DICE_WORDLIST__WORDLIST_SIZE
MAX_VALUE = BASE ** NUM_DICE - 1          # 6^5 - 1 = 7775
ROLLS__12WORD = 12
ROLLS__24WORD = 24


def roll_to_index(rolls):
    """Convert one 5-dice roll (each die 1-6, first die = most significant) into a
    BIP-39 wordlist index, delegating to the device's own helper functions.

    Returns (index, value):
        index: 0..2047 on a valid roll, or None if the roll is rejected (index >= 2048).
        value: the base-6 value of the roll (0..7775), for display/verification.
    """
    roll_str = "".join(str(d) for d in rolls)
    value = mnemonic_generation.dice_wordlist_roll_value(roll_str)
    index = mnemonic_generation.dice_wordlist_roll_index(roll_str)
    return index, value


def rolls_to_mnemonic(rolls):
    """rolls: list of 12 or 24 rolls (each a tuple/list of 5 dice in 1-6).
    Returns (per_roll, rolled_words, final_words).
    Raises ValueError if any roll is rejected (index >= 2048) or the count is wrong.

    The final mnemonic is built by the device's own generate_mnemonic_from_dice_wordlist().
    """
    if len(rolls) not in (ROLLS__12WORD, ROLLS__24WORD):
        raise ValueError(f"need {ROLLS__12WORD} or {ROLLS__24WORD} rolls, got {len(rolls)}")

    per_roll = []
    rolled_words = []
    for i, roll in enumerate(rolls, start=1):
        index, value = roll_to_index(roll)
        if index is None:
            raise ValueError(
                f"roll {i} is INVALID: base-6 value {value} -> index {value // 3} >= {NUM_WORDS}. "
                f"Re-roll this die set."
            )
        per_roll.append((roll, value, index, WORDLIST[index]))
        rolled_words.append(WORDLIST[index])

    roll_strings = ["".join(str(d) for d in roll) for roll in rolls]
    final_words = mnemonic_generation.generate_mnemonic_from_dice_wordlist(roll_strings, len(rolls))
    return per_roll, rolled_words, final_words


def parse_rolls(entropy_str):
    """Accept a digit string (all whitespace ignored) of 1-6 digits grouped into 5s."""
    digits = "".join(entropy_str.split())
    if any(c not in "123456" for c in digits):
        raise ValueError("only digits 1-6 (and whitespace) are allowed")
    if len(digits) % NUM_DICE != 0:
        raise ValueError(f"digit count {len(digits)} is not a multiple of {NUM_DICE}")
    return [tuple(int(c) for c in digits[start:start + NUM_DICE])
            for start in range(0, len(digits), NUM_DICE)]


def show(rolls):
    per_roll, rolled_words, final_words = rolls_to_mnemonic(rolls)
    print("\nPer-roll breakdown (first die = most significant):")
    for i, (roll, value, index, word) in enumerate(per_roll, start=1):
        print(f"  {i:2d}. {roll}  value={value:5d}  index={index:4d}  -> {word}")
    print(f"\n  rolled words : {' '.join(rolled_words)}")
    print(f"  final words  : {' '.join(final_words)}   <- final word is BIP-39 checksum-corrected")
    changed = [i + 1 for i, (a, b) in enumerate(zip(rolled_words, final_words)) if a != b]
    if changed:
        print(f"  (word(s) {changed} adjusted to satisfy the BIP-39 checksum)")
    print(f"\n  Verify each of the first {len(rolls) - 1} words by hand: "
          f"convert the 5 dice to base 6, divide by 3, look up the wordlist index. "
          f"The final word is the BIP-39 checksum of the first 128/256 entropy bits.")


def rand_rolls(count):
    """Rejection-sampled random (NOT cryptographically secure) rolls for a demo."""
    rolls = []
    while len(rolls) < count:
        r = tuple(random.randint(1, 6) for _ in range(NUM_DICE))
        if roll_to_index(r)[0] is not None:
            rolls.append(r)
    return rolls


# --- self-test vectors ---------------------------------------------------------
# Canonical 12-word example (see docs/dice_wordlist.md)
CANONICAL_12 = [
    (4, 1, 1, 1, 5), (1, 6, 6, 1, 1), (3, 2, 1, 1, 1), (3, 6, 5, 4, 5),
    (4, 2, 1, 2, 6), (1, 1, 5, 4, 2), (1, 6, 5, 4, 1), (1, 3, 5, 1, 6),
    (3, 4, 3, 3, 2), (1, 5, 1, 1, 3), (2, 6, 4, 6, 4), (2, 1, 1, 5, 4),
]
CANONICAL_12_FINAL = "peasant cruel insect paper problem almost critic blouse melody catch happy dash".split()

# Canonical 24-word example (the 12 above + 12 more)
CANONICAL_24 = CANONICAL_12 + [
    (2, 1, 5, 2, 2), (1, 3, 1, 5, 2), (3, 6, 1, 2, 3), (2, 3, 2, 4, 1),
    (5, 4, 3, 4, 3), (5, 4, 4, 1, 4), (5, 2, 4, 6, 5), (4, 3, 3, 1, 2),
    (4, 4, 1, 5, 1), (4, 4, 6, 3, 6), (2, 3, 1, 6, 6), (2, 5, 3, 2, 6),
]
CANONICAL_24_FINAL = (
    "peasant cruel insect paper problem almost critic blouse melody catch happy damp "
    "detail basic off engage walnut waste tragic require safe share enact divorce"
).split()

# (roll, expected_index_or_None) edge cases
EDGE_CASES = [
    ((1, 1, 1, 1, 1), 0),      # minimum valid -> wordlist[0]
    ((2, 2, 2, 2, 2), 518),
    ((3, 3, 3, 3, 3), 1036),
    ((5, 5, 3, 4, 6), 2047),   # maximum valid -> wordlist[2047]
    ((5, 5, 3, 5, 1), None),   # minimum invalid (value 6144 -> index 2048)
    ((6, 6, 6, 6, 6), None),   # maximum roll (value 7775 -> index 2591)
]


def selftest():
    print("Running self-test...\n")
    ok = True

    # canonical 12
    _, rolled, final = rolls_to_mnemonic(CANONICAL_12)
    good = final == CANONICAL_12_FINAL and bip39.mnemonic_is_valid(" ".join(final))
    ok &= good
    print(f"[{'PASS' if good else 'FAIL'}] 12-word canonical -> {final[-1]} (last word)")

    # canonical 24
    _, rolled, final = rolls_to_mnemonic(CANONICAL_24)
    good = final == CANONICAL_24_FINAL and bip39.mnemonic_is_valid(" ".join(final))
    ok &= good
    print(f"[{'PASS' if good else 'FAIL'}] 24-word canonical -> {final[-1]} (last word)")

    # edge cases
    for roll, expected in EDGE_CASES:
        idx, value = roll_to_index(roll)
        good = idx == expected
        ok &= good
        shown = WORDLIST[idx] if idx is not None else "REJECTED"
        print(f"[{'PASS' if good else 'FAIL'}] roll {roll} value={value} index={idx} -> {shown}")

    # boundary: exactly 6143 valid / 6144 invalid
    good = (6143 // 3) == 2047 and (6144 // 3) == 2048
    ok &= good
    print(f"[{'PASS' if good else 'FAIL'}] boundary: value 6143 -> idx 2047 (valid), 6144 -> idx 2048 (invalid)")

    # distribution is exactly uniform: every valid index has exactly 3 preimages
    from collections import Counter
    c = Counter(v // 3 for v in range(MAX_VALUE + 1) if v // 3 < NUM_WORDS)
    uniform = set(c.values()) == {3} and len(c) == NUM_WORDS
    ok &= uniform
    print(f"[{'PASS' if uniform else 'FAIL'}] uniformity: every index 0..2047 has exactly 3 preimages")

    print(f"\n{'ALL TESTS PASSED' if ok else 'SOME TESTS FAILED'}")
    return ok


# --- CLI -----------------------------------------------------------------------
usage = f"""
Verify / generate mnemonics with SeedSigner's "5 dice -> wordlist index" method.

  A roll of 5 dice is read as a base-6 number (die face f -> digit f-1, first die =
  most significant digit). value is in [0, {MAX_VALUE}]; index = value // 3. If
  index >= {NUM_WORDS} the roll is INVALID and must be re-rolled. Repeat 12 or 24
  times; the final word's BIP-39 checksum is auto-corrected.

Usage:
    # 12 rolls / 12-word mnemonic (digits 1-6, whitespace ignored, grouped by 5)
    python3 dice_wordlist.py 41115166113211136545...

    # 24 rolls / 24-word mnemonic
    python3 dice_wordlist.py <120 digits>

    # GENERATE a random (NOT secure) demo: 12 or 24 rejection-sampled rolls
    python3 dice_wordlist.py rand12
    python3 dice_wordlist.py rand24

    # Run the built-in self-test (canonical vectors + edge cases + uniformity)
    python3 dice_wordlist.py --selftest
"""

RAND_12 = "rand12"
RAND_24 = "rand24"
parser = argparse.ArgumentParser(description=usage, formatter_class=argparse.RawTextHelpFormatter)
parser.add_argument("entropy", nargs="?", help="60/120 dice digits (1-6), or rand12 / rand24")
parser.add_argument("--selftest", action="store_true", help="run built-in self-test and exit")


def main():
    args = parser.parse_args()

    if args.selftest:
        raise SystemExit(0 if selftest() else 1)

    if args.entropy is None:
        parser.print_help()
        raise SystemExit(1)

    try:
        if args.entropy in (RAND_12, RAND_24):
            count = ROLLS__12WORD if args.entropy == RAND_12 else ROLLS__24WORD
            rolls = rand_rolls(count)
            print(f"Random (NOT secure) {count} rolls: {''.join(str(d) for r in rolls for d in r)}")
            print("\t***** This is a demo seed. Do not use it to store funds!!! *****")
            show(rolls)
        else:
            show(parse_rolls(args.entropy))
    except ValueError as e:
        print(f"Error: {e}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
