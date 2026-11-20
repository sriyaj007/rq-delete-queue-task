"""After delete(delete_jobs=True), a new queue with the same name starts with
nothing: no waiting jobs and nothing in any of its job registries."""

from datetime import timedelta

from _harness import check, listed, run_burst


def main(r):
    from rq import Queue

    q = Queue("invoices", connection=r)
    q.enqueue("builtins.abs", -1)
    q.enqueue("builtins.int", "not a number")
    run_burst(r, q)
    q.enqueue_in(timedelta(days=1), "builtins.abs", -2)
    parent = q.enqueue("builtins.abs", -3)
    q.enqueue("builtins.abs", -4, depends_on=parent)
    q.enqueue("builtins.abs", -5).cancel()

    q.delete(delete_jobs=True)

    assert "invoices" not in listed(r), "the deleted queue is still listed"
    fresh = Queue("invoices", connection=r)
    counts = {
        "waiting": fresh.count,
        "finished": len(fresh.finished_job_registry),
        "failed": len(fresh.failed_job_registry),
        "canceled": len(fresh.canceled_job_registry),
        "deferred": len(fresh.deferred_job_registry),
        "scheduled": len(fresh.scheduled_job_registry),
        "started": len(fresh.started_job_registry),
        "ready": len(fresh.ready_job_registry),
    }
    left = {name: count for name, count in counts.items() if count}
    assert not left, f"a new queue with the deleted name starts with {left}"


check(main)
