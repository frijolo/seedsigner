import pytest
import random
from collections import Counter

from embit import bip39
from seedsigner.helpers import mnemonic_generation
from seedsigner.models.settings_definition import SettingsConstants



def test_dice_rolls():
    """ Given random dice rolls, the resulting mnemonic should be valid. """
    dice_rolls = ""
    for i in range(0, 99):
        # Do not need truly rigorous random for this test
        dice_rolls += str(random.randint(1, 6))

    mnemonic = mnemonic_generation.generate_mnemonic_from_dice(dice_rolls)

    assert len(mnemonic) == 24
    assert bip39.mnemonic_is_valid(" ".join(mnemonic))

    dice_rolls = ""
    for i in range(0, mnemonic_generation.DICE__NUM_ROLLS__12WORD):
        # Do not need truly rigorous random for this test
        dice_rolls += str(random.randint(1, 6))

    mnemonic = mnemonic_generation.generate_mnemonic_from_dice(dice_rolls)
    assert len(mnemonic) == 12
    assert bip39.mnemonic_is_valid(" ".join(mnemonic))



def test_calculate_checksum_input_type():
    """
        Given an 11-word or 23-word mnemonic, the calculated checksum should yield a
        valid complete mnemonic.
        
        calculate_checksum should accept the mnemonic as:
        * a list of strings
        * string: "A B C", "A, B, C", "A,B,C"
    """
    # Test mnemonics from https://iancoleman.io/bip39/
    def _try_all_input_formats(partial_mnemonic: str):
        # List of strings
        mnemonic = mnemonic_generation.calculate_checksum(partial_mnemonic.split(" "))
        assert bip39.mnemonic_is_valid(" ".join(mnemonic))

        # Comma-separated string
        mnemonic = mnemonic_generation.calculate_checksum(partial_mnemonic.replace(" ", ","))
        assert bip39.mnemonic_is_valid(" ".join(mnemonic))

        # Comma-separated string w/space
        mnemonic = mnemonic_generation.calculate_checksum(partial_mnemonic.replace(" ", ", "))
        assert bip39.mnemonic_is_valid(" ".join(mnemonic))

        # Space-separated string
        mnemonic = mnemonic_generation.calculate_checksum(partial_mnemonic)
        assert bip39.mnemonic_is_valid(" ".join(mnemonic))

    partial_mnemonic = "crawl focus rescue cable view pledge rather dinner cousin unfair day"
    _try_all_input_formats(partial_mnemonic)

    partial_mnemonic = "bubble father debate ankle injury fence mesh evolve section wet coyote violin pyramid flower rent arrow round clutch myth safe base skin mobile"
    _try_all_input_formats(partial_mnemonic)




def test_calculate_checksum_invalid_mnemonics():
    """
        Should raise an Exception on a mnemonic that is invalid due to length or using invalid words.
    """
    with pytest.raises(Exception) as e:
        # Mnemonic is too short: 10 words instead of 11
        partial_mnemonic = "abandon " * 9 + "about"
        mnemonic_generation.calculate_checksum(partial_mnemonic)
    assert "12- or 24-word" in str(e)

    with pytest.raises(Exception) as e:
        # Valid mnemonic but unsupported length
        mnemonic = "devote myth base logic dust horse nut collect buddy element eyebrow visit empty dress jungle"
        mnemonic_generation.calculate_checksum(mnemonic)
    assert "12- or 24-word" in str(e)

    with pytest.raises(Exception) as e:
        # Mnemonic is too short: 22 words instead of 23
        partial_mnemonic = "abandon " * 21 + "about"
        mnemonic_generation.calculate_checksum(partial_mnemonic)
    assert "12- or 24-word" in str(e)

    with pytest.raises(ValueError) as e:
        # Invalid BIP-39 word
        partial_mnemonic = "foobar " * 11 + "about"
        mnemonic_generation.calculate_checksum(partial_mnemonic)
    assert "not in the dictionary" in str(e)



