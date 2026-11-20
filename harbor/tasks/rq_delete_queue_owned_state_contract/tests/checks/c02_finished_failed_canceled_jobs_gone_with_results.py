"""Jobs of the deleted queue that already ran (finished, failed) or were
canceled are gone with their stored results, and a group no longer lists them."""

from _harness import check, exists, run_burst


def main(r):
    from rq import Queue
    from rq.group import Group
    from rq.results import Result

    q = Queue("reports", connection=r)
    archive = Queue("archive", connection=r)
    finished = q.enqueue("builtins.abs", -7)
    failed = q.enqueue("builtins.int", "x")
    canceled = q.enqueue("builtins.abs", -8)
    canceled.cancel()
    group = Group.create(connection=r, name="monthly")
    grouped = group.enqueue_many(q, [Queue.prepare_data("builtins.abs", (-9,))])[0]
    kept = group.enqueue_many(archive, [Queue.prepare_data("builtins.abs", (-10,))])[0]
    run_burst(r, q)
    assert Result.fetch_latest(finished) is not None, "setup: no result stored"

    q.delete(delete_jobs=True)

    still = [name for name, job in
             (("finished", finished), ("failed", failed), ("canceled", canceled), ("grouped", grouped))
             if exists(r, job)]
    assert not still, f"jobs of the deleted queue are still stored: {still}"
    results = [name for name, job in (("finished", finished), ("failed", failed), ("grouped", grouped))
               if Result.fetch_latest(job) is not None]
    assert not results, f"results of deleted jobs are still stored: {results}"
    members = sorted(job.id for job in Group.fetch("monthly", connection=r).get_jobs())
    assert members == [kept.id], f"group lists {members}, expected only the other queue's job {kept.id}"


check(main)
