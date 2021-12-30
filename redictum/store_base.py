"""
Redictum store base module.

Store adapters should inherit the `StoreBase` class and override the methods.StoreBase()

Store adapter `__init__` implementations should call the super class `__init__` first.
The other methods should not call the super class as an unimplemented error will be raised.

The `dictum_cls_to_code(self, dictum_cls)` and `code_to_dictum_cls(dictum_cls)` methods
are not intended to be overridden, unless this is somehow useful, they may be used by
super classes to translate a `Dictum` derived class into a string, and that string back
into the class, for serialisation and deserialisation purposes. Note that if you change
your dictum class name or module, the previously serialised record will not be restorable
any more, so, you must perform some sort of migration. Various ways of doing this could
be attempted, but it is suggested to move all codebases to retain the old class with a
`restore` method which returns an instantiation of the new class, which will allow the
newly named class to work seemlessly, until migration is complete.
"""


from .dictum import DictumRegister


class StoreBase:
    """
    Store adapter base class.

    Most of the functions will dictum_cls_to_code and code_to_dictum_cls.
    """

    class UnimplementedError(Exception):
        """Raised for calls to methods unimplemented by subclasses."""

        def __init__(self, msg=None):
            super().__init__(msg or "unimplemented")  # pragma: no cover

    def commit(self, dictum):
        """
        Commit the dictum (create or update) to permanent storage, or raise if unsuccessful.

        Subclass must implement.

        The adapter must call the dictums `link_store` method after storage, passing the primary key
        ID and optionally a reference, such as an object useful to the storage adapter.
        """

        raise self.UnimplementedError()  # pragma: no cover

    def delete(self, dictum):
        """
        Delete the dictum from permanent storage, or raise if unsuccessful.

        Subclass must implement.
        """

        raise self.UnimplementedError()  # pragma: no cover

    def sync(self, dictum, **kwargs):
        """
        Synchronise changes to permanent storage. The kwargs must provide a items to sync.

        Valid items to sync are "data", "valid_from_ts" and "valid_to_ts".

        Data should be JSON serialisable and the timestamps should be floats.

        Subclass must implement.
        """

        raise self.UnimplementedError()  # pragma: no cover

    def load_by_id(self, id):
        """
        Access data from permanent storage and return a dictum object. The "id" param is a unique primary key.

        Subclass should implement, though technically it is not absolutely mandatory. Not implementing means
        that the adapter is not compatible for any client which calls "load_by_id" on the repository. It should
        only be unimplemented if it is not possible for the back end storage.
        """

        raise self.UnimplementedError()  # pragma: no cover

    def load_by_udigest(self, udigest):
        """
        Access data from permanent storage and return a dictum object.

        The "udigest" param is a binary value calculated from the parts of the data which make the dictum unique.
        Thus if two dictums have the same digest, then they are essentially the same dictum. Their data may vary of
        course which means they are different versions of that dictum.

        Subclass must implement. The operation MUST be efficient, i.e. subject to an index, or the adapter
        will perform horribly and not scale at all.
        """

        raise self.UnimplementedError()  # pragma: no cover

    def load_valid(self, ts=None):
        """
        Access data from permanent storage and return a "valid" dictum objects iterable.

        "Valid" means the current time, or the provided timestamp (a float) must fall between the "from" and
        "to" (if it has a "to") of the dictum.

        Subclass must implement.

        If implemented the operation should be subject to an index!
        """

        raise self.UnimplementedError()  # pragma: no cover

    def load_expired(self, ts=None):
        """
        Access data from permanent storage and return an "expired" dictum objects iterable.

        "Expired" means the current time, or the provided timestamp (a float) is after the "to" of the dictum.
        If the dictum does not have a "to" (it is allowed to be `None`, then it cannot be expired).

        Subclass should implement, though technically it is not absolutely mandatory. Not implementing means
        that the adapter is not compatible for any client which calls "expired_dictums" on the repository. It
        should only be unimplemented if it is not possible for the back end storage.

        If implemented the operation should be subject to an index, or the adapter documentation must
        provide prominent warnings.
        """

        raise self.UnimplementedError()  # pragma: no cover

    def load_future(self, ts=None):
        """
        Access data from permanent storage and return an "future" dictum objects iterable.

        "Future" means the current time, or the provided timestamp (a float) is before the "from" of the dictum.

        Subclass should implement, though technically it is not absolutely mandatory. Not implementing means
        that the adapter is not compatible for any client which calls "future_dictums" on the repository. It
        should only be unimplemented if it is not possible for the back end storage.

        If implemented the operation should be subject to an index, or the adapter documentation must
        provide prominent warnings.
        """

        raise self.UnimplementedError()  # pragma: no cover

    def load_all(self):
        """
        Access data from permanent storage and return a dictum objects iterable for every single dictum.

        Subclass should implement, though it is not absolutely mandatory. It should be accepted that
        loading all dictums for any deployment of size is potentially impractical and certainly highly
        undesirable. However, it is the decision of the integrator to employ such functionality and
        should only be unimplemented if it is not possible for the back end storage.
        """

        raise self.UnimplementedError()  # pragma: no cover

    def dictum_cls_to_code(self, dictum_cls):
        """
        Return a (string) "code" value for the given dictum class.

        The "code" value may be passed to `code_to_dictum_cls` to get the dictum class back.
        Storage adapters may use these two methods to serialise a class for storage, and get it back again.
        """

        return DictumRegister.dictum_cls_id(dictum_cls)

    def code_to_dictum_cls(self, code):
        """Return the dictum class from a (string) "code" value."""

        return DictumRegister.lookup(code)
