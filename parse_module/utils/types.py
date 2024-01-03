import json
import pickle
import sqlite3
import threading
import time
from typing import Callable

from parse_module.utils import provision
from parse_module.utils.provision import multi_try


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


class LocalDict(dict):
    def __init__(self, path):
        super().__init__()
        self.path = path
        self._lock = threading.Lock()

        conn, cursor = self._connect_db()
        cursor.execute('CREATE TABLE IF NOT EXISTS the_table '
                       '(id INTEGER PRIMARY KEY, data TEXT)')
        conn.commit()

        cursor.execute('SELECT * FROM the_table')
        fetched = cursor.fetchall()
        conn.close()

        for key, value in fetched:
            loaded = json.loads(value)
            dict.__setitem__(self, key, loaded)

    def connect_db(self):
        return provision.multi_try(self._connect_db, tries=10, raise_exc=False,
                                   print_errors=False, multiplier=1.02)

    def _connect_db(self):
        conn = sqlite3.connect(self.path)
        cursor = conn.cursor()
        return conn, cursor

    def wait_and_get(self, key: int, timeout=None, delay=1):
        start_time = time.time()
        while True:
            try:
                return self.__getitem__(key)
            except KeyError:
                if timeout:
                    if time.time() - start_time > timeout:
                        raise KeyError(key)
                fetched = None

                try:
                    self._lock.acquire()
                    connect = self.connect_db()
                    if connect is not provision.TryError:
                        conn, cursor = connect
                        cursor.execute('SELECT data FROM the_table '
                                       f'WHERE id={key}')
                        fetched = cursor.fetchall()
                        conn.close()
                finally:
                    self._lock.release()
                if fetched:
                    loaded = json.loads(fetched[0][0])
                    dict.__setitem__(self, key, loaded)
                    return self.__getitem__(key)

                time.sleep(delay)

    def __setitem__(self, key: int, value):
        try:
            self._lock.acquire()
            if key in self:
                return
            dict.__setitem__(self, key, value)

            connect = self.connect_db()
            if connect is provision.TryError:
                raise provision.TryError('Database is blocked')
            conn, cursor = connect

            value = json.dumps(value)
            cursor.execute(f"INSERT INTO the_table (id, data) VALUES ({key}, '{value}')")
            conn.commit()
            conn.close()
        finally:
            self._lock.release()


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
        try:
            with open(path, 'wb+') as f:
                pass
        except Exception as err:
            raise RuntimeError(f'File {path} cannot be created: {err}')
    return from_file
