from __future__ import annotations

from math import hypot

from .models import Obstacle


def segment_length_inside_rectangle(
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    rectangle: Obstacle,
) -> float:
    """Return the portion of a 2D line segment inside an axis-aligned rectangle."""

    dx = x1 - x0
    dy = y1 - y0
    t_enter = 0.0
    t_exit = 1.0

    for origin, delta, lower, upper in (
        (x0, dx, rectangle.x_min, rectangle.x_max),
        (y0, dy, rectangle.y_min, rectangle.y_max),
    ):
        if delta == 0.0:
            if origin < lower or origin > upper:
                return 0.0
            continue
        t0 = (lower - origin) / delta
        t1 = (upper - origin) / delta
        if t0 > t1:
            t0, t1 = t1, t0
        t_enter = max(t_enter, t0)
        t_exit = min(t_exit, t1)
        if t_enter >= t_exit:
            return 0.0

    return hypot(dx, dy) * max(0.0, t_exit - t_enter)

