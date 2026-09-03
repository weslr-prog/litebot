class IndicatorCache:
    """A simple in-memory cache for storing and retrieving indicator data."""

    def __init__(self):
        self.cache = {}

    def store(self, key, data):
        """Store data in the cache with the given key."""
        self.cache[key] = data

    def retrieve(self, key):
        """Retrieve data from the cache by key. Returns None if the key is not found."""
        return self.cache.get(key)

    def clear(self):
        """Clear all data from the cache."""
        self.cache.clear()

    def retrieve_or_compute(self, key, data, compute_func):
        """Retrieve data from cache or compute it if not found."""
        cached_result = self.retrieve(key)
        if cached_result is not None:
            return cached_result
        
        # Compute the result
        result = compute_func(key, data)
        self.store(key, result)
        return result