def test_calculate_checksum_with_default_final_word():
    """ 11-word and 23-word mnemonics use word `0000` as a temp final word to complete
        the mnemonic.
    """
    partial_mnemonic = "crawl focus rescue cable view pledge rather dinner cousin unfair day"
    mnemonic1 = mnemonic_generation.calculate_checksum(partial_mnemonic)

    partial_mnemonic += " abandon"
    mnemonic2 = mnemonic_generation.calculate_checksum(partial_mnemonic)
    assert mnemonic1 == mnemonic2

    partial_mnemonic = "bubble father debate ankle injury fence mesh evolve section wet coyote violin pyramid flower rent arrow round clutch myth safe base skin mobile"
    mnemonic1 = mnemonic_generation.calculate_checksum(partial_mnemonic)

    partial_mnemonic += " abandon"
    mnemonic2 = mnemonic_generation.calculate_checksum(partial_mnemonic)
    assert mnemonic1 == mnemonic2


def test_generate_mnemonic_from_bytes():
    """
        Should generate a valid BIP-39 mnemonic from entropy bytes
    """
    # From iancoleman.io
    entropy = "3350f6ac9eeb07d2c6209932808aa7f6"
    expected_mnemonic = "crew marble private differ race truly blush basket crater affair prepare unique".split()
    mnemonic = mnemonic_generation.generate_mnemonic_from_bytes(bytes.fromhex(entropy))
    assert mnemonic == expected_mnemonic

    entropy = "5bf41629fce815c3570955e8f45422abd7e2234141bd4d7ec63b741043b98cad"
    expected_mnemonic = "fossil pass media what life ticket found click trophy pencil anger fish lawsuit balance agree dash estate wage mom trial aerobic system crawl review".split()
    mnemonic = mnemonic_generation.generate_mnemonic_from_bytes(bytes.fromhex(entropy))
    assert mnemonic == expected_mnemonic



def test_verify_against_coldcard_sample():
    """ https://coldcard.com/docs/verifying-dice-roll-math """
    dice_rolls = "123456"
    expected = "mirror reject rookie talk pudding throw happy era myth already payment own sentence push head sting video explain letter bomb casual hotel rather garment"

    mnemonic = mnemonic_generation.generate_mnemonic_from_dice(dice_rolls)
    actual = " ".join(mnemonic)
    assert bip39.mnemonic_is_valid(actual)
    assert actual == expected



def test_known_dice_rolls():
    """ Given 99 known dice rolls, the resulting mnemonic should be valid and match the expected. """
    dice_rolls = "522222222222222222222222222222222222222222222555555555555555555555555555555555555555555555555555555"
    expected = "resource timber firm banner horror pupil frozen main pear direct pioneer broken grid core insane begin sister pony end debate task silk empty curious"

    mnemonic = mnemonic_generation.generate_mnemonic_from_dice(dice_rolls)
    actual = " ".join(mnemonic)
    assert bip39.mnemonic_is_valid(actual)
    assert actual == expected

    dice_rolls = "222222222222222222222222222222222222222222222555555555555555555555555555555555555555555555555555555"
    expected = "garden uphold level clog sword globe armor issue two cute scorpion improve verb artwork blind tail raw butter combine move produce foil feature wave"

    mnemonic = mnemonic_generation.generate_mnemonic_from_dice(dice_rolls)
    actual = " ".join(mnemonic)
    assert bip39.mnemonic_is_valid(actual)
    assert actual == expected

    dice_rolls = "222222222222222222222222222222222222222222222555555555555555555555555555555555555555555555555555556"
    expected = "lizard broken love tired depend eyebrow excess lonely advance father various cram ignore panic feed plunge miss regret boring unique galaxy fan detail fly"

    mnemonic = mnemonic_generation.generate_mnemonic_from_dice(dice_rolls)
    actual = " ".join(mnemonic)
    assert bip39.mnemonic_is_valid(actual)
    assert actual == expected



