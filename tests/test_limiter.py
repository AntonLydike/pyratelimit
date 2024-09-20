from concurrent.futures import ThreadPoolExecutor

import pytest

from ratelimit import ContinuousLimiter
import statistics
import time


@pytest.mark.parametrize("interval", (0.01, 0.1, 0.001))
def test_no_less_than_st(interval: float):
    events = []
    limit = ContinuousLimiter(interval)

    def fn():
        with limit.ticket():
            events.append(time.time())

    for _ in range(15):
        fn()

    d_events = diff(events)
    assert min(d_events) > interval
    assert statistics.stdev(d_events) < 0.0001


@pytest.mark.parametrize("interval", (0.01, 0.1, 0.001))
def test_no_less_than_mt(interval: float):
    events = []
    limit = ContinuousLimiter(interval)
    pool = ThreadPoolExecutor()

    def fn():
        with limit.ticket():
            events.append(time.time())

    for _ in range(15):
        pool.submit(fn)

    pool.shutdown()

    d_events = diff(events)
    # assure that events don't have less than interval time between each other
    assert min(d_events) > interval
    # assure that the events are tightly grouped
    assert statistics.stdev(d_events) < 0.0001


def diff(events: list[float]) -> list[float]:
    d_events = []
    for x1, x2 in zip(events, events[1:]):
        d_events.append(x2 - x1)
    return d_events
