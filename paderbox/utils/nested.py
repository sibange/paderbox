import copy

import collections
import itertools
from typing import Optional, Any, Union, Sequence, Mapping, Tuple, Callable


def flatten(d, sep: Optional[str] = '.', *, flat_type=dict):
    """
    Flatten a nested `dict` using a specific separator.

    Args:
        sep: When `None`, return `dict` with `tuple` keys (guarantees inversion
                of flatten) else join the keys with sep
        flat_type:  Allow other mappings instead of `flat_type` to be
                flattened, e.g. using an isinstance check.

    import collections
    flat_type=collections.abc.MutableMapping

    >>> d_in = {'a': 1, 'c': {'a': 2, 'b': {'x': 5, 'y' : 10}}, 'd': [1, 2, 3]}
    >>> d = flatten(d_in)
    >>> for k, v in d.items(): print(k, v)
    a 1
    c.a 2
    c.b.x 5
    c.b.y 10
    d [1, 2, 3]
    >>> d = flatten(d_in, sep='_')
    >>> for k, v in d.items(): print(k, v)
    a 1
    c_a 2
    c_b_x 5
    c_b_y 10
    d [1, 2, 3]
    """

    # https://stackoverflow.com/a/6027615/5766934

    # {k: v for k, v in d.items()}

    def inner(d, parent_key):
        items = {}
        for k, v in d.items():
            new_key = parent_key + (k,)
            if isinstance(v, flat_type) and v:
                items.update(inner(v, new_key))
            else:
                items[new_key] = v
        return items

    items = inner(d, ())
    if sep is None:
        return items
    else:
        return {
            sep.join(k): v for k, v in items.items()
        }


def deflatten(d: dict, sep: Optional[str] = '.', maxdepth: int = -1):
    """
    Build a nested `dict` from a flat dict respecting a separator.

    Args:
        d: Flattened `dict` to reconstruct a `nested` dict from
        sep: The separator used in the keys of `d`. If `None`, `d.keys()` should
            only contain `tuple`s.
        maxdepth: Maximum depth until wich nested conversion is performed

    >>> d_in = {'a': 1, 'c': {'a': 2, 'b': {'x': 5, 'y' : 10}}, 'd': [1, 2, 3]}
    >>> d = flatten(d_in)
    >>> for k, v in d.items(): print(k, v)
    a 1
    c.a 2
    c.b.x 5
    c.b.y 10
    d [1, 2, 3]
    >>> deflatten(d)
    {'a': 1, 'c': {'a': 2, 'b': {'x': 5, 'y': 10}}, 'd': [1, 2, 3]}
    >>> deflatten(d, maxdepth=1)
    {'a': 1, 'c': {'a': 2, 'b.x': 5, 'b.y': 10}, 'd': [1, 2, 3]}
    >>> deflatten(d, maxdepth=0)
    {'a': 1, 'c.a': 2, 'c.b.x': 5, 'c.b.y': 10, 'd': [1, 2, 3]}
    >>> d = flatten(d_in, sep='_')
    >>> for k, v in d.items(): print(k, v)
    a 1
    c_a 2
    c_b_x 5
    c_b_y 10
    d [1, 2, 3]
    >>> deflatten(d, sep='_')
    {'a': 1, 'c': {'a': 2, 'b': {'x': 5, 'y': 10}}, 'd': [1, 2, 3]}
    >>> deflatten({('a', 'b'): 'd', ('a', 'c'): 'e'}, sep=None)
    {'a': {'b': 'd', 'c': 'e'}}
    >>> deflatten({'a.b': 1, 'a': 2})
    Traceback (most recent call last):
      ...
    AssertionError: Conflicting keys! ('a',)
    >>> deflatten({'a': 1, 'a.b': 2})
    Traceback (most recent call last):
      ...
    AssertionError: Conflicting keys! ('a', 'b')

    """
    ret = {}
    if sep is not None:
        d = {
            tuple(k.split(sep, maxdepth)): v for k, v in d.items()
        }

    for keys, v in d.items():
        sub_dict = ret
        for sub_key in keys[:-1]:
            if sub_key not in sub_dict:
                sub_dict[sub_key] = {}
            assert isinstance(sub_dict[sub_key], dict), (
                f'Conflicting keys! {keys}'
            )
            sub_dict = sub_dict[sub_key]
        assert keys[-1] not in sub_dict, f'Conflicting keys! {keys}'
        sub_dict[keys[-1]] = v
    return ret


