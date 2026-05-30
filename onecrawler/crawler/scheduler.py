import asyncio
from collections import deque
from typing import Optional, Set


class BFScheduler:
    """A scheduler for Breadth-First Search crawling.

    Manages a queue of URLs to visit, a priority queue for immediate visits,
    and a set of already visited URLs to avoid duplicates.

    Attributes:
        queue (deque): The main queue of URLs to visit.
        priority (deque): A high-priority queue for URLs.
        visited (Set[str]): Set of URLs that have already been processed.
        in_queue (Set[str]): Set of URLs currently in one of the queues.
        max_queue_size (int): Maximum allowed size for the queue.
    """

    def __init__(self, base_url: str, max_queue_size: int = 5000):
        self.queue: deque[str] = deque([base_url])
        self.priority: deque[str] = deque()

        self.visited: Set[str] = set()
        self.in_queue: Set[str] = {base_url}

        self.max_queue_size: int = max_queue_size
        self.lock: asyncio.Lock = asyncio.Lock()

    async def has_next(self) -> bool:
        async with self.lock:
            return bool(self.queue or self.priority)

    async def next(self) -> Optional[str]:
        """Retrieves the next URL to visit and atomically marks it as visited.

        Marking visited here — inside the scheduler lock — eliminates the
        TOCTOU window that existed when next() and mark_visited() were
        separate operations. No two workers can ever dequeue the same URL.

        Returns:
            Optional[str]: The next URL, or None if queues are empty.
        """
        async with self.lock:
            if self.priority:
                url = self.priority.popleft()
            elif self.queue:
                url = self.queue.popleft()
            else:
                return None

            self.visited.add(url)
            self.in_queue.discard(url)
            return url

    async def add(self, url: str, priority: bool = False):
        async with self.lock:
            if url in self.visited or url in self.in_queue:
                return

            if len(self.in_queue) >= self.max_queue_size:
                return

            self.in_queue.add(url)

            if priority:
                self.priority.append(url)
            else:
                self.queue.append(url)
