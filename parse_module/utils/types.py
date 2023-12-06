import json
import pickle

from loguru import logger


class HashDict(dict):
    def __init__(self, hash_function=hash, **kwargs):
        super().__init__(**kwargs)
        self.hash_function = hash_function
        self.aliases = {}

    def __setitem__(self, key, value):
        hash_ = self.hash_function(key)
        self.aliases[hash_] = key
        super().__setitem__(key, value)

    def __getitem__(self, item):
        hash_ = self.hash_function(item)
        try:
            # logger.debug(self.aliases.keys())
            key = self.aliases[hash_]
            return super().__getitem__(key)
        except KeyError:
            raise KeyError(f'{item} with hash {hash_}')

    def __contains__(self, item):
        return self.hash_function(item) in self.aliases


class LocalCacheDict(HashDict):
    def __init__(self, path, hash_function=hash, **kwargs):
        super().__init__(hash_function=hash_function, **kwargs)
        self.path = path
        cache = load_cache(self.path)
        for key, value in cache.items():
            super().__setitem__(key, value)

    def __setitem__(self, key, value):
        normal_dict = dict(self)
        with open(self.path, 'wb+') as f:
            pickle.dump(normal_dict, f)
        super().__setitem__(key, value)


class LowerDict(HashDict):
    def __init__(self, **kwargs):
        super().__init__(hash_function=lambda item: item.lower(), **kwargs)


def load_cache(path):
    from_file = {}
    try:
        with open(path, 'rb') as f:
            from_file = pickle.load(f)
    except Exception as err:
        logger.info(f'Pickle file was not found, created an empty dict: {err}')
    return from_file