def nested_update(orig, update):
    # Todo:
    assert isinstance(orig, type(update)), (type(orig), type(update))
    if isinstance(orig, list):
        for i, value in enumerate(update):
            if isinstance(value, (dict, list)) \
                    and i < len(orig) and isinstance(orig[i], type(value)):
                nested_update(orig[i], value)
            elif i < len(orig):
                orig[i] = value
            else:
                assert i == len(orig), (i, len(orig))
                orig.append(value)
    elif isinstance(orig, dict):
        for key, value in update.items():
            if isinstance(value, (dict, list)) \
                    and key in orig and isinstance(orig[key], type(value)):
                nested_update(orig[key], value)
            else:
                orig[key] = value


def nested_merge(default_dict, *update_dicts, allow_update=True, inplace=False):
    """
    Nested updates the first dict with all other dicts.

    The last dict has the highest priority when `allow_update` is `True`.
    When `allow_update` is `False`, it is assumed that no values get
    overwritten and an exception is raised when duplicate keys are found.

    When `inplace` is `True`, the `default_dict` is manipulated inplace. This is
    useful for `collections.defaultdict`.

    # Example from: https://stackoverflow.com/q/3232943/5766934
    >>> dictionary = {'level1': {'level2': {'levelA': 0,'levelB': 1}}}
    >>> update = {'level1': {'level2': {'levelB': 10, 'levelC': 2}}}
    >>> new = nested_merge(dictionary, update)
    >>> print(new)
    {'level1': {'level2': {'levelA': 0, 'levelB': 10, 'levelC': 2}}}
    >>> print(dictionary)  # no inplace manipulation
    {'level1': {'level2': {'levelA': 0, 'levelB': 1}}}
    >>> new = nested_merge(dictionary, update, inplace=True)
    >>> print(dictionary)  # with inplace manipulation
    {'level1': {'level2': {'levelA': 0, 'levelB': 10, 'levelC': 2}}}

    >>> nested_merge({'foo': 0}, {'foo': {'bar':1}})
    {'foo': {'bar': 1}}

    >>> nested_merge({'foo': {'bar': 1}}, {'foo': 0})
    {'foo': 0}

    >>> nested_merge({'foo': {'bar': 1}}, {'foo': 0}, allow_update=False)
    Traceback (most recent call last):
    ...
    AssertionError: [{'bar': 1}, 0]
    >>> nested_merge({'foo': {'bar': 1}}, {'blub': 0}, allow_update=False)
    {'foo': {'bar': 1}, 'blub': 0}
    >>> nested_merge({'foo': {'blub': 0}}, {'foo': 1}, {'foo': {'bar': 1}})
    {'foo': {'bar': 1}}
    >>> nested_merge({'foo': 1}, {'foo': {'bar': 1}}, allow_update=False)
    Traceback (most recent call last):
    ...
    AssertionError: [1, {'bar': 1}]
    >>> nested_merge({'foo': {'bar': 1}}, {'foo': {'bar': 1}}, allow_update=False)
    {'foo': {'bar': 1}}
    >>> nested_merge({'foo': {'bar': 1}}, {'foo': {'blub': 1}}, allow_update=False)
    {'foo': {'bar': 1, 'blub': 1}}


    """
    if len(update_dicts) == 0:
        if inplace:
            return default_dict
        else:
            return copy.copy(default_dict)

    dicts = [default_dict, *update_dicts]

    def get_value_for_key(key):
        values = [
            d[key]
            for d in dicts
            if key in d.keys()
        ]
        if isinstance(values[-1], collections.abc.Mapping):
            mapping_values = []
            for value in values[::-1]:
                if isinstance(value, collections.abc.Mapping):
                    mapping_values.insert(0, value)
                else:
                    break
            if not allow_update:
                assert len(mapping_values) == len(values), values
            return nested_merge(
                *mapping_values, allow_update=allow_update, inplace=inplace)
        else:
            if not allow_update:
                try:
                    values = set(values)
                except TypeError:
                    # set requires hashable, force len 1 when not hashable
                    # e.g.: TypeError: unhashable type: 'dict'
                    pass
                assert len(values) == 1, values
                values = list(values)
            return values[-1]

    keys = itertools.chain(*[
        d.keys()
        for d in dicts
    ])

    if not inplace:
        default_dict = copy.copy(default_dict)

    for k in keys:
        default_dict[k] = get_value_for_key(k)

    return default_dict


