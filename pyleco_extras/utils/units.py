# -*- coding: utf-8 -*-
"""
For unitful quantities with pint


https://pint.readthedocs.io/en/stable/index.html


Created on Wed Feb 15 17:51:49 2023 by Benedikt Burger
"""

import pint

ureg = pint.UnitRegistry()


def assume_units(value: pint.Quantity | str, units: pint.Unit | str) -> pint.Quantity:
    """Return a unitful quantity, assuming, if necessary the `units`.

    :param value: A value that may or may not be unitful.
    :param units: Units to be assumed for ``value`` if it does not already
        have units.
    :return: A unitful quantity that has either the units of ``value`` or
        ``units``, depending on if ``value`` is unitful.
    :rtype: `Quantity`
    """
    if isinstance(value, pint.Quantity):
        return value
    elif isinstance(value, str):
        value = ureg.Quantity(value)
        if value.dimensionless:  # type: ignore
            return ureg.Quantity(value.magnitude, units)  # type: ignore
        return value  # type: ignore
    return ureg.Quantity(value, units)
