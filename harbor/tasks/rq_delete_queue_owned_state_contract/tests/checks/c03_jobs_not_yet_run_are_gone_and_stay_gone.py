"""Jobs of the deleted queue that had not run yet are gone: waiting,
scheduled for later or already due, and waiting on another job in this queue
or another one. None of them puts the queue back when the scheduler runs or
when the job they waited on finishes."""

from datetime import datetime, timedelta, timezone

from _harness import check, exists, listed, run_burst


def main(r):
    from rq import Queue
    from rq.job import JobStatus
    from rq.scheduler import RQScheduler

    q = Queue("emails", connection=r)
    sms = Queue("sms", connection=r)
    previews = Queue("previews", connection=r)
    past = datetime.now(timezone.utc) - timedelta(minutes=5)
    sms_parent = sms.enqueue("builtins.abs", -1)
    other_due = previews.enqueue_at(past, "builtins.abs", -2)
    local_parent = q.enqueue("builtins.abs", 1)
    jobs = {
        "waiting": local_parent,
        "scheduled for later": q.enqueue_in(timedelta(days=1), "builtins.abs", 2),
        "scheduled and due": q.enqueue_at(past, "builtins.abs", 3),
        "waiting on a job in this queue": q.enqueue("builtins.abs", 4, depends_on=local_parent),
        "waiting on another queue's job": q.enqueue("builtins.abs", 5, depends_on=sms_parent),
    }

    q.delete(delete_jobs=True)

    scheduler = RQScheduler([Queue("emails", connection=r), Queue("previews", connection=r)], connection=r)
    scheduler.acquire_locks()
    scheduler.enqueue_scheduled_jobs()
    run_burst(r, sms)

    assert other_due.id in Queue("previews", connection=r).job_ids, "setup: the scheduler did not run"
    assert sms_parent.get_status() == JobStatus.FINISHED, "setup: the other queue's job did not run"
    still = [name for name, job in jobs.items() if exists(r, job)]
    assert not still, f"jobs of the deleted queue are still stored: {still}"
    assert Queue("emails", connection=r).job_ids == [], "a job was put back on the deleted queue"
    assert "emails" not in listed(r), "the deleted queue is listed again"


check(main)