def nested_op(
        func,
        arg1, *args,
        broadcast=False,
        handle_dataclass=False,
        keep_type=True,
        mapping_type=collections.abc.Mapping,
        sequence_type=(tuple, list),
):
    """
    Applies the function `func` to the leafs of the nested data structures in
    `arg1` and `*args`.
    This is similar to the map function that applies the function the the
    elements of an iterable input (e.g. list).
    This function is `nested_map` with a fancy name.

    CB: Should handle_dataclass be True or False?
        Other suggestions for the name "handle_dataclass"?

    >>> import operator
    >>> nested_op(operator.add, (3, 5), (7, 11))  # like map
    (10, 16)
    >>> nested_op(operator.add, {'a': (3, 5)}, {'a': (7, 11)})  # with nested
    {'a': (10, 16)}

    >>> nested_op(\
    lambda x, y: x + 3*y, dict(a=[1], b=dict(c=4)), dict(a=[0], b=dict(c=1)))
    {'a': [1], 'b': {'c': 7}}
    >>> arg1, arg2 = dict(a=1, b=dict(c=[1,1])), dict(a=0, b=[1,3])
    >>> nested_op(\
    lambda x, y: x + 3*y, arg1, arg2)
    Traceback (most recent call last):
    ...
    AssertionError: ({'c': [1, 1]}, ([1, 3],))

    Note the broadcasting behavior (arg2.b is broadcasted to arg2.b.c)
    >>> nested_op(\
    lambda x, y: x + 3*y, arg1, arg2, broadcast=True)
    {'a': 1, 'b': {'c': [4, 10]}}

    >>> import dataclasses
    >>> @dataclasses.dataclass
    ... class Data:
    ...     a: int
    ...     b: int
    >>> nested_op(operator.add, Data(3, 5), Data(7, 11), handle_dataclass=True)
    Data(a=10, b=16)

    Args:
        func:
        arg1:
        *args:
        broadcast:
        handle_dataclass: Treat dataclasses as "nested" type or not
        keep_type: Keep the types in the nested structure of arg1 for the
            output or use dict and list as types for the output.
        mapping_type: Types that are interpreted as mapping.
        sequence_type: Types that are interpreted as sequence.

    Returns:

    """
    if isinstance(arg1, mapping_type):
        if not broadcast:
            assert all(
                [isinstance(arg, mapping_type) and arg.keys() == arg1.keys()
                 for arg in args]), (arg1, args)
        else:
            assert all(
                [not isinstance(arg, mapping_type) or arg.keys() == arg1.keys()
                 for arg in args]), (arg1, args)
        keys = arg1.keys()
        output = {
            key: nested_op(
                func,
                arg1[key],
                *[arg[key] if isinstance(arg, mapping_type) else arg
                  for arg in args],
                broadcast=broadcast,
                mapping_type=mapping_type,
                sequence_type=sequence_type,
                keep_type=keep_type,
            )
            for key in keys
        }
        if keep_type:
            output = arg1.__class__(output)
        return output
    elif isinstance(arg1, sequence_type):
        if not broadcast:
            assert all([
                isinstance(arg, sequence_type) and len(arg) == len(arg1)
                for arg in args
            ]), (arg1, args)
        else:
            assert all([
                not isinstance(arg, sequence_type) or len(arg) == len(arg1)
                for arg in args
            ]), (arg1, args)
        output = [
            nested_op(
                func,
                arg1[j],
                *[
                    arg[j] if isinstance(arg, sequence_type) else arg
                    for arg in args
                ],
                broadcast=broadcast,
                mapping_type=mapping_type,
                sequence_type=sequence_type,
                keep_type=keep_type,
            )
            for j in range(len(arg1))
        ]
        if keep_type:
            output = arg1.__class__(output)
        return output
    elif handle_dataclass and hasattr(arg1, '__dataclass_fields__'):
        if not broadcast:
            assert all([
                hasattr(arg, '__dataclass_fields__')
                and arg.__dataclass_fields__ == arg1.__dataclass_fields__
                for arg in args
            ]), (arg1, args)
        else:
            assert all([
                not hasattr(arg, '__dataclass_fields__')
                or arg.__dataclass_fields__ == arg1.__dataclass_fields__
                for arg in args
            ]), (arg1, args)
        return arg1.__class__(
            **{
                f_key: nested_op(
                    func,
                    getattr(arg1, f_key),
                    *[getattr(arg, f_key)
                      if hasattr(arg, '__dataclass_fields__')
                      else arg
                      for arg in args
                      ],
                    broadcast=broadcast,
                    mapping_type=mapping_type,
                    sequence_type=sequence_type,
                    keep_type=keep_type,
                )
                for f_key in arg1.__dataclass_fields__
            }
        )

    return func(arg1, *args)


