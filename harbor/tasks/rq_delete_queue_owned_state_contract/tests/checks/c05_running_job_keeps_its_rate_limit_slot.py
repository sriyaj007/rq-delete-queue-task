"""Fence. A rate-limited job that is running when its queue is deleted keeps
its slot until the run ends, so the limit is never exceeded; after that the
next queue's waiting job gets the slot."""

from _harness import check, run_burst


def main(r):
    from rq import Queue, SimpleWorker
    from rq.job import JobStatus
    from rq.rate_limit import RateLimit, RateLimitRegistry
    from rq.registry import StartedJobRegistry
    from rq.utils import now

    q = Queue("render", connection=r)
    encode = Queue("encode", connection=r)
    limit = RateLimit("gpu", 1)
    q.enqueue("builtins.abs", -1, rate_limit=limit)
    # Take the job the way a worker does, and stop just before running it.
    worker = SimpleWorker([q], connection=r)
    running, _ = worker.dequeue_job_and_maintain_ttl(timeout=None)
    execution = worker.prepare_execution(running)
    worker.prepare_job_execution(running)
    waiting = encode.enqueue("builtins.abs", -2, rate_limit=limit)

    q.delete(delete_jobs=True)
    RateLimitRegistry("gpu", connection=r).cleanup()
    run_burst(r, encode)
    status = waiting.get_status()
    assert status == JobStatus.RATE_LIMITED, (
        f"while the deleted queue's job is still running, the other job is {status.value}: the limit of 1 was exceeded"
    )

    running.ended_at = now()
    worker.handle_job_success(running, q, StartedJobRegistry(queue=q), execution)
    run_burst(r, encode)
    status = waiting.get_status()
    assert status == JobStatus.FINISHED, f"after the running job ended, the other job is {status.value}"


check(main)
