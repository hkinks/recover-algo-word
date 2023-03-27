#!/usr/bin/env python
import argparse
import difflib
import math
import sys
from typing import Tuple, Optional

import algosdk.account as account
import algosdk.mnemonic as mnemonic
from algosdk.wordlist import word_list_raw

bip39 = word_list_raw().split()
reported = {}


class AlgoRecovery:
    def __init__(self, words: list, address: str = "", explore: bool = False, rotate: bool = True):
        self.address = address
        self._explore = explore
        self._rotate = rotate

        self.words = [w.lower() for w in words]
        self._original_words = self.words.copy()

        self.found: list = []

    @property
    def choices(self):
        return [bip39_choices(w.lower()) for w in self.words]

    @property
    def count(self):
        return count_choices(self.choices)

    def recover_with_rotate(self):
        print(f"Starting rotating recovery for {self.words}")
        if self._rotate:
            n_words = len(self.words)
            for _ in range(n_words + 1):
                print(f"Trying: {' '.join(self.words)}")
                self.words = [self.words[-1]] + self.words[:-1]
                self.recover()

    def recover(self):
        if len(self.words) == 25:
            self.recovery_25()
        if len(self.words) == 24:  # Missing one word. Insert _ in each slot
            self.recovery_24()
        if len(self.words) == 23:
            self.recovery_23()
        if 1 < len(self.words) <= 22:
            print("No. I can't work miracles. " +
                  "Finding >= 3 self.words is only possible if _ indicates their positions.")
        if len(self.words) == 1:
            # Useful for debugging a pattern
            print(str(self.choices[0]))
        elif self.count == 0:
            print("Unable to find candidates to check.")
        if len(self.found) > 1 and not self.address:
            print("Multiple possibilities. Narrow possibilities with --address")

    def recovery_23(self):
        # This is at least 600 * 4M = 2.5B possibilities (more if any
        # words have wildcards).  Utterly hopeless without an
        # --address to winnow them down, and will take days anyway.
        if self.count > 0:
            print(f"Trying {24 * 25 * 2048 * 2048 * self.count} possibilities")
            for lo, hi in index_pairs(25):
                wild = self.choices[:lo] + [bip39] + self.choices[lo:hi] + [bip39] + self.choices[hi:]
                self.check_choices(wild)

    def recovery_24(self):
        if self.count > 0:
            print(f"Trying {25 * 2048 * self.count} possibilities")
            for i in range(25):
                wild = self.choices[:i] + [bip39] + self.choices[i:]
                self.check_choices(wild)

    def recovery_25(self):
        if self.count == 1:  # 25 words given, no wildcarding
            if self.check_choices(self.choices) == 0:
                print("Bad checksum. Finding similar mnemonics")
                print(f" Trying swaps of all pairs. {25 * 24} possibilities")
                # Maybe this should be a switch that affects all
                # check_self.choices calls.  That would change all our
                # reporting about possibility self.count, but it would be
                # cool to always handle swaps.
                for lo, hi in index_pairs(25):
                    self.choices[hi], self.choices[lo] = self.choices[lo], self.choices[hi]
                    self.check_choices(self.choices)
                    self.choices[hi], self.choices[lo] = self.choices[lo], self.choices[hi]
                if len(self.found) > 0:  # Add a switch to keep going?
                    return
                print(f" Trying to replace each word. {25 * 2048} possibilities")
                for i in range(25):
                    wild = self.choices[:i] + [bip39] + self.choices[i + 1:]
                    self.check_choices(wild)
        elif self.count > 1:
            print(f"Trying {self.count} possibilities")
            self.check_choices(self.choices)

    def get_candidate(self, candidate: list, prefix: str = "") -> Optional[Tuple[str, str]]:
        phrase = " ".join([mnemonic.index_to_word[mnemonic.word_to_index[c]]
                           for c in candidate])
        sk = mnemonic.to_private_key(phrase)
        address = account.address_from_private_key(sk)
        if address.startswith(prefix):
            if self._explore and not has_algos(address):
                return
            self.found.append([address, phrase])
            return address, phrase

    def check_choices(self, choices):
        found_count = 0
        for c in candidates(choices):
            if chk25(c):
                found_count += 1
                candidate = self.get_candidate(c, self.address.upper())
                if candidate:
                    print(candidate)
        return found_count

    def start(self):
        if self._rotate:
            self.recover_with_rotate()
        else:
            self.recover()


def bip39_choices(pattern):
    if pattern in mnemonic.word_to_index:
        return [pattern]

    comma = pattern.find(',')
    if comma >= 0:
        return bip39_choices(pattern[:comma]) + bip39_choices(pattern[comma + 1:])

    underscore = pattern.find('_')
    if underscore >= 0:
        if underscore > 3:
            print(f"Useless _ in '{pattern}' " +
                  "bip39 words are unique in the first four characters.")
        prefix = pattern[:underscore]
        return [w for w in bip39 if w.startswith(prefix)]

    if pattern.endswith("~"):
        return difflib.get_close_matches(pattern[:-1], bip39, 6, .6)

    if pattern not in reported:
        print(f"{pattern} is not a bip39 word.")

    if len(pattern) > 4 and pattern[:4] in mnemonic.word_to_index:
        word = mnemonic.index_to_word[mnemonic.word_to_index[pattern[:4]]]
        if pattern not in reported:
            print(f"Using {word} for {pattern}.")
        reported[pattern] = 1
        return [word]

    matches = difflib.get_close_matches(pattern, bip39, 6, .6)
    if matches:
        print(f"Consider '{','.join(matches)}' or equivalently '{pattern}~'.")

    return []


def chk25(words):
    check = mnemonic.word_to_index[words[-1]]
    m_indexes = [mnemonic.word_to_index[w] for w in words[:-1]]
    m_bytes = mnemonic._to_bytes(m_indexes)
    if not m_bytes[-1:] == b'\x00':
        return False
    return check == mnemonic._checksum(m_bytes[:32])


def candidates(options):
    if not options:
        yield []
        return

    head = options[0]
    for candidate in candidates(options[1:]):
        for h in head:
            yield [h, *candidate]


def has_algos(addr):
    import explore
    explore.active(addr)


def count_choices(choices):
    return math.prod([len(c) for c in choices])


def index_pairs(top):
    for lo in range(top - 1):
        for hi in range(lo + 1, top):
            yield lo, hi


def parse_args():
    parser = argparse.ArgumentParser(
        description='Recover Algorand mnemonics when some is missing or wrong.')
    parser.add_argument('words', metavar='N', nargs='+',
                        help='sequence of of words in account mnemonic')
    parser.add_argument('--address', default='',
                        help='the account being recovered (prefix), if known')
    parser.add_argument('--explore', action='store_true',
                        help='use algoexplorer API to filter inactive accounts')
    parser.add_argument('--rotate', action='store_true',
                        help='try rotations')
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    r = AlgoRecovery(args.words, args.address, args.explore, args.rotate)
    r.start()
