from datetime import date

from src.collectors.ports import StoreRunState
from src.collectors.redis_run_log import RedisStoreRunLog


class DictRedis:
    def __init__(self):
        self.values = {}

    def get(self, key):
        return self.values.get(key)

    def set(self, key, value):
        self.values[key] = value


def test_a_store_that_never_ran_has_a_blank_state():
    assert RedisStoreRunLog(DictRedis()).get("x") == StoreRunState()


def test_a_saved_state_comes_back_the_same():
    state = StoreRunState(
        last_run=date(2026, 11, 10),
        last_blocked=date(2026, 11, 10),
        paused_until=date(2026, 11, 17),
        failed_on=None,
        failed_attempts=2,
    )
    redis = DictRedis()
    RedisStoreRunLog(redis).save("estante_virtual", state)

    assert RedisStoreRunLog(redis).get("estante_virtual") == state
    assert "collectors:run_state:estante_virtual" in redis.values


def test_stores_do_not_share_state():
    log = RedisStoreRunLog(DictRedis())
    log.save("a", StoreRunState(last_run=date(2026, 11, 10)))

    assert log.get("b") == StoreRunState()
