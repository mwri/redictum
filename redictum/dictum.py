"""Redictum dictum module. Provides Dictum class."""


import hashlib
import inspect
from datetime import datetime

import bencodepy


class DictumRegister(type):
    """Dictum metaclass."""

    dictum_types = {}

    def __new__(meta_cls, name, bases, dct):
        cls = super().__new__(meta_cls, name, bases, dct)
        cls_id = meta_cls.dictum_cls_id(cls)
        DictumRegister.dictum_types[cls_id] = cls

        return cls

    @classmethod
    def dictum_cls_id(cls, dictum_cls):
        return f"{dictum_cls.__module__},{dictum_cls.__qualname__}"

    @classmethod
    def lookup(cls, cls_id):
        return DictumRegister.dictum_types[cls_id]


class Dictum(metaclass=DictumRegister):
    """
    Dictums essentially represent lumps of data, optionally with code and a schema
    associated, always with a "valid from" time (before which time the data is not
    considered "valid"), optionally with a TTL which implies a "valid to" time (after
    which time the data is not considered "valid").

    The data is a dictionary and the keys and values may be anything as long as it
    remains JSON serialisable.

    The "valid from" time defaults to the current time, and the "valid to" time
    defaults to None (no expiry, the data is "valid" forever).

    "Valid", as used above, means nothing more than the current time is within
    the "from" to "to" window.

    By default, a dictum's data is what defines it's identity, meaning that two
    dictums with the exact same data, are the same dictum. Of course it is possible
    to construct two dictum objects with the same data and they will be different
    objects, but from a database / storage lookup point of view, they are the same.
    Thus constructing and "applying" (committing to permanent storage) a dictum, and
    then constructing another one, and applying that as well, will not create a
    new dictum (in storage), instead the stored dictum will be updated. Since in this
    example the data is the same only the "valid from" and "valid to" will change.

    What constitues the uniqueness of a dictum can be set to a subset of the
    data. So for example if the data being dictum represents dogs, with five keys
    "owner", "address", "name", "age" and "health", it should be clear that the
    age and health of a dog do not make it a different dog, but, if we assume for
    the sake of this contrived example that no dog owners at the same address
    will have two dogs with the same name, then the owner, address and name
    uniquely identify all dogs! That means you can apply dictum after dictum entirely
    carelessly, and either new dictums (or dogs if you like) will be established in
    storage, or where there is already a dictum with the given owner, address and
    name, that dictum will be updated (the age and health will change, and also the
    "valid from" will be updated, and "valid to" as well if a TTL applies to dog
    dictums).

    Creating the dog dictum exemplified above would look like this:

        from redictum import Dictum

        class DogDictum(Dictum):
            ttl = 3600 * 24 * 365
            unique_by = ("owner", "address", "name")

        d1 = DogDictum({
            "owner": "Fred",
            "address": "The place",
            "name": "Woofie",
            "age": 1, "health": "good",
        })
        # d1 represents a new dog

        d2 = DogDictum({
            "owner": "Fred",
            "address": "The place",
            "name": "Growler",
            "age": 2, "health": "good",
        })
        # d2 represents a new dog (different owner, address, name combination)

        d3 = DogDictum({
            "owner": "Fred",
            "address": "Other place",
            "name": "Woofie",
            "age": 1, "health": "good",
        })
        # d3 represents a new dog (a different Fred at a different address, albeit with a
        # Woofie age 1 in good health)

        d4 = DogDictum({
            "owner": "Fred",
            "address": "The place",
            "name": "Woofie",
            "age": 2,
            "health": "moderate",
        })
        # d4 does not represent a new dog, d1 and d4 are the same data, even if not
        # the same object, so this represents an update to d1

    The TTL here is a year, so that means if there is no update of a given dog
    for a year, that dog's data becomes "invalid". This is only relevant when
    looking up all valid dictums, or dogs, or whatever. When doing such a lookup
    the valid dictums can be sought, rather than all dictums. See the repository
    for details.
    """

    ttl = None
    unique_by = None

    def __init__(self, data, *, ts=None):
        """
        Initialise dictum.

        An optional "ts" kwarg is given to change the valid from time. This should
        be a floating point timestamp value. The default will be the current time.
        """

        self._store = None
        self._id = None
        self._store_ref = None

        self._set_meta_data(None, ts)
        self._set_data(data)

    def _set_meta_data(self, meta_data=None, ts=None):
        if meta_data is None:
            now_ts = ts if ts is not None else datetime.now().timestamp()

            meta_data = {
                "valid_from_ts": now_ts,
                "valid_to_ts": now_ts + type(self).ttl if type(self).ttl else None,
            }

        self._meta_data = meta_data

    def _set_data(self, data=None):
        self._data = data or {}

        if type(self).unique_by is None:
            hash_data = self._data
        else:
            hash_data = {k: v for k, v in self._data.items() if k in type(self).unique_by}

        self._udigest = hashlib.sha256(bencodepy.encode(hash_data)).digest()

    def slide_ts_window(self, offset):
        """Slide the time window of the dictum by the given number of seconds. "From" and "to" are both moved."""

        self._meta_data["valid_from_ts"] += offset

        if self._meta_data["valid_to_ts"] is None:
            if self._store is not None:
                self._store.sync(
                    self,
                    valid_from_ts=self._meta_data["valid_from_ts"],
                )
        else:
            self._meta_data["valid_to_ts"] += offset

            if self._store is not None:
                self._store.sync(
                    self,
                    valid_from_ts=self._meta_data["valid_from_ts"],
                    valid_to_ts=self._meta_data["valid_to_ts"],
                )

        return self

    def extend_ts_window(self, offset):
        """Extend the time window of the dictum by the given number of seconds. "To" is moved."""

        if self._meta_data["valid_to_ts"] is not None:
            self._meta_data["valid_to_ts"] += offset

        if self._store is not None:
            self._store.sync(
                self,
                valid_to_ts=self._meta_data["valid_to_ts"],
            )

        return self

    def delete(self):
        """Delete the dictum."""

        if self._store_ref is not None:
            self._store.delete(self)

        return self

    @property
    def data(self):
        """The dictum's data."""

        return self._data.copy()

    @property
    def meta_data(self):
        """The dictum's meta data, a dictionary with "valid_from_ts" and "valid_to_ts" keys."""

        return self._meta_data.copy()

    @property
    def all_data(self):
        """All the dictum's data, that is the actual user data, and the meta data, merged."""

        return {**self._data, **self._meta_data}

    def added(self):
        """
        Called when the dictum is committed. Intended for subclass use if required.

        Note that this is called once, on one instance of the class, the instance that is added.
        If there are other instances (up to date or not) of the dictum, their "update" callback will
        not be invoked.
        """

    def updated(self, _old_dictum):
        """
        Called when a change to the dictum is committed. Intended for subclass use if required.

        Note that this is called once, on one instance of the class, the instance that is updated.
        If there are other instances (up to date or not) of the dictum, their "update" callback will
        not be invoked.
        """

    def deleted(self):
        """
        Called when the dictum is deleted.

        Note that this is called once, on the instance of the class which `delete` is called on.
        If there are other instances (up to date or not) of the dictum, their "deleted" callback will
        not be invoked.
        """

    def __repr__(self):
        return (
            self.__module__
            + "."
            + self.__class__.__name__
            + "{"
            + ", ".join([f"{repr(k)}: {repr(v)}" for k, v in {**self._meta_data, **self._data}.items()])
            + "}"
        )

    def __str__(self):
        return self.__repr__()

    def __eq__(self, other):
        return (
            type(self) == type(other)
            and self.id == other.id
            and self.meta_data == other.meta_data
            and self.data == other.data
        )

    def __deepcopy__(self, _memo):
        return type(self).restore(self.meta_data, self.data, self.id, self.store, self.store_ref)

    @classmethod
    def restore(cls, meta_data, data, id, store, store_ref=None, *args, **kwargs):
        """Restore dictum, used by store adapters to deserialise a stored record."""

        dictum = cls(None, *args, **kwargs)
        dictum.link_store(id, store, store_ref=store_ref)
        dictum._set_meta_data(meta_data)
        dictum._set_data(data)

        return dictum

    @property
    def id(self):
        """The (unique, primary key) storage ID of the dictum, IF it has been committed."""

        return self._id

    @property
    def udigest(self):
        """A digest of the data which contributes to the uniqueness of the dictum."""

        return self._udigest

    @property
    def store_ref(self):
        """A store reference, should be considered opaque and used only by the store adapter."""

        return self._store_ref

    @property
    def store(self):
        """The store, which should be `None` or an instance of a store class."""

        return self._store

    def link_store(self, id, store, store_ref=None):
        """Link dictum to a back end storage, used by the store adapter when the dictum is committed."""

        self._id = id
        self._store = store
        self._store_ref = store_ref
