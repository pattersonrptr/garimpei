from datetime import date

from src.collectors.offers import CollectedOffer
from src.collectors.ports import (
    StoreBlockedError,
    StoreRunState,
    StoreUnavailableError,
)
from src.collectors.use_cases import CollectDaily
from src.tests.collectors.fakes import (
    FixedQueue,
    InMemoryRunLog,
    RecordingSink,
    ScriptedSource,
)

TODAY = date(2026, 11, 10)
YESTERDAY = date(2026, 11, 9)
STORE = "Test Store"


def offer(isbn):
    return CollectedOffer(
        isbn=isbn, url=f"https://store/{isbn}", price=10.0, condition="new"
    )


def run(source, run_log, queue=None, sink=None):
    (outcome,) = CollectDaily(
        [source],
        queue or FixedQueue(["A", "B"]),
        sink or RecordingSink(),
        run_log,
        TODAY,
    ).execute()
    return outcome


def test_collects_the_queue_in_order_and_marks_the_day_done():
    source = ScriptedSource({"A": [offer("A")], "B": [offer("B")]})
    log = InMemoryRunLog()

    outcome = run(source, log, FixedQueue(["B", "A"]))

    assert outcome.status == "collected"
    assert outcome.report.sent == 2
    assert source.asked == ["B", "A"]
    assert log.get(STORE).last_run == TODAY


def test_a_store_already_collected_today_is_not_asked_again():
    source = ScriptedSource({"A": [offer("A")]})
    queue = FixedQueue(["A"])
    log = InMemoryRunLog({STORE: StoreRunState(last_run=TODAY)})

    outcome = run(source, log, queue)

    assert outcome.status == "already_done"
    assert source.asked == [] and queue.asked == []


def test_a_store_collected_yesterday_runs_today():
    source = ScriptedSource({"A": [offer("A")]})
    log = InMemoryRunLog({STORE: StoreRunState(last_run=YESTERDAY)})

    assert run(source, log).status == "collected"
    assert log.get(STORE).last_run == TODAY


def test_a_block_ends_the_store_day_without_pausing_it():
    source = ScriptedSource({"A": StoreBlockedError("HTTP 429")})
    log = InMemoryRunLog()

    outcome = run(source, log)

    assert outcome.status == "blocked"
    assert source.asked == ["A"]  # B is not asked after the block
    state = log.get(STORE)
    assert state.last_run == TODAY  # not tried again today
    assert state.last_blocked == TODAY
    assert state.paused_until is None


def test_a_second_day_blocked_in_a_row_pauses_the_store_for_a_week(caplog):
    source = ScriptedSource({"A": StoreBlockedError("captcha")})
    log = InMemoryRunLog(
        {STORE: StoreRunState(last_run=YESTERDAY, last_blocked=YESTERDAY)}
    )

    run(source, log)

    assert log.get(STORE).paused_until == date(2026, 11, 17)
    assert "paused until 2026-11-17" in caplog.text


def test_blocks_on_days_apart_do_not_pause():
    source = ScriptedSource({"A": StoreBlockedError("captcha")})
    log = InMemoryRunLog({STORE: StoreRunState(last_blocked=date(2026, 11, 8))})

    run(source, log)

    assert log.get(STORE).paused_until is None


def test_a_paused_store_is_skipped_until_the_pause_ends():
    source = ScriptedSource({"A": [offer("A")]})
    log = InMemoryRunLog({STORE: StoreRunState(paused_until=date(2026, 11, 11))})

    outcome = run(source, log)

    assert outcome.status == "paused"
    assert source.asked == []


def test_the_store_runs_again_on_the_day_the_pause_ends():
    source = ScriptedSource({"A": [offer("A")]})
    log = InMemoryRunLog({STORE: StoreRunState(paused_until=TODAY)})

    assert run(source, log).status == "collected"
    assert log.get(STORE).paused_until is None


def test_a_run_that_only_failed_is_tried_again_later_the_same_day():
    source = ScriptedSource({"A": StoreUnavailableError("timeout")})
    log = InMemoryRunLog()

    outcome = run(source, log, FixedQueue(["A"]))

    assert outcome.status == "failed"
    state = log.get(STORE)
    assert state.last_run is None
    assert (state.failed_on, state.failed_attempts) == (TODAY, 1)


def test_the_store_gives_up_for_the_day_after_three_failed_attempts():
    source = ScriptedSource({"A": [offer("A")]})
    log = InMemoryRunLog({STORE: StoreRunState(failed_on=TODAY, failed_attempts=3)})

    outcome = run(source, log)

    assert outcome.status == "skipped"
    assert source.asked == []


def test_failed_attempts_from_another_day_do_not_count():
    source = ScriptedSource({"A": [offer("A")]})
    log = InMemoryRunLog({STORE: StoreRunState(failed_on=YESTERDAY, failed_attempts=3)})

    assert run(source, log).status == "collected"


def test_some_books_not_found_still_counts_as_done():
    source = ScriptedSource({"A": [offer("A")]})  # B: the store does not have it

    log = InMemoryRunLog()

    assert run(source, log).status == "collected"
    assert log.get(STORE).last_run == TODAY


def test_a_queue_the_backend_cannot_give_leaves_the_store_for_next_hour():
    source = ScriptedSource({"A": [offer("A")]})
    log = InMemoryRunLog()

    outcome = run(source, log, FixedQueue(error=ConnectionError("refused")))

    assert outcome.status == "failed"
    assert source.asked == []
    assert log.get(STORE) == StoreRunState()


def test_each_store_has_its_own_state():
    blocked = ScriptedSource({"A": StoreBlockedError("403")})
    blocked.store_name = "blocked"
    fine = ScriptedSource({"A": [offer("A")]})
    fine.store_name = "fine"
    log = InMemoryRunLog()

    outcomes = CollectDaily(
        [blocked, fine], FixedQueue(["A"]), RecordingSink(), log, TODAY
    ).execute()

    assert [o.status for o in outcomes] == ["blocked", "collected"]
    assert log.get("fine").last_blocked is None
