import pytest

from ratelimit.continuous import RingBuffer


def test_insertion():
    b = RingBuffer(10, 0)
    assert all(x == 0 for x in b)
    for i in range(100):
        b.append(i)

    assert b.head() == 99

    for exp, act in zip(range(99, 89, -1), b):
        assert exp == act


def test_size():
    for size in (1, 10, 42, 144):
        b = RingBuffer(size, 0)
        assert len(b) == size


def test_getitem():
    b = RingBuffer(10, 0xFF)

    # get items out of range of the buffer
    assert all(b[i] == 0xFF for i in range(-10, 20))

    with pytest.raises(
        ValueError, match="__getitem__ on RingBuffer only supports integers"
    ):
        x = b[1:10]
