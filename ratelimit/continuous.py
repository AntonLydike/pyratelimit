import contextlib
import threading
import time
from collections.abc import Generator
from typing import List, TypeVar, Generic, Any

T = TypeVar("T")


class RingBuffer(Generic[T]):
    buff: List[T]
    i: int
    size: int

    def __init__(self, size: int, default_val: T):
        self.buff = [default_val for _ in range(size)]
        self.i = 0
        self.size = size

    def append(self, val: T):
        self.i = (self.i + 1) % self.size
        self.buff[self.i] = val

    def __getitem__(self, item: Any) -> T:
        """
        Access the last n elements in the buffer.

        Negative accesses instead return from the back of the buffer
        """
        if not isinstance(item, int):
            raise ValueError("__getitem__ on RingBuffer only supports integers")
        if item < 0:
            item = self.size + item
        id = (self.i - item) % self.size
        return self.buff[id]

    def __len__(self) -> int:
        return self.size

    def __iter__(self):
        return iter((self[i] for i in range(self.size)))

    def head(self) -> T:
        return self.buff[self.i]


class ContinuousLimiter:
    last_requests: RingBuffer[float]
    """
    Record the last $saved_tickets requests so we can always know how many tickets are available
    """
    production_interval: float
    """
    Seconds between ticket production
    """

    saved_tickets: int
    """
    Number of tickets that can be acrued if no tickets are used
    """

    queue: int
    """
    The number of the next person to enter the queue
    """
    queue_index: int
    """
    The next queue number to get a ticket minted
    """

    lock: threading.Lock

    def __init__(self, interval: float, saved_tickets: int = 1):
        self.last_requests = RingBuffer(saved_tickets, 0.0)
        self.production_interval = interval
        self.saved_tickets = saved_tickets
        self.queue = 0
        self.queue_index = 0
        self.lock = threading.Lock()

    @contextlib.contextmanager
    def ticket(self) -> Generator[None, None, None]:
        self.lock.acquire()
        # if threads are waiting, we must enqueue ourselves at the back
        if self.queue != self.queue_index:
            self.lock.release()
            yield self._enqueue_self()
            return

        # otherwise, if we can get a trivial ticket, we can just return that
        if self._get_trivial_ticket_must_be_locked():
            self.lock.release()
            yield
            return

        # if we allow the saving up of tickets, check that part
        if self.saved_tickets > 1:
            now = time.time()
            # check if we have accrued tickets:
            tickets_generated_since_interval_start = (
                now - self.last_requests[-1]
            ) // self.production_interval
            # if the number of tickets generated in the remembered interval does not exceed the maximum number
            # of saved tickets:
            if tickets_generated_since_interval_start > self.saved_tickets:
                # mint a ticket, and return
                self.last_requests.append(now)
                self.lock.release()
                yield
                return

        # otherwise we have to enqueue
        self.lock.release()
        yield self._enqueue_self()

    def _enqueue_self(self) -> None:
        with self.lock:
            my_idx = self.queue
            self.queue += 1
        return self._wait_with_ticket(my_idx)

    def _wait_with_ticket(self, ticket: int) -> None:
        with self.lock:
            # time until the next ticket is minted
            time_til_next_ticket = self.production_interval - (
                time.time() - self.last_requests.head()
            )
            # number of threads in the queue before us:
            position_in_queue = ticket - self.queue_index

        # wait for almost the entire needed time.
        # take 5% off of the time to wait until our ticket is minted
        # then we can re-adjust and wait precisely for our ticket to be ready
        if not (time_til_next_ticket < 0 and position_in_queue == 0):
            # assert for sanity, check that we haven't been skipped in the queue
            assert position_in_queue >= 0
            # sleep until our time in the queue is up
            time.sleep(
                max(time_til_next_ticket, 0)
                + position_in_queue * self.production_interval * 0.95
            )

        with self.lock:
            # check that it's our turn, and that we have waited long enough to mint a new trivial ticket
            if ticket == self.queue_index and self._get_trivial_ticket_must_be_locked():
                # dequeue ourselves
                self.queue_index += 1
                return

        return self._wait_with_ticket(ticket)

    def _get_trivial_ticket_must_be_locked(self) -> bool:
        """
        Try to get a "trivial" ticket, i.e. time elapsed since last minting is more than the production interval

        Must be called while the limiter is locked!
        """
        now = time.time()
        # if trivial amount of time passed (more than needed to generate a ticket)
        if now > self.last_requests.head() + self.production_interval:
            # not down that we minted a ticket
            self.last_requests.append(now)
            return True
        return False
