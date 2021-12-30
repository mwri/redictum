"""
Test cases for the rdbms storage adapter.

In principal these test cases should be adaptable to any storage adapter with minimal change
by replacing the `existing_store` fixture, and changing the class in `test_constructor_returns_store`.
The singleton tests `test_constructor_is_singleton` and `test_constructor_diff_objs_per_dsn` may
or may not be applicable to other adapters.
"""


import re
from datetime import datetime

import pytest
import sqlalchemy

from redictum import Dictum
from redictum.store import RdbmsStore


@pytest.fixture
def existing_store():
    store = RdbmsStore("sqlite:///:memory:")

    for c in store.load_all():
        store.delete(c)

    return store


@pytest.fixture
def new_dictum():
    class TestDictum(Dictum):
        pass

    return TestDictum({})


@pytest.fixture
def new_dictums_6list():
    class TestDictum(Dictum):
        ttl = 2000

    return [
        TestDictum({"is": "past", "order": 1}).slide_ts_window(-4000),
        TestDictum({"is": "past", "order": 2}).slide_ts_window(-3000),
        TestDictum({"is": "present", "order": 3}).slide_ts_window(-100),
        TestDictum({"is": "present", "order": 4}).slide_ts_window(-200),
        TestDictum({"is": "future", "order": 5}).slide_ts_window(3000),
        TestDictum({"is": "future", "order": 6}).slide_ts_window(4000),
    ]


@pytest.fixture
def new_dictums_6overlappinglist():
    class TestDictum(Dictum):
        ttl = 2000
        unique_by = ("set1", "set2")

    return [
        TestDictum({"is": "present1", "set1": 1, "set2": 4}),
        TestDictum({"is": "present2", "set1": 1, "set2": 4}),
        TestDictum({"is": "present3", "set1": 2, "set2": 5}),
        TestDictum({"is": "present4", "set1": 2, "set2": 5}),
        TestDictum({"is": "present5", "set1": 2, "set2": 6}),
        TestDictum({"is": "present6", "set1": 3, "set2": 6}),
    ]


def test_constructor_returns_store():
    """Check constructor returns a store object."""

    assert isinstance(RdbmsStore("sqlite:///:memory:"), RdbmsStore)


def test_constructor_is_singleton():
    """Check store instances are the same object for the same DSN."""

    store1 = RdbmsStore("sqlite:///:memory:")
    store2 = RdbmsStore("sqlite:///:memory:")

    assert id(store1) == id(store2)


def test_constructor_diff_objs_per_dsn():
    """Check store instances are different for different DSNs."""

    store1 = RdbmsStore("sqlite:///:memory:?a=1")
    store2 = RdbmsStore("sqlite:///:memory:?a=2")

    assert id(store1) != id(store2)


def test_commit_sets_id(existing_store, new_dictum):
    """Check committing a dictum sets it's ID."""

    assert new_dictum.id is None
    existing_store.commit(new_dictum)

    assert isinstance(new_dictum.id, int)


def test_load_by_id_loads_applied_dictum(existing_store, new_dictum):
    """Check load_by_id returns a committed dictum given the ID."""

    existing_store.commit(new_dictum)
    dictum = existing_store.load_by_id(new_dictum.id)

    assert id(new_dictum) != id(dictum)
    assert new_dictum == dictum


def test_load_by_id_loads_applied_dictum(existing_store):
    """Check load_by_id None if ID does not exist."""

    assert existing_store.load_by_id(1234567890) is None


def test_load_by_udigest_loads_dictum(existing_store, new_dictum):
    """Check load_by_udigest returns a committed dictum given the binary digest value."""

    existing_store.commit(new_dictum)
    dictum = existing_store.load_by_udigest(new_dictum.udigest)

    assert id(new_dictum) != id(dictum)
    assert new_dictum == dictum


def test_load_valid_loads_dictums_currently_valid(existing_store, new_dictums_6list):
    """Check valid_dictums returns dictums which "valid" (between "from" and "to") of the current time."""

    for new_dictum in new_dictums_6list:
        existing_store.commit(new_dictum)

    valid_dictums = existing_store.load_valid()

    assert all([dictum.data["is"] == "present" for dictum in valid_dictums])
    assert set([c.data["order"] for c in valid_dictums]) == {3, 4}


