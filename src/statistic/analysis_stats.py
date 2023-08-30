from __future__ import annotations

import ctypes

import numpy as np
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from helperFunctions.types import MpValue, MpArray

    pass

# FIXME Make this configurable (but not per plugin!)
ANALYSIS_STATS_LIMIT = 1000


def get_plugin_stats(stats: MpArray, stats_count: MpValue) -> dict[str, str] | None:
    try:
        count = stats_count.value
        array = np.array(stats.get_obj(), ctypes.c_float)
        if count < ANALYSIS_STATS_LIMIT:
            array = array[:count]
        return {
            'min': _format_float(array.min()),
            'max': _format_float(array.max()),
            'mean': _format_float(array.mean()),
            'median': _format_float(np.median(array)),
            'std_dev': _format_float(array.std()),
            'count': str(count),
        }
    except (ValueError, AssertionError):
        return None


def _format_float(number: float) -> str:
    """format float with 2 decimal places"""
    return f'{number:.2f}'
