import time
from contextlib import contextmanager
from typing import Generator, Callable

@contextmanager
def measure_time() -> Generator[Callable[[], float], None, None]:
    """Context manager to measure execution time using perf_counter."""
    start_time = time.perf_counter()
    yield lambda: time.perf_counter() - start_time