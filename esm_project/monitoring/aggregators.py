from collections import deque
from threading import Lock
from django.conf import Settings

class MovingAverage:
    def __init__(self, n : int):
        self.n = n
        self._window = deque()
        self._total = 0.0
        self._lock = Lock()

    def add(self, value : float) -> float:
        with self._lock:
            self._window.append(value)
            self._total += value
            if len(self._window) > self.n:
                self._total -= self._window.popleft()
            return self._total / len(self._window)  

    def current(self):
        with self._lock:
            return self._total / len(self._window) if self._window else None

    def count(self)->int:
        return len(self._window)

class AggregatorRegistry:
     """One MovingAverage per key (e.g. per API route).""" 
     MAX_KEYS = 500  # guard against unbounded memory 
    
     def __init__(self):
        self._item = {}
        self._lock = Lock()

     def get(self, key : str, n : int) -> MovingAverage: 
         n = n or getattr(Settings, 'MOVING_AVERAGE_WINDOW', 100)  # default window size 
         with self._lock:
            agg = self._item.get(key) 
            if agg is None:
                if len(self._item) >= self.MAX_KEYS:
                    raise RuntimeError(f"Too many keys in AggregatorRegistry (max {self.MAX_KEYS})")
                agg = self._item [key] = MovingAverage(n)
                return agg
     def add(self, key : str, value : float)-> float:
        return self.get(key).add(value)

     def snapshot(self) -> dict:
        """Return a snapshot of the current moving averages for all keys."""
        with self._lock:
            return {k: {"moving_average": a.current(), "samples": a.count(), "window": a.n}
                    for k, a in self._item.items()}

registry = AggregatorRegistry()       