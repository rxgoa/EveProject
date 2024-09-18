from datetime import datetime
from collections import OrderedDict

#caching
class CustomTTLCache:
    def __init__(self, maxsize=128):
        self.cache = OrderedDict()
        self.maxsize = maxsize
        self.timestamps = {}
        self.ttls = {}
        self.stats = {}

    def set_with_ttl(self, key, value, ttl):
        self.__setitem__(key, value, ttl)

    def __setitem__(self, key, value, ttl):
        if len(self.cache) >= self.maxsize:
            self._popitem()

        current_time = datetime.now()
        self.cache[key] = value
        self.timestamps[key] = current_time
        self.ttls[key] = ttl if ttl is not None else float('inf')
        self.stats[key] = {'hits': 0, 'misses': 0, 'last_access': current_time.strftime("%Y-%m-%dT%H:%M:%S")}

    def __getitem__(self, key):
        try:
            current_time = datetime.now()
            if key not in self.cache or (current_time - self.timestamps[key]).total_seconds() > self.ttls[key]:
                raise KeyError(key)  # Treat as a miss if expired or not found

            # Update stats for hit
            self.stats[key]['hits'] += 1
            self.stats[key]['last_access'] = current_time.strftime("%Y-%m-%dT%H:%M:%S")
            self.cache.move_to_end(key)  # Move to end to mark as recently used
            return self.cache[key]
        except KeyError:
            # Update stats for miss
            if key in self.stats:
                self.stats[key]['misses'] += 1
            else:
                self.stats[key] = {'hits': 0, 'misses': 1, 'last_access': None}
            raise

    def _popitem(self):
        key, _ = self.cache.popitem(last=False)
        del self.timestamps[key]
        del self.ttls[key]
        del self.stats[key]

    def get_stats(self, key):
        return self.stats.get(key, {'hits': 0, 'misses': 0, 'last_access': None})

    def global_stats(self):
        total_hits = sum(stats['hits'] for stats in self.stats.values())
        total_misses = sum(stats['misses'] for stats in self.stats.values())
        return {'total_hits': total_hits, 'total_misses': total_misses}

    def __contains__(self, key):
        try:
            self[key]
            return True
        except KeyError:
            return False

    def __len__(self):
        return len(self.cache)

print(f"\n\n\n\n\n\nCACHEEEEEEEEEEEEE\n\n\n\n")
cache = CustomTTLCache(maxsize=50)