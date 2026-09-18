import hashlib
import unicodedata

from embit import bip39
from seedsigner.models.settings_definition import SettingsConstants
from seedsigner.models.seed import Seed

"""
    This is SeedSigner's internal mnemonic generation utility.
     
    It can also be run as an independently-executable CLI to facilitate external
    verification of SeedSigner's results for a given input entropy.

    see: docs/dice_verification.md (the "Command Line Tool" section).
"""

DICE__NUM_ROLLS__12WORD = 50
DICE__NUM_ROLLS__24WORD = 99

# "Dice wordlist" method: map each 5-dice roll directly to one BIP-39 wordlist word
# (no hashing). See docs/dice_wordlist.md for the algorithm and the proof of exact
# uniformity. 6^5 = 7776 possible rolls; a roll is accepted when value // 3 < 2048
# (i.e. value <= 6143) and rejected when value >= 6144.
DICE_WORDLIST__DICE_PER_WORD = 5
DICE_WORDLIST__FACES = 6
DICE_WORDLIST__WORDLIST_SIZE = 2048
DICE_WORDLIST__MAX_ACCEPTED_VALUE = (DICE_WORDLIST__WORDLIST_SIZE - 1) * 3 + 2  # 6143
DICE_WORDLIST__MIN_REJECTED_VALUE = DICE_WORDLIST__WORDLIST_SIZE * 3            # 6144



def calculate_checksum(mnemonic: list | str, wordlist_language_code: str = SettingsConstants.WORDLIST_LANGUAGE__ENGLISH) -> list[str]:
    """
        Provide 12- or 24-word mnemonic, returns complete mnemonic w/checksum as a list.

        Mnemonic may be a list of words or a string of words separated by spaces or commas.

        If 11- or 23-words are provided, append word `0000` to end of list as temp final
        word.
    """
    if type(mnemonic) == str:
        import re
        # split on commas or spaces
        mnemonic = re.findall(r'[^,\s]+', mnemonic)

    if len(mnemonic) in [11, 23]:
        temp_final_word = Seed.get_wordlist(wordlist_language_code)[0]
        mnemonic.append(temp_final_word)

    if len(mnemonic) not in [12, 24]:
        raise Exception("Pass in a 12- or 24-word mnemonic")
    
    # Work on a copy of the input list
    mnemonic_copy = mnemonic.copy()

    # Convert the resulting mnemonic to bytes, but we `ignore_checksum` validation
    # because we assume it's incorrect since we either let the user select their own
    # final word OR we injected the 0000 word from the wordlist.
    mnemonic_bytes = bip39.mnemonic_to_bytes(unicodedata.normalize("NFKD", " ".join(mnemonic_copy)), ignore_checksum=True, wordlist=Seed.get_wordlist(wordlist_language_code))

    # This function will convert the bytes back into a mnemonic, but it will also
    # calculate the proper checksum bits while doing so. For a 12-word seed it will just
    # overwrite the last 4 bits from the above result with the checksum; for a 24-word
    # seed it'll overwrite the last 8 bits.
    #
    # Pass the requested wordlist so the result is expressed in the same language the
    # mnemonic was entered in (embit defaults to English otherwise).
    return bip39.mnemonic_from_bytes(mnemonic_bytes, wordlist=Seed.get_wordlist(wordlist_language_code)).split()



def generate_mnemonic_from_bytes(entropy_bytes, wordlist_language_code: str = SettingsConstants.WORDLIST_LANGUAGE__ENGLISH) -> list[str]:
    return bip39.mnemonic_from_bytes(entropy_bytes, wordlist=Seed.get_wordlist(wordlist_language_code)).split()



def generate_mnemonic_from_dice(roll_data: str, wordlist_language_code: str = SettingsConstants.WORDLIST_LANGUAGE__ENGLISH) -> list[str]:
    """
        Takes a string of 50 or 99 dice rolls and returns a 12- or 24-word mnemonic.

        Uses the iancoleman.io/bip39 and bitcoiner.guide/seed "Base 10" or "Hex" mode approach:
        * dice rolls are treated as string data.
        * hashed via SHA256.

        Important note: This method is NOT compatible with iancoleman's "Dice" mode.
    """
    entropy_bytes = hashlib.sha256(roll_data.encode()).digest()

    if len(roll_data) == DICE__NUM_ROLLS__12WORD:
        # 12-word mnemonic; only use 128bits / 16 bytes
        entropy_bytes = entropy_bytes[:16]

    # Return as a list
    return bip39.mnemonic_from_bytes(entropy_bytes, wordlist=Seed.get_wordlist(wordlist_language_code)).split()



