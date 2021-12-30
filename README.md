# Python redictum lib/service (redictum)

[![test](https://github.com/mwri/redictum/actions/workflows/test.yml/badge.svg)](https://github.com/mwri/redictum/actions/workflows/test.yml) [![codecov](https://codecov.io/gh/mwri/redictum/branch/main/graph/badge.svg)](https://codecov.io/gh/mwri/redictum)

## Concept

Imagine some state (a set of key value pairs; a dictionary), the state has a start time and
optionally an end time (like a "valid from" and "valid to" criteria), and some of the state
is just information, and some of it defines the state's uniqueness.

Imagine now that you can just throw state information at the wall, and it sticks, meaning
that the state that is not unique is taken as an update, and the state which is unique, is
new state.

That's what redictum does, as briefly as I can make it!

In case the idea of uniqueness isn't quite clear, imagine a type of state which represents
people, and we are interested in the first name, last name, age and thirst and hunger of
these people.

For example imagine these four bits of state:

```json
{"first_name": "Fred", "last_name": "Flint", "age": 10, "thirst": 2, "hunger": 80}
{"first_name": "Jane", "last_name": "Oster", "age": 20, "thirst": 30, "hunger": 30}
{"first_name": "John", "last_name": "Medium", "age": 40, "thirst": 76, "hunger": 60}
{"first_name": "John", "last_name": "Winter", "age": 30, "thirst": 40, "hunger": 10}
```

Let's say, in our contrived world, that no two people have the same first and last names
and that is the extent of our consideration for identifying the uniqueness of a person.

In that case all four states above are unique, but, if we add this state:

```json
{"first_name": "John", "last_name": "Winter", "age": 31, "thirst": 55, "hunger": 10}
```

...John Winter has become a year older, and a bit more thirsty (that could happen in
a year).

The total state of the system is now:

```json
{"first_name": "Fred", "last_name": "Flint", "age": 10, "thirst": 2, "hunger": 80}
{"first_name": "Jane", "last_name": "Oster", "age": 20, "thirst": 30, "hunger": 30}
{"first_name": "John", "last_name": "Medium", "age": 40, "thirst": 76, "hunger": 60}
{"first_name": "John", "last_name": "Winter", "age": 31, "thirst": 55, "hunger": 10}
```

Had `age` been considered part of what made people unique, then the state would have been
this instead:

```json
{"first_name": "Fred", "last_name": "Flint", "age": 10, "thirst": 2, "hunger": 80}
{"first_name": "Jane", "last_name": "Oster", "age": 20, "thirst": 30, "hunger": 30}
{"first_name": "John", "last_name": "Medium", "age": 40, "thirst": 76, "hunger": 60}
{"first_name": "John", "last_name": "Winter", "age": 30, "thirst": 40, "hunger": 10}
{"first_name": "John", "last_name": "Winter", "age": 31, "thirst": 55, "hunger": 10}
```

You can also set the start (valid from time) and optionally end (valid to time) by way of
a TTL (time to live), and get the "valid" states, or expired or future states.

This simple set of rules means you can throw state at the system that will go away if not
renewed / updated regularly (as govered by the TTL), and you can throw state at the system
which will become "valid" after some time, if it's not cancelled, or otherwise updated.
Being able to get the "valid" states then becomes a powerful tool.

That's more or less the entire concept, it just remains to be said that there are types of
state, with which code can be associated, and the back end storage can be whatever there
is a storage adapter for.

## In code

The above explanation and data is shown here in code now.

First import redictum, create a repository, create a class for people with a (default) time
to live of 200 (seconds), then get the valid dictums, and there will of course be one item:

```python
>>> import redictum
>>> 
>>> people = redictum.Repo(redictum.store.RdbmsStore("sqlite:///:memory:"))
>>> 
>>> class Person(redictum.Dictum):
...     unique_by = ("first_name", "last_name")
...     ttl = 200
... 
>>> people.apply(Person({"first_name": "Fred", "last_name": "Flint", "age": 10, "thirst": 2, "hunger": 80}))
>>> 
>>> people.valid_dictums()
[__main__.Person{'valid_from_ts': 1654451266.453832, 'valid_to_ts': 1654451466.453832, 'first_name': 'Fred', 'last_name': 'Flint', 'age': 10, 'thirst': 2, 'hunger': 80}]
>>> 
```

Now add more people:

```python
>>> people.apply(Person({"first_name": "Jane", "last_name": "Oster", "age": 20, "thirst": 30, "hunger": 30}))
>>> people.apply(Person({"first_name": "John", "last_name": "Medium", "age": 40, "thirst": 76, "hunger": 60}))
>>> people.apply(Person({"first_name": "John", "last_name": "Winter", "age": 30, "thirst": 40, "hunger": 10}))
>>>
```

The display of the dictum objects is a bit inconvenient, so something a little easier on the eye:

```python
>>> for p in [f"{d.data['first_name']} {d.data['last_name']} {d.data['age']} {d.data['thirst']} {d.data['hunger']}" for d in people.valid_dictums()]: print(p)
... 
Fred Flint 10 2 80
Jane Oster 20 30 30
John Medium 40 76 60
John Winter 30 40 10
>>>
```

Now add the new person, which is not a new person, because the first and last names are already in
use (so it updates the existing John Winter record):

```python
>>> people.apply(Person({"first_name": "John", "last_name": "Winter", "age": 31, "thirst": 55, "hunger": 10}))
>>> 
>>> for p in [f"{d.data['first_name']} {d.data['last_name']} {d.data['age']} {d.data['thirst']} {d.data['hunger']}" for d in people.valid_dictums()]: print(p)
... 
Fred Flint 10 2 80
Jane Oster 20 30 30
John Medium 40 76 60
John Winter 31 55 10
>>> 
```

The valid from and valid to timestamps are also available:

```python
>>> for p in [f"{d.data['first_name']} {d.data['last_name']} {d.meta_data['valid_from_ts']} {d.meta_data['valid_to_ts']}" for d in people.valid_dictums()]: print(p)
... 
Fred Flint 1654451266.453832 1654451466.453832
Jane Oster 1654451279.888088 1654451479.888088
John Medium 1654451282.265007 1654451482.265007
John Winter 1654451347.873571 1654451547.873571
>>> 
```

A short while later, the first people "applied" have expired, so `people.valid_dictums()` no
longer returns them, though the later record is still valid:

```python
>>> for p in [f"{d.data['first_name']} {d.data['last_name']} {d.meta_data['valid_from_ts']} {d.meta_data['valid_to_ts']}" for d in people.valid_dictums()]: print(p)
... 
John Winter 1654451347.873571 1654451547.873571
>>> 
```

The expired records can be retrieved:

```python
>>> for p in [f"{d.data['first_name']} {d.data['last_name']} {d.meta_data['valid_from_ts']} {d.meta_data['valid_to_ts']}" for d in people.expired_dictums()]: print(p)
... 
Fred Flint 1654451266.453832 1654451466.453832
Jane Oster 1654451279.888088 1654451479.888088
John Medium 1654451282.265007 1654451482.265007
>>> 
```

If these records are updated, they will disappear from expired and be valid again.

## dictum API

The `Dictum` class API is as follows.

### constructor

There is one required positional parameter, the data. Optionally a `ts` kwarg may be given which
changes the valid from time from now, to whatever you set. A floating point timestamp value should
be given. For example this will create a record which will not appear in the list of valid dictums
until 20 seconds has elapsed:

```python
Dictum({"first_name": "John", "last_name": "Winter"}, ts=datetime.now().timestamp() + 20))
```

The valid to time (if there is a TTL set) will be adjusted as well, so the TTL will remain whatever
it was.

### slide_ts_window

This slides the validity window, forwards or backwards. A single positional parameter specifying
the offset to apply in seconds must be given. The dictum object it self is returned. Thus this:

```python
Dictum({"first_name": "John", "last_name": "Winter"}).slide_ts_window(20)
```

...will be the same as this:

```python
Dictum({"first_name": "John", "last_name": "Winter"}, ts=datetime.now().timestamp() + 20))
```

### extend_ts_window

This is like `slide_ts_window` but only the "to" time is shifted. Though "extend" implies
a positive offset, as with `slide_ts_window` a negative number may be given to shrink the
validity window.

### delete

Delete the dictum.

### data

This *property* returns the dictum's data.

### meta_data

This *property* returns the dictum's meta data (a dictionary with `valid_from_ts`
and `valid_to_ts` keys).

# all_data

This *property* returns data and meta data as one dict.

### id

This *property* returns the store ID which can uniquely identify the dict. It will
be `None` if the dictum is not committed to a store.

## dictum callbacks

The `Dict` class has two callback methods which do nothing by default, but which your `Dict`
subclass may implement. Only the instance being worked on will have it's callback called.

### added

Called when a dictum is added and committed to storage.

### updated

Called when a change to an existing dictum is committed.

### deleted

For completeness of the API, this is called when a dictum is deleted.

### the tracer dictum

The Tracer class is a Dictum subclass or mix in which automatically adds "tracer" data.

To use it, add it to the super classes of your `Dictum` subclass:

```python
class DogDictum(redictum.Tracer, redictum.Dictum):
    ttl = 3600 * 24 * 365
    unique_by = ("owner", "address", "name")
```

Now data will contain an "inst_at" key, and the value will be a structure
describing the module and function where the dictum was instantiated.

It you instantiate another dog, which is the same dog, then the trace data will be updated.

## Notes

You may have as many different types (`Dictum` subclasses) as you like, in the same store
or different ones. If you create two or more `RdbmsStore` objects with the same DSN for this
purpose, it will be the same object, which should be fine. This per DSN singleton behaviour
is specific to the `RdbmsStore` class, other stores behaviour may vary.
