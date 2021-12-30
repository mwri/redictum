import re
from datetime import datetime

import pytest
from freezegun import freeze_time

from redictum import Dictum


def test_constructor_returns_dictum():
    """Check constructor returns a dictum object."""

    assert isinstance(Dictum(None), Dictum)


def test_repr_shows_data():
    """Check repr() shows data."""

    res = repr(Dictum({"foo": "bar"}))

    assert re.compile(r"redictum\.dictum\.Dictum\{(:?'\w+': .+)+\}").match(res)
    assert "'foo': 'bar'" in res


def test_str_shows_data():
    """Check str() shows data."""

    res = str(Dictum({"foo": "bar"}))

    assert re.compile(r"redictum\.dictum\.Dictum\{(:?'\w+': .+)+\}").match(str(res))
    assert "'foo': 'bar'" in res


@freeze_time("2022-05-28")
def test_valid_from_now_by_default():
    """Check default valid from time is now."""

    dictum = Dictum({"foo": "bar"})

    assert dictum.meta_data["valid_from_ts"] == datetime.now().timestamp()


@freeze_time("2022-05-28")
def test_valid_to_none_by_default():
    """Check default valid to time is None."""

    dictum = Dictum({"foo": "bar"})

    assert dictum.meta_data["valid_to_ts"] is None


@freeze_time("2022-05-28")
def test_valid_to_now_plus_ttl_if_ttl():
    """Check valid to time is now plus the TTL, if there is a TTL."""

    class MyDictum(Dictum):
        ttl = 100

    dictum = MyDictum({"foo": "bar"})

    assert dictum.meta_data["valid_from_ts"] == datetime.now().timestamp()
    assert dictum.meta_data["valid_to_ts"] == datetime.now().timestamp() + 100


def test_slide_ts_window_moves_from_to_ts_when_ttl():
    """Check slide_ts_window moves the to time when there is a TTL."""

    class MyDictum(Dictum):
        ttl = 100

    dictum = MyDictum({"foo": "bar"})

    orig_from_ts = dictum.meta_data["valid_from_ts"]
    orig_to_ts = dictum.meta_data["valid_to_ts"]

    offset = 123
    dictum.slide_ts_window(offset)

    assert dictum.meta_data["valid_from_ts"] == orig_from_ts + offset
    assert dictum.meta_data["valid_to_ts"] == orig_to_ts + offset


def test_slide_ts_window_moves_from_ts():
    """Check slide_ts_window moves the from time."""

    dictum = Dictum({"foo": "bar"})

    orig_from_ts = dictum.meta_data["valid_from_ts"]
    orig_to_ts = dictum.meta_data["valid_to_ts"]
    assert orig_to_ts is None

    offset = 123
    dictum.slide_ts_window(offset)

    assert dictum.meta_data["valid_from_ts"] == orig_from_ts + offset
    assert dictum.meta_data["valid_to_ts"] is None


def test_extend_ts_window_moves_to_ts_when_ttl():
    """Check extend_ts_window moves the to time, when there is a TTL."""

    class MyDictum(Dictum):
        ttl = 100

    dictum = MyDictum({"foo": "bar"})

    orig_from_ts = dictum.meta_data["valid_from_ts"]
    orig_to_ts = dictum.meta_data["valid_to_ts"]

    offset = 123
    dictum.extend_ts_window(offset)

    assert dictum.meta_data["valid_from_ts"] == orig_from_ts
    assert dictum.meta_data["valid_to_ts"] == orig_to_ts + offset


def test_extend_ts_window_leaves_to_ts_none():
    """Check extend_ts_window moves the to time None."""

    dictum = Dictum({"foo": "bar"})

    orig_from_ts = dictum.meta_data["valid_from_ts"]
    orig_to_ts = dictum.meta_data["valid_to_ts"]
    assert orig_to_ts is None

    offset = 123
    dictum.extend_ts_window(offset)

    assert dictum.meta_data["valid_from_ts"] == orig_from_ts
    assert dictum.meta_data["valid_to_ts"] is None
