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



# --- Dice wordlist method (direct 6-dice -> wordlist word) ---
# See docs/dice_wordlist.md for the algorithm and canonical vectors.

DICE_WORDLIST_ROLLS_12 = [
    "162252", "452152", "256231", "423565", "622414", "525132",
    "641441", "312261", "513161", "514522", "344513", "335154",
]
DICE_WORDLIST_ROLLS_24 = DICE_WORDLIST_ROLLS_12 + [
    "623333", "262213", "645256", "621636", "612331", "325254",
    "414233", "111155", "522211", "133463", "133616", "215266",
]


def test_dice_wordlist_roll_value():
    """ A 6-dice roll converts to its base-6 value (first die is most significant). """
    assert mnemonic_generation.dice_wordlist_roll_value("162252") == 6757
    assert mnemonic_generation.dice_wordlist_roll_value("111111") == 0
    assert mnemonic_generation.dice_wordlist_roll_value("666666") == 46655
    assert mnemonic_generation.dice_wordlist_roll_value("655442") == 45055
    assert mnemonic_generation.dice_wordlist_roll_value("655443") == 45056


def test_dice_wordlist_roll_index():
    """ index = value // 22; rejected (None) when index >= 2048, i.e. value >= 45056. """
    assert mnemonic_generation.dice_wordlist_roll_index("111111") == 0
    assert mnemonic_generation.dice_wordlist_roll_index("655442") == 2047   # max accepted
    assert mnemonic_generation.dice_wordlist_roll_index("655443") is None   # min rejected
    assert mnemonic_generation.dice_wordlist_roll_index("666666") is None


def test_dice_wordlist_roll_word():
    """ An accepted roll maps to its wordlist word; a rejected roll maps to None. """
    assert mnemonic_generation.dice_wordlist_roll_word("111111") == "abandon"
    assert mnemonic_generation.dice_wordlist_roll_word("655442") == "zoo"
    assert mnemonic_generation.dice_wordlist_roll_word("655443") is None
    assert mnemonic_generation.dice_wordlist_roll_word("666666") is None


def test_dice_wordlist_known_mnemonics():
    """ The canonical 12- and 24-word vectors from docs/dice_wordlist.md. """
    expected_12 = "chapter person exotic month tower rug victory fly rebuild relief indicate horse"
    mnemonic = mnemonic_generation.generate_mnemonic_from_dice_wordlist(DICE_WORDLIST_ROLLS_12, 12)
    assert bip39.mnemonic_is_valid(" ".join(mnemonic))
    assert " ".join(mnemonic) == expected_12

    expected_24 = "chapter person exotic month tower rug victory fly rebuild relief indicate history transfer fame weapon tornado teach gossip mass ability ridge ball banana choose"
    mnemonic = mnemonic_generation.generate_mnemonic_from_dice_wordlist(DICE_WORDLIST_ROLLS_24, 24)
    assert bip39.mnemonic_is_valid(" ".join(mnemonic))
    assert " ".join(mnemonic) == expected_24


def test_dice_wordlist_checksum_corrects_final_word():
    """ Only the final word is adjusted to satisfy the BIP-39 checksum. """
    # The 12th roll's raw word is "history"; as the checksum word of a 12-word mnemonic
    # it is corrected to "horse".
    assert mnemonic_generation.dice_wordlist_roll_word("335154") == "history"
    expected_12 = "chapter person exotic month tower rug victory fly rebuild relief indicate horse"
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
                roll = "".join(str(random.randint(1, 6)) for _ in range(6))
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
    """ Every accepted index 0..2047 has exactly 22 preimages; value >= 45056 is rejected. """
    counts = Counter()
    rejected = 0
    for value in range(6 ** 6):
        index = value // 22
        if index < mnemonic_generation.DICE_WORDLIST__WORDLIST_SIZE:
            counts[index] += 1
        else:
            rejected += 1

    # Uniform: each of the 2048 indices has exactly 22 preimages
    assert len(counts) == mnemonic_generation.DICE_WORDLIST__WORDLIST_SIZE
    assert set(counts.values()) == {22}

    # Exactly 45056 accepted and 1600 rejected (the hard floor for 6 dice). The accepted
    # count equals the rejection threshold: values [0, MIN_REJECTED_VALUE) are accepted.
    assert sum(counts.values()) == mnemonic_generation.DICE_WORDLIST__MIN_REJECTED_VALUE
    assert rejected == 6 ** 6 - mnemonic_generation.DICE_WORDLIST__MIN_REJECTED_VALUE


def test_dice_wordlist_invalid_input():
    """ Rolls must be exactly 6 dice of value 1-6; rejected rolls / bad counts raise. """
    for bad in ["12345", "1234567", "123457", "abcdef", ""]:
        with pytest.raises(ValueError):
            mnemonic_generation.dice_wordlist_roll_value(bad)

    # A rejected roll cannot be part of a mnemonic
    with pytest.raises(ValueError):
        mnemonic_generation.generate_mnemonic_from_dice_wordlist(DICE_WORDLIST_ROLLS_12[:-1] + ["666666"], 12)

    # Wrong number of words / rolls
    with pytest.raises(ValueError):
        mnemonic_generation.generate_mnemonic_from_dice_wordlist(DICE_WORDLIST_ROLLS_12, 24)
    with pytest.raises(ValueError):
        mnemonic_generation.generate_mnemonic_from_dice_wordlist(DICE_WORDLIST_ROLLS_12, 13)
