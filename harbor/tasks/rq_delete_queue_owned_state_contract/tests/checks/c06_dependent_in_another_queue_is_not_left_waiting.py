"""A job in another queue that was waiting on a job of the deleted queue is not
left waiting forever. Deleting it, canceling it, failing it or letting it run
are all accepted."""

from _harness import check, exists, run_burst


def main(r):
    from rq import Queue
    from rq.job import Job, JobStatus

    q = Queue("ingest", connection=r)
    notify = Queue("notify", connection=r)
    parent = q.enqueue("builtins.abs", -1)
    dependent = notify.enqueue("builtins.abs", -2, depends_on=parent)

    q.delete(delete_jobs=True)
    run_burst(r, notify)

    if not exists(r, dependent):
        return
    status = Job.fetch(dependent.id, connection=r).get_status()
    assert status != JobStatus.DEFERRED, "the dependent job in the other queue is still waiting on a deleted job"
    assert dependent.id not in Queue("notify", connection=r).deferred_job_registry, (
        "the dependent job is still in the other queue's deferred registry"
    )


check(main)
