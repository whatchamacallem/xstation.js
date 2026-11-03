# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests of the server substrate's largest database on scratch roots under
# build/: a database that `kv_put` fills with values of `overflow_bytes`,
# each kept in its row, until the write past `blob_max` fails with SQLite's
# full error, then its limit read through `sql_run`, its file at most
# `blob_max`, its rows still read, and the limit again once it is opened
# again; and a `sql_run` that sets the page limit refused by the store's
# authorizer, the limit read back as it was. The texts of the full and the
# authorization errors are the gold's.

import harness, os, sqlite3, substrate, tempfile, unittest

# The checkout's build directory, where each test makes its scratch roots.
_BUILD_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "build"
)

# The id of this module's gold, in its own `test_setting_` file.
_GOLD_ID = "python.test_substrate_limit"

# The `overflow_bytes` of the settings, the largest value kept in its row.
_OVERFLOW_BYTES: int = harness.setting_get("overflow_bytes")

# The `blob_max` of the settings, the largest database file.
_BLOB_MAX: int = harness.setting_get("blob_max")

# A value of exactly `overflow_bytes`, which stays in its row.
_VALUE_EXACT = bytes(index % 256 for index in range(_OVERFLOW_BYTES))

# One put more of `_VALUE_EXACT` than `blob_max` holds without overhead.
_PUTS_MAX = _BLOB_MAX // _OVERFLOW_BYTES + 1

# The database the tests fill.
_DATABASE = "alpha"

# The statements that read a connection's page size and page limit.
_LIMIT_STATEMENTS = [
    substrate.SqlStatement("PRAGMA page_size", []),
    substrate.SqlStatement("PRAGMA max_page_count", []),
]

# The statements that set the page limit, each refused, in the gold.
_LIMIT_SETTERS: list[str] = harness.gold_get(f"{_GOLD_ID}.limit_setters")


# A text of this module's gold.
def _text_get(name: str) -> str:
    text: str = harness.gold_get(f"{_GOLD_ID}.texts.{name}")
    return text


# Makes a scratch root under build/, removed when the test ends.
def _root_make(case: unittest.TestCase) -> str:
    os.makedirs(_BUILD_PATH, exist_ok=True)
    return case.enterContext(tempfile.TemporaryDirectory(dir=_BUILD_PATH))


# Closes every database a store has open.
def _store_close(store: substrate.Store) -> None:
    for name in store.db_list():
        store.db_close(name)


# The ref of the fill's value of an index.
def _fill_ref(index: int) -> str:
    return f"/{_DATABASE}/fill/{index:03d}"


# The bytes the limit of the database's connection allows, by `sql_run`.
def _limit_bytes(store: substrate.Store) -> int:
    page_size, page_count = store.sql_run(_DATABASE, _LIMIT_STATEMENTS)
    size: int = page_size.rows[0][0] * page_count.rows[0][0]
    return size


# The database filled to its limit.
class TestFull(unittest.TestCase):
    # Asserts the error is SQLite's full error with the gold's text.
    def full_assert(self, error: sqlite3.OperationalError) -> None:
        self.assertEqual(error.sqlite_errorcode, sqlite3.SQLITE_FULL)
        self.assertEqual(str(error), _text_get("full"))

    # Puts until the put past `blob_max` fails full, giving the count put.
    def fill_full(self, store: substrate.Store) -> int:
        count = 0
        with self.assertRaises(sqlite3.OperationalError) as caught:
            for index in range(_PUTS_MAX):
                store.kv_put(_fill_ref(index), _VALUE_EXACT)
                count = index + 1
        self.full_assert(caught.exception)
        return count

    # The put past `blob_max` fails full, and the file, rows and limit hold.
    def test_full_refused(self) -> None:
        root = _root_make(self)
        store = substrate.Store(root, _OVERFLOW_BYTES, _BLOB_MAX)
        self.addCleanup(_store_close, store)
        store.db_create(_DATABASE)
        self.assertEqual(_limit_bytes(store), _BLOB_MAX)
        count = self.fill_full(store)
        keys = [f"fill/{index:03d}" for index in range(count)]
        rows = store.kv_list(_DATABASE, "fill/")
        self.assertEqual([row.key for row in rows], keys)
        self.assertEqual(store.kv_get(_fill_ref(0)).data, _VALUE_EXACT)
        last = store.kv_get(_fill_ref(count - 1))
        self.assertEqual(last.data, _VALUE_EXACT)
        store.db_close(_DATABASE)
        path = os.path.join(root, _DATABASE + ".sqlite")
        self.assertLessEqual(os.path.getsize(path), _BLOB_MAX)
        store.db_open(_DATABASE)
        self.assertEqual(_limit_bytes(store), _BLOB_MAX)
        self.assertEqual(store.kv_list(_DATABASE, "fill/"), rows)
        with self.assertRaises(sqlite3.OperationalError) as caught:
            store.kv_put(_fill_ref(count), _VALUE_EXACT)
        self.full_assert(caught.exception)
        self.assertEqual(store.kv_list(_DATABASE, "fill/"), rows)


# The page limit, which only the store sets.
class TestLimitSet(unittest.TestCase):
    # Each statement that sets the limit is refused, and the limit holds.
    def test_limit_refused(self) -> None:
        root = _root_make(self)
        store = substrate.Store(root, _OVERFLOW_BYTES, _BLOB_MAX)
        self.addCleanup(_store_close, store)
        store.db_create(_DATABASE)
        for sql in _LIMIT_SETTERS:
            with self.subTest(sql=sql):
                statement = substrate.SqlStatement(sql, [])
                with self.assertRaises(sqlite3.DatabaseError) as caught:
                    store.sql_run(_DATABASE, [statement])
                error = caught.exception
                self.assertEqual(error.sqlite_errorcode, sqlite3.SQLITE_AUTH)
                self.assertEqual(str(error), _text_get("denied"))
                self.assertEqual(_limit_bytes(store), _BLOB_MAX)
