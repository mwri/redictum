"""Redictum RDBMS store adapter module (sqlalchemy store really)."""


import importlib
import json
import os
from copy import deepcopy
from datetime import datetime

import sqlalchemy
from singleton_type import Singleton
from sqlalchemy import BINARY, Column, Float, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from ..store_base import StoreBase


class RdbmsStore(StoreBase, metaclass=Singleton):
    """
    This store adapter uses sqlalchemy to interface redictum to an RDBMS.

    Multiple instantiations of the class with the same connection string will result in the same
    object (i.e. a singleton per connection string).

    The default implementation is thread safe and creates a new session for each operation.
    You can pass the optional kwarg `single_session=True` in which case a single session is
    created and used for all operations. For any other desired behaviour create a subclass
    and override the `_create_session` and `_close_session` methods. It is also possible to
    override the `_create_engine` method to introduce alternative sqlalchemy engine creation
    behaviour, or `_create_session_factory` to return an alternative session maker function.

    The `_create_engine` and `_create_session_factory` methods are passed the dsn and engine
    respectively, and both are passed any extra parameters given to the constructor.
    """

    _dsn_store_cache = {}

    @classmethod
    def singleton_ref(cls, dsn, single_session=False):
        """Singleton metaclass callback."""

        return cls._dsn_store_cache.get(dsn)

    @classmethod
    def singleton_set_ref(cls, obj, dsn, single_session=False):
        """Singleton metaclass callback."""

        cls._dsn_store_cache[dsn] = obj

    def singleton_detach_ref(self):
        """Singleton metaclass callback."""

        del type(self)._dsn_store_cache[self._dsn]

    def __init__(self, dsn, single_session=False, *args, **kwargs):
        """Initialise adapter."""

        super().__init__(*args, **kwargs)

        engine = self._create_engine(dsn, *args, **kwargs)
        session_factory = self._create_session_factory(engine, *args, **kwargs)

        self._dsn = dsn
        self._engine = engine
        self._session_factory = session_factory
        self._single_session = self._session_factory() if single_session else None

        self._setup_tables()

    def _create_engine(self, dsn, *args, **kwargs):
        return create_engine(dsn)

    def _create_session_factory(self, engine, *args, **kwargs):
        return sessionmaker(bind=engine)

    def _create_session(self):
        return self._single_session or self._session_factory()

    def _close_session(self, session):
        if self._single_session is None:
            session.close()

    def commit(self, dictum):
        """Commit new dictum to the store, or update it if it already exists."""

        session = self._create_session()
        same_dictum = self._load_by_udigest(session, dictum.udigest)
        new_dictum = same_dictum is None

        if new_dictum:
            record = self.DictumTable(
                **dictum.meta_data,
                code=self.dictum_cls_to_code(type(dictum)),
                udigest=dictum.udigest,
                data=json.dumps(dictum.data),
            )

            session.add(record)
        else:
            record = same_dictum.store_ref
            session.add(record)

            record.valid_from_ts = dictum.meta_data["valid_from_ts"]
            record.valid_to_ts = dictum.meta_data["valid_to_ts"]
            record.data = json.dumps(dictum.data)

        session.flush()
        session.commit()

        dictum.link_store(record.id, self, record)

        self._close_session(session)

        if new_dictum:
            dictum.added()
        else:
            dictum.updated(same_dictum)

    def delete(self, dictum):
        """Delete dictum from the store."""

        session = self._create_session()
        record = session.query(self.DictumTable).filter(self.DictumTable.id == dictum.id)[0]
        session.add(record)
        session.delete(record)
        session.commit()
        self._close_session(session)

        dictum.deleted()

    def sync(self, dictum, **kwargs):
        """Update given values of the dictum in the store."""

        old_dictum = deepcopy(dictum)

        session = self._create_session()

        record = dictum.store_ref
        session.add(record)
        for k, v in kwargs.items():
            setattr(record, k, v)

        session.flush()
        session.commit()
        self._close_session(session)

        dictum.updated(old_dictum)

    def load_by_id(self, id):
        """Load dictum from the store by primary key ID."""

        session = self._create_session()

        try:
            record = session.query(self.DictumTable).filter(self.DictumTable.id == id)[0]
        except IndexError:
            return None

        self._close_session(session)

        return self._record_to_dictum(record)

    def _load_by_udigest(self, session, udigest):
        """Load dictum by uniqueness digest."""

        try:
            record = session.query(self.DictumTable).filter(self.DictumTable.udigest == udigest)[0]
        except IndexError:
            return None

        return self._record_to_dictum(record)

    def load_by_udigest(self, udigest):
        """Load dictum from the store by it's (binary) digest value."""

        session = self._create_session()

        dictum = self._load_by_udigest(session, udigest)

        self._close_session(session)

        return dictum

    def load_valid(self, ts=None):
        """Load valid dictums from the store."""

        if ts is None:
            ts = datetime.now().timestamp()

        session = self._create_session()

        dictums = [
            self._record_to_dictum(record)
            for record in session.query(self.DictumTable)
            .filter(ts >= self.DictumTable.valid_from_ts)
            .filter(ts < self.DictumTable.valid_to_ts)
            .all()
        ]

        self._close_session(session)

        return dictums

    def load_expired(self, ts=None):
        """Load expired dictums form the store."""

        if ts is None:
            ts = datetime.now().timestamp()

        session = self._create_session()

        dictums = [
            self._record_to_dictum(record)
            for record in session.query(self.DictumTable).filter(ts >= self.DictumTable.valid_to_ts).all()
        ]

        self._close_session(session)

        return dictums

    def load_future(self, ts=None):
        """Load future dictums form the store."""

        if ts is None:
            ts = datetime.now().timestamp()

        session = self._create_session()

        dictums = [
            self._record_to_dictum(record)
            for record in session.query(self.DictumTable).filter(ts < self.DictumTable.valid_from_ts).all()
        ]

        self._close_session(session)

        return dictums

    def load_all(self):
        """Load all dictums form the store."""

        session = self._create_session()

        dictums = [self._record_to_dictum(record) for record in session.query(self.DictumTable).all()]

        self._close_session(session)

        return dictums

    def _record_to_dictum(self, record):
        dictum_cls = self.code_to_dictum_cls(record.code)

        dictum = dictum_cls.restore(
            {"valid_from_ts": record.valid_from_ts, "valid_to_ts": record.valid_to_ts},
            json.loads(record.data),
            record.id,
            self,
            store_ref=record,
        )

        return dictum

    def _setup_tables(self):
        table_base = declarative_base()

        class DictumTable(table_base):
            __tablename__ = "dictums"

            id = Column(Integer, primary_key=True)
            code = Column(String)
            udigest = Column(BINARY)
            valid_from_ts = Column(Float)
            valid_to_ts = Column(Float)
            data = Column(String)

            __table_args__ = (
                sqlalchemy.Index("udigest_index", "udigest"),
                sqlalchemy.Index("validity_index", "valid_from_ts", "valid_to_ts"),
                sqlalchemy.Index("valid_to_ts_index", "valid_to_ts"),
            )

            def __repr__(self):
                return (
                    f"<RdbmsStore.Dictum(id='{self.id}'"
                    f", valid_from_ts='{self.valid_from_ts}'"
                    f", valid_to_ts='{self.valid_to_ts}"
                    f", data='{self.data}'"
                    ")>"
                )

        self.DictumTable = DictumTable

        table_base.metadata.create_all(self._engine)