def squeeze_nested(orig):
    """
    recursively flattens hierarchy if all nested elements have the same value

    >>> squeeze_nested({'a': 1, 'b': 1})
    1
    """
    if isinstance(orig, (dict, list)):
        keys = list(orig.keys() if isinstance(orig, dict) else range(len(orig)))
        squeezed = True
        for key in keys:
            orig[key] = squeeze_nested(orig[key])
            if isinstance(orig[key], (list, dict)):
                squeezed = False
        if squeezed and all([orig[key] == orig[keys[0]] for key in keys]):
            return orig[keys[0]]
    return orig


def _get_by_path(
        d: Union[Mapping, Sequence],
        path: Tuple[Any, ...],
        allow_partial_path: bool = False
):
    """ Helper function for `get_by_path` and `set_by_path`. """
    for k in path:
        try:
            d = d[k]
        except Exception:
            # Indexing a custom type can raise any exception, in which case we
            # try to broadcast
            # Not sure if broadcasting makes sense for lists/tuples. It is hard
            # to check for custom sequences because of str, so sequences are
            # broadcasted here
            if allow_partial_path and not isinstance(d, Mapping):
                return d
            raise
    return d


def get_by_path(
        d: Union[Mapping, Sequence],
        path: Union[str, Tuple[Any, ...], None],
        *,
        allow_partial_path: bool = False,
        sep: str = '.',
        default: Any = ...,
) -> Any:
    """
    Gets a value from the nested dictionary `d` by the dotted path `path`.

    Args:
        d: The container to get the value from
        path: Dotted path or tuple of keys to index the nested container with.
            A `tuple` is useful if not all keys are strings. If it is a `str`,
            keys are delimited by `delimiter`
        allow_partial_path: If `True`, broadcast leaves if a sub-path of `path` points to
            a leaf in `d`. Useful for nested structures where the exact
            structure can vary, e.g., in a database the number of samples for
            the "observation" can be located in "num_samples" or
            "num_samples.observation". Use with care!
        sep: The delimiter for keys in path
        default: Default value that is returned when the path is not present in
            the nested container (and cannot be broadcasted if `broadcast=True`)

    Returns:
        Value located at `path` in `d`

    Examples:
        >>> d = {'a': 'b', 'c': {'d': {'e': 'f'}, 'g': [1, [2, 3], 4]}}
        >>> get_by_path(d, 'a')
        'b'
        >>> get_by_path(d, 'c.d.e')
        'f'
        >>> get_by_path(d, ('c', 'g', 1, 0))
        2
        >>> get_by_path(d, 'a.b.c', allow_partial_path=True)
        'b'
        >>> get_by_path(d, 'c.b.c', default=42)
        42
    """
    if path is None:
        return d
    if isinstance(path, str):
        path = path.split(sep)
    try:
        return _get_by_path(d, path, allow_partial_path=allow_partial_path)
    except (KeyError, IndexError):
        if default is not ...:
            return default
        raise


