import itertools
import os
from importlib.resources import files

import Levenshtein
import numpy as np
from loguru import logger

from aiframe.aiframe.export.solver import Solver

from .. import ai_nlp
from ...utils.types import LocalCacheDict, load_cache


def translate(words):
    word1, word2 = words
    word1 = word1.replace(' ', ' ').replace('-', ' ').replace('-', ' ')
    word2 = word2.replace(' ', ' ').replace('-', ' ').replace('-', ' ')

    word1_norm = [chr_ for chr_ in word1.lower() if chr_ in all_symbols]
    word1 = ''.join(word1_norm)
    while '  ' in word1:
        word1 = word1.replace('  ', ' ')

    word2_norm = [chr_ for chr_ in word2.lower() if chr_ in all_symbols]
    word2 = ''.join(word2_norm)
    while '  ' in word2:
        word2 = word2.replace('  ', ' ')
    return differences(word1, word2)


def differences(string1, string2):
    max_words = 20
    levenshtein_grid = np.zeros((max_words, max_words,), dtype=np.float32)

    # solving words
    words1 = [word for word in string1.split(' ')[:20] if no_prepositions(word)]
    words2 = [word for word in string2.split(' ')[:20] if no_prepositions(word)]
    iterator = itertools.product(words1, words2)
    for i, words in enumerate(iterator):
        word1, word2 = words
        row = i // len(words2)
        col = i % len(words2)
        distance = Levenshtein.distance(word1, word2)
        levenshtein_grid[row, col] = 1 / (distance + 1)

    levenshtein_grid = levenshtein_grid.reshape((max_words ** 2,))
    matches1 = str_to_wordstats(string1)
    matches2 = str_to_wordstats(string2)
    concatted = np.concatenate([levenshtein_grid, matches1, matches2])
    return concatted


def str_to_wordstats(string):
    sequences = [ords.index(ord(char)) for char in string.lower()]
    matches = np.zeros((75,))
    for char in sequences:
        matches[char] += 1
    matches /= 20
    for i in range(matches.shape[0]):
        matches[i] = min(matches[i], 1)
    return matches


def no_prepositions(word):
    if len(word) < 3:
        return False
    if word in ('для', 'или', 'под', 'как', 'так',):
        return False
    return True


def softmax_to_result(layer):
    return layer[0] - layer[1]


def pairs_hasher(pairs):
    hash_ = ''
    for pair in pairs:
        left, right = pair
        hash_ += '%%' + left + '$$' + right
    return hash_


ord_iters = [[46, 32, 1104, 1105], range(48, 58), range(97, 123), range(1072, 1104)]
ords = list(itertools.chain(*ord_iters))
all_symbols = [chr(code) for code in ords]

ai_model = files(ai_nlp).joinpath('ai_model')
solver = Solver(ai_model, in_converter=translate,
                out_converter=softmax_to_result,
                timeout=180,
                remember_answers=True)
models_path = os.path.join(solver.model_name, 'assets', 'high_level_cache.pkl')
cache_dict = LocalCacheDict(models_path, hash_function=pairs_hasher)
