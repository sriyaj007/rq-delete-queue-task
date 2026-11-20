"""Fence. delete(delete_jobs=False) removes the queue but every job stays
readable, with its result."""

from datetime import timedelta

from _harness import check, exists, listed, run_burst


def main(r):
    from rq import Queue
    from rq.job import Job
    from rq.results import Result

    q = Queue("audit", connection=r)
    finished = q.enqueue("builtins.abs", -11)
    run_burst(r, q)
    waiting = q.enqueue("builtins.abs", -12)
    scheduled = q.enqueue_in(timedelta(days=1), "builtins.abs", -13)

    q.delete(delete_jobs=False)

    assert "audit" not in listed(r), "the queue is still listed"
    gone = [name for name, job in (("finished", finished), ("waiting", waiting), ("scheduled", scheduled))
            if not exists(r, job)]
    assert not gone, f"delete_jobs=False deleted jobs: {gone}"
    result = Result.fetch_latest(Job.fetch(finished.id, connection=r))
    assert result is not None and result.return_value == 11, "the finished job's result is gone"


check(main)
