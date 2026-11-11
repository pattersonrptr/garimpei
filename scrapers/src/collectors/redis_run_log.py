"""StoreRunLog on Redis, the broker the workers already share. One JSON value
per store, kept with no expiry (a week-long pause must survive restarts)."""

import json
from dataclasses import asdict, fields
from datetime import date

from src.collectors.ports import StoreRunLog, StoreRunState

KEY = "collectors:run_state:{store}"
_DATES = {f.name for f in fields(StoreRunState) if f.name != "failed_attempts"}


class RedisStoreRunLog(StoreRunLog):
    def __init__(self, redis):
        self.redis = redis  # a redis.Redis with decode_responses=True

    def get(self, store_name: str) -> StoreRunState:
        raw = self.redis.get(KEY.format(store=store_name))
        if not raw:
            return StoreRunState()
        return StoreRunState(
            **{
                name: date.fromisoformat(value) if name in _DATES and value else value
                for name, value in json.loads(raw).items()
            }
        )

    def save(self, store_name: str, state: StoreRunState) -> None:
        data = {
            name: value.isoformat() if isinstance(value, date) else value
            for name, value in asdict(state).items()
        }
        self.redis.set(KEY.format(store=store_name), json.dumps(data))