def test_load_valid_loads_dictums_valid_at_ts(existing_store, new_dictums_6list):
    """Check valid_dictums returns dictums which "valid" (between "from" and "to") for a given timestamp."""

    for new_dictum in new_dictums_6list:
        existing_store.commit(new_dictum)

    valid_dictums = existing_store.load_valid(datetime.now().timestamp() - 3000)

    assert all([dictum.data["is"] == "past" for dictum in valid_dictums])
    assert set([c.data["order"] for c in valid_dictums]) == {1, 2}


def test_load_expired_loads_dictums_currently_expired(existing_store, new_dictums_6list):
    """Check load_expired returns dictums which expire before the current time."""

    for new_dictum in new_dictums_6list:
        existing_store.commit(new_dictum)

    expired_dictums = existing_store.load_expired()

    assert all([dictum.data["is"] == "past" for dictum in expired_dictums])
    assert set([c.data["order"] for c in expired_dictums]) == {1, 2}


def test_load_expired_loads_dictums_expired_at_ts(existing_store, new_dictums_6list):
    """Check load_expired returns dictums which expire before the given timestamp."""

    for new_dictum in new_dictums_6list:
        existing_store.commit(new_dictum)

    expired_dictums = existing_store.load_expired(datetime.now().timestamp() + 5500)

    assert set([c.data["order"] for c in expired_dictums]) == {1, 2, 3, 4, 5}


def test_load_future_loads_dictums_currently_future(existing_store, new_dictums_6list):
    """Check load_future returns dictums in the future of the current time."""

    for new_dictum in new_dictums_6list:
        existing_store.commit(new_dictum)

    future_dictums = existing_store.load_future()

    assert all([dictum.data["is"] == "future" for dictum in future_dictums])
    assert set([c.data["order"] for c in future_dictums]) == {5, 6}


def test_load_future_loads_dictums_future_at_ts(existing_store, new_dictums_6list):
    """Check load_future returns dictums in the future of the given timestamp."""

    for new_dictum in new_dictums_6list:
        existing_store.commit(new_dictum)

    future_dictums = existing_store.load_future(datetime.now().timestamp() + 3500)

    assert set([c.data["order"] for c in future_dictums]) == {6}


def test_commit_updates_existing_dictum_if_not_unique(existing_store, new_dictums_6overlappinglist):
    """
    Take the six sample dictums from new_dictums_6overlappinglist and commit them, "present2" overlaps
    with "present1" and "present4" overlaps with "present3" (in so much that the data which defines
    them as unique is the same), so committing those should not result in a new dictum, but an update
    to an existing one.
    """

    assert len(existing_store.load_valid()) == 0

    existing_store.commit(new_dictums_6overlappinglist[0])
    assert len(existing_store.load_valid()) == 1
    assert existing_store.load_by_id(new_dictums_6overlappinglist[0].id).data["is"] == "present1"

    existing_store.commit(new_dictums_6overlappinglist[1])
    assert len(existing_store.load_valid()) == 1
    assert existing_store.load_by_id(new_dictums_6overlappinglist[0].id).data["is"] == "present2"

    existing_store.commit(new_dictums_6overlappinglist[2])
    assert len(existing_store.load_valid()) == 2
    assert existing_store.load_by_id(new_dictums_6overlappinglist[2].id).data["is"] == "present3"

    existing_store.commit(new_dictums_6overlappinglist[3])
    assert len(existing_store.load_valid()) == 2
    assert existing_store.load_by_id(new_dictums_6overlappinglist[2].id).data["is"] == "present4"

    existing_store.commit(new_dictums_6overlappinglist[4])
    assert len(existing_store.load_valid()) == 3
    assert existing_store.load_by_id(new_dictums_6overlappinglist[4].id).data["is"] == "present5"

    existing_store.commit(new_dictums_6overlappinglist[5])
    assert len(existing_store.load_valid()) == 4
    assert existing_store.load_by_id(new_dictums_6overlappinglist[5].id).data["is"] == "present6"


def test_sync_updates_kwargs(existing_store, new_dictum):
    """Check sync updates items in kwargs."""

    assert new_dictum.id is None
    existing_store.commit(new_dictum)

    existing_store.sync(new_dictum, valid_from_ts=5.0)
    loaded_dictum = existing_store.load_by_id(new_dictum.id)
    assert loaded_dictum.meta_data["valid_from_ts"] == 5.0

    existing_store.sync(new_dictum, udigest=b"456", valid_from_ts=1.0, valid_to_ts=1000)
    loaded_dictum = existing_store.load_by_id(new_dictum.id)
    assert loaded_dictum.meta_data["valid_from_ts"] == 1.0
    assert loaded_dictum.meta_data["valid_to_ts"] == 1000.0
