"""Redictum repo(sitory) module."""


class Repo:
    """
    The repository is essentially an interface between dictums and a permanent
    storage. Creating a repo object requires a storage adapter object to be
    given, and then the resultant object may be used to apply any dictums which
    are instantiated (which will utilise the given storage).

    For example:

        import redictum

        repo = redictum.Repo(
            redictum.store.RdbmsStore("sqlite:///:memory:")
        )

        class DogDictum(redictum.Dictum):
            ttl = 3600 * 24 * 365
            unique_by = ("owner", "address", "name")

        d1 = DogDictum({
            "owner": "Fred",
            "address": "The place",
            "name": "Woofie",
            "age": 1, "health": "good",
        })
        # d1 defined / instantiated, but does not really exist as such

        repo.apply(d1)
        # d1 is committed to permanent storage now

        d2 = DogDictum({
            "owner": "Fred",
            "address": "The place",
            "name": "Woofie",
            "age": 2,
            "health": "moderate",
        })

        repo.apply(d2)
        # this is actuall an update (in perment storage) to the d1 previously committed
    """

    def __init__(self, store):
        """Initialise repository. A store object must be given."""

        self._store = store  # pragma: no cover

    @property
    def store(self):
        """Return the storage adapter."""

        return self._store  # pragma: no cover

    def apply(self, dictum):
        """Apply the dictum (commit it)."""

        return self._store.commit(dictum)  # pragma: no cover

    def load_by_id(self, *args):
        """Return the dictum with the given (DB/storage) ID. None is returned if it does not exist."""

        return self._store.load_by_id(*args)  # pragma: no cover

    def valid_dictums(self, *args):
        """Return dictums which are valid (timestamp falls between the valid from and valid to)."""

        return self._store.load_valid(*args)  # pragma: no cover

    def expired_dictums(self, *args):
        """
        Return dictums which are expired (the valid to is in the past).

        Expired dictums are not purged from storage; expiry is merely a state w.r.t. time.
        There is nothing to stop you from deleting expired dictums in some sort of garbage
        collection cycle if appropriate though.
        """

        return self._store.load_expired(*args)  # pragma: no cover

    def future_dictums(self, *args):
        """Return dictums which are expired (the valid from is in the future)."""

        return self._store.load_future(*args)  # pragma: no cover

    def all_dictums(self, *args):
        """Return all dictums."""

        return self._store.load_all(*args)  # pragma: no cover
