import json
import threading
import queue
from typing import Optional, Set, Tuple

_broker_lock = threading.Lock()
_subscribers: Set[Tuple[queue.Queue, Optional[int]]] = set()


def subscribe(user_id: Optional[int] = None):
    q = queue.Queue()
    with _broker_lock:
        _subscribers.add((q, user_id))
    return q


def unsubscribe(q):
    with _broker_lock:
        _subscribers.copy()
        _subscribers_list = list(_subscribers)
        for item in _subscribers_list:
            if item[0] == q:
                _subscribers.discard(item)


def broadcast(event: dict, target_user_id: Optional[int] = None):
    payload = json.dumps(event)
    with _broker_lock:
        targets = list(_subscribers)
    for q, uid in targets:
        if target_user_id is not None and uid != target_user_id:
            continue
        try:
            q.put_nowait(payload)
        except Exception:
            pass