def set_by_path(
        d: Union[Mapping, Sequence],
        path: Union[str, Tuple[Any, ...], None],
        value: Any,
        *,
        sep: str = '.',
) -> None:
    """
    Sets a value in the nested dictionary `d` by the dotted path.

    Modifies `d` inplace.

    Args:
        d: The container to get the value from
        path: Dotted path or tuple of keys to index the nested container with.
            A `tuple` is useful if not all keys are strings. If it is a `str`,
            keys are delimited by `delimiter`
        value: The value to set in `d` for `path`
        sep: The delimiter for keys in path

    Examples:
        >>> d = {}
        >>> set_by_path(d, 'a', {})
        >>> d
        {'a': {}}
        >>> set_by_path(d, 'a.b', {'c': [1, 2, 3], 'd': 'e'})
        >>> d
        {'a': {'b': {'c': [1, 2, 3], 'd': 'e'}}}
        >>> set_by_path(d, ('a', 'b', 'c', 2), 42)
        >>> d
        {'a': {'b': {'c': [1, 2, 42], 'd': 'e'}}}
    """
    if isinstance(path, str):
        path = path.split(sep)
    d = _get_by_path(d, path[:-1])
    d[path[-1]] = value


def nested_any(x, fn: Callable = bool):
    """
    Checks if any value in the nested strucutre `x` evaluates to `True`

    Args:
        x: Nested structure to check
        fn: Function that is applied to every leaf before checking for truth.

    Returns:
        `True` if any leaf value in `x` evaluates to `True`.

    Examples:
        >>> nested_any([False, False, False])
        False
        >>> nested_any([True, False, False])
        True
        >>> nested_any({'a': False})
        False
        >>> nested_any({'a': False, 'b': True})
        True
        >>> nested_any([True, {'a': True, 'b': {'c': True}}, 1, 'true!'])
        True
        >>> nested_any([1, 2, 3, 4], fn=lambda x: x%2)
        True
    """

    class StopException(Exception):
        """Exception raised for early stopping. We have to raise an exception
        that is not used anywhere else to be sure it is not raised by accident.
        """
        pass

    def _local(_x):
        if fn(_x):
            raise StopException()

    try:
        nested_op(_local, x)
    except StopException:
        return True
    return False


def nested_all(x, fn: Callable = bool):
    """
    Checks if all values in the nested strucutre `x` evaluate to `True`

    Args:
        x: Nested structure to check
        fn: Function that is applied to every leaf before checking for truth.

    Returns:
        `True` if all leaf values in `x` evaluate to `True`.

    Examples:
        >>> nested_all([False, False, False])
        False
        >>> nested_all([True, True, True])
        True
        >>> nested_all([True, False, True])
        False
        >>> nested_all({'a': True})
        True
        >>> nested_all({'a': False, 'b': True})
        False
        >>> nested_all([True, {'a': True, 'b': {'c': True}}, 1, ''])
        False
        >>> nested_all([1, 2, 3, 4], fn=lambda x: x%2)
        False
        >>> nested_all([1, 3, 5, 7], fn=lambda x: x%2)
        True
    """
    # `all(x)` is the same as `not any([not x_ for x_ in x])`
    return not nested_any(x, fn=lambda x_: not fn(x_))
