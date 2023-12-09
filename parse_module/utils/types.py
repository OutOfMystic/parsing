import pickle
from typing import Callable

from loguru import logger


class HashDict:
    def __init__(self, hash_function=hash):
        self.hash_function = hash_function
        self._hash_to_key = dict()
        self._hash_to_value = dict()

    def __setitem__(self, key, value):
        hash_ = self.hash_function(key)
        self._hash_to_key[hash_] = key
        self._hash_to_value[hash_] = value

    def __getitem__(self, item):
        hash_ = self.hash_function(item)
        try:
            # logger.debug(f'{item} {hash_} {list(self._hash_to_key.keys())} {list(self._hash_to_key.values())}')
            return self._hash_to_value[hash_]
        except KeyError:
            raise KeyError(f'{item} with hash {hash_}')

    def __delitem__(self, key):
        hash_ = self.hash_function(key)
        del self._hash_to_key[hash_]
        del self._hash_to_value[hash_]

    def __contains__(self, item):
        return self.hash_function(item) in self._hash_to_key

    def __iter__(self):
        for key in self._hash_to_key.values():
            yield key

    def get(self, key, default=None):
        if key in self:
            return self[key]
        else:
            return default

    def keys(self):
        for key in self._hash_to_key.values():
            yield key

    def values(self):
        for value in self._hash_to_value.values():
            yield value

    def items(self):
        for hash_, key in self._hash_to_key.items():
            yield key, self._hash_to_value[hash_]


class LocalCacheDict(HashDict):
    def __init__(self, path, hash_function: Callable):
        super().__init__(hash_function=hash_function)
        self.path = path
        cache = load_cache(self.path)
        for key, value in cache.items():
            super().__setitem__(key, value)

    def __setitem__(self, key, value):
        normal_dict = {item: value for item, value in self.items()}
        with open(self.path, 'wb+') as f:
            pickle.dump(normal_dict, f)
        super().__setitem__(key, value)


class LowerDict(HashDict):
    def __init__(self):
        super().__init__(hash_function=lambda item: item.lower())


class DateDict(HashDict):
    def __init__(self):
        super().__init__(hash_function=lambda item: item.__str__())


def load_cache(path):
    from_file = {}
    try:
        with open(path, 'rb') as f:
            from_file = pickle.load(f)
    except Exception as err:
        logger.info(f'Pickle file was not found, created an empty dict: {err}')
    return from_file
