from enum import Enum


def get_unique_prefix_match(prefix: str,
                            choices: list[str],
                            case_sensitive: bool = False,
                            category_name: str = "value") -> str:
    '''
    Try to find a single element of ``choices`` for which ``prefix`` is a prefix.

    If more than one element matches, or none do, will raise a ``ValueError``.

    :param prefix: String prefix to match.
    :param choices: Possible strings to match against.
    :param case_sensitive: Whether match should be case-sensitive.
    :param category_name: A human readable name for what a value in ``choices``
                          represents, for error messages: eg. if ``choices`` is the days
                          of the week, ``category_name`` would be ``"weekday"``.
    '''

    if not case_sensitive:
        prefix = prefix.lower()
        choices = [c.lower() for c in choices]

    results = [c for c in choices if c.startswith(prefix)]

    if len(results) == 1:
        return results[0]

    allowed_values = [f"'{c}'" for c in choices]
    allowed_values_str = ", ".join(allowed_values[:-1])
    allowed_values_str += f" and {allowed_values[-1]}"

    raise ValueError(f"Couldn't parse a unique {category_name} from the prefix "
                     f"'{prefix}' (had {len(results)} matches). Allowed values are "
                     f"{allowed_values_str}.")


def get_unique_enum_prefix_match(prefix: str,
                                 enum: Enum,
                                 case_sensitive: bool = False,
                                 value_name: str = "value") -> Enum:
    '''
    Like ``get_unique_prefix_match``, but take the choices from the names of an
    ``Enum``'s values and return the matching instance of the ``Enum`` class.

    :param value_name: A human readable name for what a value from ``enum`` represents,
                       for error messages.
    '''
    res_name: str = get_unique_prefix_match(prefix,
                                            [p.name for p in enum],
                                            case_sensitive=case_sensitive,
                                            category_name=value_name)
    return enum._member_map_[res_name.upper()]
