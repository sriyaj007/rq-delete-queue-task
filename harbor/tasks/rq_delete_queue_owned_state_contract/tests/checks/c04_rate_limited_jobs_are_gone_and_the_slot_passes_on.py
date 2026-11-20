"""Jobs of the deleted queue that were waiting for a rate-limit slot are
gone. They do not put the queue back when a slot frees up, and a slot the
deleted queue held passes to the next queue's waiting job, which runs."""

from _harness import check, exists, listed, run_burst


def main(r):
    from rq import Queue
    from rq.job import JobStatus
    from rq.rate_limit import RateLimit

    q = Queue("crawl", connection=r)
    imports = Queue("imports", connection=r)
    index = Queue("index", connection=r)
    warehouse, proxy = RateLimit("warehouse", 1), RateLimit("proxy", 1)

    # Another queue holds the warehouse slot; the deleted queue waits for it.
    holder = imports.enqueue("builtins.abs", -1, rate_limit=warehouse)
    behind_other = q.enqueue("builtins.abs", -2, rate_limit=warehouse)
    # The deleted queue holds the proxy slot and also waits for more. Waiting
    # jobs are ordered by the second they arrived, then by id; the ids put
    # the deleted queue's job first in line even within the same second.
    q.enqueue("builtins.abs", -3, rate_limit=proxy)
    behind_own = q.enqueue("builtins.abs", -4, rate_limit=proxy, job_id="crawl-waiting")
    next_in_line = index.enqueue("builtins.abs", -5, rate_limit=proxy, job_id="index-waiting")

    q.delete(delete_jobs=True)
    run_burst(r, imports, index)

    assert holder.get_status() == JobStatus.FINISHED, "setup: the other queue's slot holder did not run"
    still = [name for name, job in (("behind another queue", behind_other), ("behind its own", behind_own)) if exists(r, job)]
    assert not still, f"rate-limited jobs of the deleted queue are still stored: {still}"
    assert Queue("crawl", connection=r).job_ids == [], "a waiting job was put back on the deleted queue"
    assert "crawl" not in listed(r), "the deleted queue is listed again"
    status = next_in_line.get_status()
    assert status == JobStatus.FINISHED, f"the next queue's waiting job is {status.value}, expected the freed slot to let it run"


check(main)
