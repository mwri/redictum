import pytest
from freezegun import freeze_time

from redictum import Dictum, Tracer


def test_instantiation_sets_inst_at_data():
    """Using Tracer adds "inst_at" data with module and function info."""

    class MyDictum(Tracer, Dictum):
        pass

    dictum = MyDictum({"foo": "bar"})

    assert dictum.data["inst_at"] == {
        "fun": "test_instantiation_sets_inst_at_data",
        "mod": "test.redictum.test_tracer",
    }