def generate_mnemonic_from_coin_flips(coin_flips: str, wordlist_language_code: str = SettingsConstants.WORDLIST_LANGUAGE__ENGLISH) -> list[str]:
    """
        Takes a string of 128 or 256 0s and 1s and returns a 12- or 24-word mnemonic.

        Uses the iancoleman.io/bip39 and bitcoiner.guide/seed "Binary" mode approach:
        * binary digit stream is treated as string data.
        * hashed via SHA256.
    """
    entropy_bytes = hashlib.sha256(coin_flips.encode()).digest()

    if len(coin_flips) == 128:
        # 12-word mnemonic; only use 128bits / 16 bytes
        entropy_bytes = entropy_bytes[:16]

    # Return as a list
    return bip39.mnemonic_from_bytes(entropy_bytes, wordlist=Seed.get_wordlist(wordlist_language_code)).split()



def get_partial_final_word(coin_flips: str, wordlist_language_code: str = SettingsConstants.WORDLIST_LANGUAGE__ENGLISH) -> str:
    """ Look up the partial final word for the given coin flips.
        7 coin flips: 0101010 + **** where the final 4 bits will be replaced with the checksum
        3 coin flips: 010 + ******** where the final 8 bits will be replaced with the checksum
    """
    binary_string = coin_flips + "0" * (11 - len(coin_flips))
    wordlist_index = int(binary_string, 2)

    return Seed.get_wordlist(wordlist_language_code)[wordlist_index]



def dice_wordlist_roll_value(roll: str) -> int:
    """
        Convert a 5-dice roll to its base-6 value.

        `roll` is a string of exactly 5 characters, each '1'..'6'. The first character
        is the most significant digit (the first die rolled).

        e.g. "41115" -> 3892
    """
    if len(roll) != DICE_WORDLIST__DICE_PER_WORD:
        raise ValueError(f"roll must be exactly {DICE_WORDLIST__DICE_PER_WORD} dice; got {len(roll)}")
    if any(digit not in "123456" for digit in roll):
        raise ValueError("roll must contain only dice values 1-6")

    value = 0
    for digit in roll:
        value = value * DICE_WORDLIST__FACES + (int(digit) - 1)
    return value



def dice_wordlist_roll_index(roll: str) -> int | None:
    """
        Map a 5-dice roll to a BIP-39 wordlist index (0..2047), or None if the roll is
        rejected and must be re-rolled.

        The roll's base-6 value (0..7775) is divided by 3. An index >= 2048 (base-6
        value >= 6144) is rejected. Every accepted index 0..2047 has exactly 3 preimage
        rolls, so an accepted word is exactly uniform.
    """
    value = dice_wordlist_roll_value(roll)
    if value >= DICE_WORDLIST__MIN_REJECTED_VALUE:
        return None
    return value // 3



def dice_wordlist_roll_word(roll: str, wordlist_language_code: str = SettingsConstants.WORDLIST_LANGUAGE__ENGLISH) -> str | None:
    """
        Return the wordlist word for an accepted 5-dice roll, or None if the roll is
        rejected.
    """
    index = dice_wordlist_roll_index(roll)
    if index is None:
        return None
    return Seed.get_wordlist(wordlist_language_code)[index]



def generate_mnemonic_from_dice_wordlist(rolls: list[str], num_words: int, wordlist_language_code: str = SettingsConstants.WORDLIST_LANGUAGE__ENGLISH) -> list[str]:
    """
        Build a BIP-39 mnemonic from a list of accepted 5-dice rolls.

        Each roll maps to exactly one uniform wordlist word. The final word is then
        corrected to satisfy the BIP-39 checksum (reusing calculate_checksum()).

        Args:
        * rolls: list of `num_words` roll strings (5 chars each, values 1-6)
        * num_words: 12 or 24
    """
    if num_words not in (12, 24):
        raise ValueError("num_words must be 12 or 24")
    if len(rolls) != num_words:
        raise ValueError(f"expected {num_words} rolls; got {len(rolls)}")

    wordlist = Seed.get_wordlist(wordlist_language_code)
    words = []
    for roll in rolls:
        index = dice_wordlist_roll_index(roll)
        if index is None:
            raise ValueError("all rolls must be in range; a rejected roll was passed in")
        words.append(wordlist[index])

    return calculate_checksum(words, wordlist_language_code)
