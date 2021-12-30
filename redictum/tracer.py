"""Redictum tracer module."""


import inspect

from .dictum import Dictum


class Tracer(Dictum):
    """
    The Tracer class is a Dictum subclass or mix in which automatically adds
    "tracer" data.

    To use it, add it to the super class list:

    ```
    class DogDictum(Tracer, Dictum):
        ttl = 3600 * 24 * 365
        unique_by = ("owner", "address", "name")
    ```

    Now data will contain an "inst_at" key, and the value will be a structure
    describing the module and function where the dictum was instantiated.
    """

    def _set_data(self, data, *args, **kwargs):
        if data is not None:
            data.setdefault("inst_at", self._caller_data(stacklevel=2))

        return super()._set_data(data, *args, **kwargs)

    @classmethod
    def _caller_data(cls, stacklevel=1):
        f = inspect.currentframe()

        while stacklevel > -1:
            f = f.f_back
            stacklevel -= 1

        return {
            "mod": f.f_globals["__name__"],
            "fun": f.f_code.co_name,
        }
