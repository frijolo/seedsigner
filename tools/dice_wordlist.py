#!/usr/bin/env python3
"""
Verification tool for SeedSigner's dice-wordlist mnemonic method.

6 six-sided dice -> one BIP-39 wordlist word (no hashing), repeated 12 or 24 times,
with the final word's BIP-39 checksum auto-corrected.

Imports the same code the device runs (seedsigner.helpers.mnemonic_generation),
so its results always match the firmware.

See: docs/dice_wordlist.md for the full algorithm, proof, and test vectors.

Usage:
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

DICE_PER_WORD = mnemonic_generation.DICE_WORDLIST__DICE_PER_WORD
FACES = mnemonic_generation.DICE_WORDLIST__FACES
WORDLIST_SIZE = mnemonic_generation.DICE_WORDLIST__WORDLIST_SIZE
MULTIPLIER = mnemonic_generation.DICE_WORDLIST__MULTIPLIER
MAX_VALUE = FACES ** DICE_PER_WORD - 1  # 46655


def roll_to_index(roll_tuple):
    """Convert a 6-dice roll (each 1-6, first = most significant) to (index, value)."""
    roll_str = "".join(str(d) for d in roll_tuple)
    value = mnemonic_generation.dice_wordlist_roll_value(roll_str)
    index = mnemonic_generation.dice_wordlist_roll_index(roll_str)
    return index, value


def rolls_to_mnemonic(rolls):
    """rolls: list of 12 or 24 tuples of 6 dice values (1-6). Returns per-roll breakdown."""
    if len(rolls) not in (12, 24):
        raise ValueError(f"need 12 or 24 rolls, got {len(rolls)}")

    per_roll = []
    rolled_words = []
    for i, roll in enumerate(rolls, start=1):
        index, value = roll_to_index(roll)
        if index is None:
            raise ValueError(
                f"roll {i} is REJECTED: value {value} // {MULTIPLIER} = {value // MULTIPLIER} >= {WORDLIST_SIZE}"
            )
        per_roll.append((roll, value, index, WORDLIST[index]))
        rolled_words.append(WORDLIST[index])

    roll_strings = ["".join(str(d) for d in roll) for roll in rolls]
    final_words = mnemonic_generation.generate_mnemonic_from_dice_wordlist(roll_strings, len(rolls))
    return per_roll, rolled_words, final_words


def parse_rolls(entropy_str):
    """Accept a digit string (whitespace ignored) of 1-6 digits grouped into 6s."""
    digits = "".join(entropy_str.split())
    if any(c not in "123456" for c in digits):
        raise ValueError("only digits 1-6 (and whitespace) are allowed")
    if len(digits) % DICE_PER_WORD != 0:
        raise ValueError(f"digit count {len(digits)} is not a multiple of {DICE_PER_WORD}")
    return [tuple(int(c) for c in digits[i:i + DICE_PER_WORD])
            for i in range(0, len(digits), DICE_PER_WORD)]


def show(rolls):
    per_roll, rolled_words, final_words = rolls_to_mnemonic(rolls)
    print("\nPer-roll breakdown (first die = most significant):")
    for i, (roll, value, index, word) in enumerate(per_roll, start=1):
        print(f"  {i:2d}. {' '.join(map(str, roll))}  value={value:5d}  index={index:4d}  -> {word}")
    print(f"\n  rolled words: {' '.join(rolled_words)}")
    print(f"  final words : {' '.join(final_words)}")
    changed = [i + 1 for i, (a, b) in enumerate(zip(rolled_words, final_words)) if a != b]
    if changed:
        print(f"  (word {changed[0]} adjusted for BIP-39 checksum)")


def rand_rolls(count):
    """Rejection-sampled random (NOT cryptographically secure) rolls."""
    rolls = []
    while len(rolls) < count:
        r = tuple(random.randint(1, 6) for _ in range(DICE_PER_WORD))
        if roll_to_index(r)[0] is not None:
            rolls.append(r)
    return rolls


# --- self-test vectors (from docs/dice_wordlist.md) ---
CANONICAL_12 = [
    (1,6,2,2,5,2), (4,5,2,1,5,2), (2,5,6,2,3,1), (4,2,3,5,6,5),
    (6,2,2,4,1,4), (5,2,5,1,3,2), (6,4,1,4,4,1), (3,1,2,2,6,1),
    (5,1,3,1,6,1), (5,1,4,5,2,2), (3,4,4,5,1,3), (3,3,5,1,5,4),
]
CANONICAL_12_FINAL = "chapter person exotic month tower rug victory fly rebuild relief indicate horse".split()

CANONICAL_24 = CANONICAL_12 + [
    (6,2,3,3,3,3), (2,6,2,2,1,3), (6,4,5,2,5,6), (6,2,1,6,3,6),
    (6,1,2,3,3,1), (3,2,5,2,5,4), (4,1,4,2,3,3), (1,1,1,1,5,5),
    (5,2,2,2,1,1), (1,3,3,4,6,3), (1,3,3,6,1,6), (2,1,5,2,6,6),
]
CANONICAL_24_FINAL = ("chapter person exotic month tower rug victory fly rebuild relief "
                      "indicate history transfer fame weapon tornado teach gossip mass "
                      "ability ridge ball banana choose").split()

EDGE_CASES = [
    ((1,1,1,1,1,1), 0),        # min valid -> "abandon"
    ((6,5,5,4,4,2), 2047),     # max valid -> "zoo"
    ((6,5,5,4,4,3), None),     # min rejected
    ((6,6,6,6,6,6), None),     # max roll
]


def selftest():
    print("Running self-test...\n")
    ok = True

    _, _, final = rolls_to_mnemonic(CANONICAL_12)
    good = final == CANONICAL_12_FINAL and bip39.mnemonic_is_valid(" ".join(final))
    ok &= good
    print(f"[{'PASS' if good else 'FAIL'}] 12-word canonical")

    _, _, final = rolls_to_mnemonic(CANONICAL_24)
    good = final == CANONICAL_24_FINAL and bip39.mnemonic_is_valid(" ".join(final))
    ok &= good
    print(f"[{'PASS' if good else 'FAIL'}] 24-word canonical")

    for roll, expected in EDGE_CASES:
        idx, value = roll_to_index(roll)
        good = idx == expected
        ok &= good
        shown = WORDLIST[idx] if idx is not None else "REJECTED"
        print(f"[{'PASS' if good else 'FAIL'}] {' '.join(map(str, roll))}  value={value}  index={idx}  -> {shown}")

    from collections import Counter
    c = Counter(v // MULTIPLIER for v in range(FACES ** DICE_PER_WORD) if v // MULTIPLIER < WORDLIST_SIZE)
    uniform = set(c.values()) == {MULTIPLIER} and len(c) == WORDLIST_SIZE
    ok &= uniform
    print(f"[{'PASS' if uniform else 'FAIL'}] uniformity: every index 0..{WORDLIST_SIZE-1} has exactly {MULTIPLIER} preimages")

    print(f"\n{'ALL TESTS PASSED' if ok else 'SOME TESTS FAILED'}")
    return ok


# --- CLI ---
usage = f"""
Verify / generate mnemonics with SeedSigner's dice-wordlist method (6 dice per word).

  Each roll of 6 dice is a base-6 number (die face f -> digit f-1, first die = MSD).
  value is in [0, {MAX_VALUE}]; index = value // {MULTIPLIER}. If index >= {WORDLIST_SIZE},
  the roll is rejected. Repeat 12 or 24 times; the final word's checksum is auto-corrected.

Usage:
    python3 dice_wordlist.py <72 or 144 digits>   # verify your rolls
    python3 dice_wordlist.py rand12               # random demo (NOT secure)
    python3 dice_wordlist.py rand24
    python3 dice_wordlist.py --selftest           # run built-in self-test
"""

parser = argparse.ArgumentParser(description=usage, formatter_class=argparse.RawTextHelpFormatter)
parser.add_argument("entropy", nargs="?", help="72/144 dice digits (1-6), or rand12 / rand24")
parser.add_argument("--selftest", action="store_true", help="run built-in self-test and exit")


def main():
    args = parser.parse_args()

    if args.selftest:
        raise SystemExit(0 if selftest() else 1)

    if args.entropy is None:
        parser.print_help()
        raise SystemExit(1)

    try:
        if args.entropy in ("rand12", "rand24"):
            count = 12 if args.entropy == "rand12" else 24
            rolls = rand_rolls(count)
            print(f"Random (NOT secure) {count} rolls: {''.join(str(d) for r in rolls for d in r)}")
            print("\t***** Demo seed only. Do NOT use to store funds! *****")
            show(rolls)
        else:
            show(parse_rolls(args.entropy))
    except ValueError as e:
        print(f"Error: {e}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
