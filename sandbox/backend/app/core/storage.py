from typing import Dict, Any
from datetime import datetime
import threading

class MemoryStorage:
    def __init__(self):
        self._storage = {}
        self._lock = threading.Lock()

    def set(self, key: str, value: Any, expire: int = None):
        with self._lock:
            self._storage[key] = {
                'value': value,
                'created_at': datetime.now()
            }

    def get(self, key: str) -> Any:
        with self._lock:
            data = self._storage.get(key)
            return data['value'] if data else None

    def delete(self, key: str):
        with self._lock:
            if key in self._storage:
                del self._storage[key]

storage = MemoryStorage()