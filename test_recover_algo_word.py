import pytest

from recover_algo_word import bip39_choices, chk25, candidates, count_choices, index_pairs, AlgoRecovery

EXPECTED_ADDRESS = "IYSW3K34LAQY6OTQ2E65QOPX55HNN6YZVPQIZN7AM7AEQSEXC72E2W3KXI"
CORRECT_WORDS = ["tent", "pen", "universe", "toddler", "eager", "boil", "deliver", "funny", "naive", "pyramid",
                 "endless", "safe", "slow", "stereo", "road", "glow", "apple", "asthma", "inflict", "public", "cancel",
                 "idea", "chat", "absorb", "prize"]

choices = [[word] for word in CORRECT_WORDS]


class TestBip39:
    def test_bip39_choices_with_pattern_in_mnemonic_word_to_index(self):
        pattern = "abandon"
        expected = ["abandon"]
        result = bip39_choices(pattern)
        assert result == expected

    def test_bip39_choices_with_comma_in_pattern(self):
        pattern = "abandon,absorb"
        expected = ["abandon", "absorb"]
        result = bip39_choices(pattern)
        assert result == expected

    def test_bip39_choices_with_underscore_in_pattern_first_four_characters(self):
        pattern = "abo_"
        expected = ["about", "above"]
        result = bip39_choices(pattern)
        assert result == expected

    def test_bip39_choices_with_tilde_in_pattern(self):
        pattern = "cake~"
        expected = ["cake", "make", "lake", "cave", "case", "cage"]
        result = bip39_choices(pattern)
        assert result == expected

    def test_bip39_choices__unkown_word(self):
        pattern = "foobar"
        expected = []
        result = bip39_choices(pattern)
        assert result == expected


def test_chk25():
    result = chk25(CORRECT_WORDS)
    assert result is True


@pytest.mark.parametrize("options, expected", [
    ([[1, 2], [3, 4], [5, 6]], [[1, 3, 5], [2, 3, 5], [1, 4, 5], [2, 4, 5], [1, 3, 6], [2, 3, 6], [1, 4, 6], [2, 4, 6]])
])
def test_candidates(options, expected):
    result = candidates(options)
    assert list(result) == expected


def test_candidates__empty():
    result = candidates([])
    assert list(result) == [[]]


@pytest.mark.parametrize("choices, expected", [
    (choices, 1),
    ([["test", "test2"], choices[1:]], 48),
    ([["test"], choices[1:]], 24),
    ([["test", "foobar"]] + [a for a in choices[1:]], 2)
])
def test_count_choices(choices, expected):
    result = count_choices(choices)
    assert result == expected


@pytest.mark.parametrize("top, expected", [
    (4, [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)])
])
def test_index_pairs(top, expected):
    result = list(index_pairs(top))
    assert result == expected


class TestAlgoRecovery:
    def test_recover_24(self):
        r = AlgoRecovery(CORRECT_WORDS[:-1])
        r.recovery_24()
        res = r.found[0]
        assert res[0] == EXPECTED_ADDRESS
        assert res[1] == " ".join(CORRECT_WORDS)

    def test_check_choices(self):
        r = AlgoRecovery(CORRECT_WORDS)
        result = r.check_choices(choices)
        assert result == 1

    def test_get_candidate(self):
        r = AlgoRecovery(CORRECT_WORDS)
        res = r.get_candidate(CORRECT_WORDS)
        assert res[0] == EXPECTED_ADDRESS
        assert res[1] == " ".join(CORRECT_WORDS)

    def test_rotate_25(self):
        r = AlgoRecovery([CORRECT_WORDS[-1]] + CORRECT_WORDS[:-1], rotate=True)
        r.recover_with_rotate()
        assert [EXPECTED_ADDRESS, " ".join(CORRECT_WORDS)] in r.found

    def test_rotate_24(self):
        r = AlgoRecovery([CORRECT_WORDS[-2]] + CORRECT_WORDS[:-2], rotate=True)
        r.recover_with_rotate()
        assert [EXPECTED_ADDRESS, " ".join(CORRECT_WORDS)] in r.found