def test_50_dice_rolls():
    """ 50 dice roll input should yield the same 12-word mnemonic as iancoleman.io/bip39 """
    # Check "Show entropy details", paste in dice_rolls sequence, click "Hex", select "Mnemonic Length" as "12 Words"
    dice_rolls = "12345612345612345612345612345612345612345612345612"
    expected = "unveil nice picture region tragic fault cream strike tourist control recipe tourist"
    mnemonic = mnemonic_generation.generate_mnemonic_from_dice(dice_rolls)
    actual = " ".join(mnemonic)
    assert bip39.mnemonic_is_valid(actual)
    assert actual == expected

    dice_rolls = "11111111111111111111111111111111111111111111111111"
    expected = "diet glad hat rural panther lawsuit act drop gallery urge where fit"
    mnemonic = mnemonic_generation.generate_mnemonic_from_dice(dice_rolls)
    actual = " ".join(mnemonic)
    assert bip39.mnemonic_is_valid(actual)
    assert actual == expected

    dice_rolls = "66666666666666666666666666666666666666666666666666"
    expected = "senior morning song proud recycle toy search apple trigger lend vibrant arrest"
    mnemonic = mnemonic_generation.generate_mnemonic_from_dice(dice_rolls)
    actual = " ".join(mnemonic)
    assert bip39.mnemonic_is_valid(actual)
    assert actual == expected



# --- "Dice wordlist" method (direct 5-dice -> wordlist word) -------------------
# Algorithm, proof of uniformity, and the canonical vectors below are in
# docs/dice_wordlist.md (also mirrored in tools/dice_wordlist.py). Each roll is a
# string of 5 dice values, "1".."6".

DICE_WORDLIST_ROLLS_12 = [
    "41115", "16611", "32111", "36545", "42126", "11542",
    "16541", "13516", "34332", "15113", "26464", "21154",
]
DICE_WORDLIST_ROLLS_24 = DICE_WORDLIST_ROLLS_12 + [
    "21522", "13152", "36123", "23241", "54343", "54414",
    "52465", "43312", "44151", "44636", "23166", "25326",
]


def test_dice_wordlist_roll_value():
    """ A 5-dice roll converts to its base-6 value (first die is most significant). """
    assert mnemonic_generation.dice_wordlist_roll_value("41115") == 3892
    assert mnemonic_generation.dice_wordlist_roll_value("11111") == 0
    assert mnemonic_generation.dice_wordlist_roll_value("66666") == 7775
    assert mnemonic_generation.dice_wordlist_roll_value("55346") == 6143
    assert mnemonic_generation.dice_wordlist_roll_value("55351") == 6144


def test_dice_wordlist_roll_index():
    """ index = value // 3; rejected (None) when index >= 2048, i.e. value >= 6144. """
    assert mnemonic_generation.dice_wordlist_roll_index("11111") == 0
    assert mnemonic_generation.dice_wordlist_roll_index("55346") == 2047   # max accepted
    assert mnemonic_generation.dice_wordlist_roll_index("55351") is None   # min rejected
    assert mnemonic_generation.dice_wordlist_roll_index("66666") is None


def test_dice_wordlist_roll_word():
    """ An accepted roll maps to its wordlist word; a rejected roll maps to None. """
    assert mnemonic_generation.dice_wordlist_roll_word("11111") == "abandon"
    assert mnemonic_generation.dice_wordlist_roll_word("55346") == "zoo"
    assert mnemonic_generation.dice_wordlist_roll_word("55351") is None
    assert mnemonic_generation.dice_wordlist_roll_word("66666") is None


def test_dice_wordlist_known_mnemonics():
    """ The canonical 12- and 24-word vectors from docs/dice_wordlist.md. """
    expected_12 = "peasant cruel insect paper problem almost critic blouse melody catch happy dash"
    mnemonic = mnemonic_generation.generate_mnemonic_from_dice_wordlist(DICE_WORDLIST_ROLLS_12, 12)
    assert bip39.mnemonic_is_valid(" ".join(mnemonic))
    assert " ".join(mnemonic) == expected_12

    expected_24 = "peasant cruel insect paper problem almost critic blouse melody catch happy damp detail basic off engage walnut waste tragic require safe share enact divorce"
    mnemonic = mnemonic_generation.generate_mnemonic_from_dice_wordlist(DICE_WORDLIST_ROLLS_24, 24)
    assert bip39.mnemonic_is_valid(" ".join(mnemonic))
    assert " ".join(mnemonic) == expected_24


