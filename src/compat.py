"""Temps monotone compatible CPython et MicroPython."""

import time
import asyncio

try:
    ticks_ms = time.ticks_ms
    ticks_diff = time.ticks_diff
except AttributeError:
    def ticks_ms() -> int:
        """Renvoie le temps monotone en millisecondes."""
        return int(time.monotonic() * 1000)

    def ticks_diff(fin: int, debut: int) -> int:
        """Calcule une durée sur ordinateur."""
        return fin - debut


async def sleep_ms(duree: int) -> None:
    """Attend sans bloquer les autres tâches."""
    await asyncio.sleep(duree / 1000)