def test_dice_wordlist_checksum_corrects_final_word():
    """ Only the final word is adjusted to satisfy the BIP-39 checksum. """
    # The 12th roll's raw word is "damp"; as the checksum word of a 12-word mnemonic
    # it is corrected to "dash".
    assert mnemonic_generation.dice_wordlist_roll_word("21154") == "damp"
    expected_12 = "peasant cruel insect paper problem almost critic blouse melody catch happy dash"
    assert " ".join(mnemonic_generation.generate_mnemonic_from_dice_wordlist(DICE_WORDLIST_ROLLS_12, 12)) == expected_12


def test_dice_wordlist_checksum_only_changes_final_word():
    """
    Property: for arbitrary accepted rolls, calculate_checksum() leaves the first N-1
    words untouched and changes the final word only in its low 4 bits (12w) / 8 bits
    (24w), preserving the high bits that carry the real entropy.
    """
    random.seed(1337)
    for num_words in (12, 24):
        num_checksum_bits = 4 if num_words == 12 else 8
        # A word index is 11 bits; keep the high bits by clearing the low checksum bits.
        high_mask = 0b11111111111 & ~((1 << num_checksum_bits) - 1)
        for _ in range(50):
            # Rejection-sample in-range rolls (deterministic seed above)
            rolls = []
            while len(rolls) < num_words:
                roll = "".join(str(random.randint(1, 6)) for _ in range(5))
                if mnemonic_generation.dice_wordlist_roll_index(roll) is not None:
                    rolls.append(roll)

            rolled_words = [mnemonic_generation.dice_wordlist_roll_word(r) for r in rolls]
            final_words = mnemonic_generation.generate_mnemonic_from_dice_wordlist(rolls, num_words)

            # The first N-1 words are exactly the words the user rolled
            assert final_words[:-1] == rolled_words[:-1]

            # The final word may only differ in its low checksum bits; high bits preserved.
            rolled_idx = bip39.WORDLIST.index(rolled_words[-1])
            final_idx = bip39.WORDLIST.index(final_words[-1])
            assert (rolled_idx & high_mask) == (final_idx & high_mask)

            # And the result is a valid BIP-39 mnemonic.
            assert bip39.mnemonic_is_valid(" ".join(final_words))


def test_dice_wordlist_uniformity():
    """ Every accepted index 0..2047 has exactly 3 preimages; value >= 6144 is rejected. """
    counts = Counter()
    rejected = 0
    for value in range(6 ** 5):
        index = value // 3
        if index < mnemonic_generation.DICE_WORDLIST__WORDLIST_SIZE:
            counts[index] += 1
        else:
            rejected += 1

    # Uniform: each of the 2048 indices has exactly 3 preimages
    assert len(counts) == mnemonic_generation.DICE_WORDLIST__WORDLIST_SIZE
    assert set(counts.values()) == {3}

    # Exactly 6144 accepted and 1632 rejected (the hard floor for 5 dice)
    assert sum(counts.values()) == mnemonic_generation.DICE_WORDLIST__MAX_ACCEPTED_VALUE + 1
    assert rejected == 6 ** 5 - (mnemonic_generation.DICE_WORDLIST__MAX_ACCEPTED_VALUE + 1)


def test_dice_wordlist_invalid_input():
    """ Rolls must be exactly 5 dice of value 1-6; rejected rolls / bad counts raise. """
    for bad in ["1234", "123456", "12347", "abcde", ""]:
        with pytest.raises(ValueError):
            mnemonic_generation.dice_wordlist_roll_value(bad)

    # A rejected roll cannot be part of a mnemonic
    with pytest.raises(ValueError):
        mnemonic_generation.generate_mnemonic_from_dice_wordlist(DICE_WORDLIST_ROLLS_12[:-1] + ["66666"], 12)

    # Wrong number of words / rolls
    with pytest.raises(ValueError):
        mnemonic_generation.generate_mnemonic_from_dice_wordlist(DICE_WORDLIST_ROLLS_12, 24)
    with pytest.raises(ValueError):
        mnemonic_generation.generate_mnemonic_from_dice_wordlist(DICE_WORDLIST_ROLLS_12, 13)
