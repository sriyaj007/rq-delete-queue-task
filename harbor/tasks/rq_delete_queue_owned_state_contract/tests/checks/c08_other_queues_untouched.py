"""Fence. Deleting a queue changes nothing stored for any other queue,
including queues whose names contain the deleted name: every one of their keys
keeps the same bytes, and the global lists lose only the deleted queue's
entries."""

from datetime import timedelta

from _harness import check, run_burst

DELETED = "mail"
NEIGHBOURS = ["mail2", "eu:mail", "mailing", "mai"]
GLOBAL = {"rq:queues", "rq:groups", "rq:rl-keys", "rq:workers", "rq:clean_groups"}


def populate(r, name, limit_key, group_name):
    from rq import Queue
    from rq.group import Group
    from rq.rate_limit import RateLimit

    q = Queue(name, connection=r)
    limit = RateLimit(limit_key, 1)
    jobs = [q.enqueue("builtins.abs", 1), q.enqueue("builtins.int", "x")]
    jobs += Group.create(connection=r, name=group_name).enqueue_many(q, [Queue.prepare_data("builtins.abs", (2,))])
    run_burst(r, q)
    parent = q.enqueue("builtins.abs", 3)
    jobs += [parent, q.enqueue("builtins.abs", 4, depends_on=parent), q.enqueue_in(timedelta(days=1), "builtins.abs", 5)]
    canceled = q.enqueue("builtins.abs", 6)
    canceled.cancel()
    jobs += [canceled, q.enqueue("builtins.abs", 7, rate_limit=limit), q.enqueue("builtins.abs", 8, rate_limit=limit)]
    return [job.id for job in jobs]


def snapshot(r):
    state = {}
    for key in r.scan_iter("*"):
        name = key.decode()
        if name in GLOBAL or name.startswith(("rq:worker:", "rq:workers:", "rq:clean_registries:", "rq:scheduler")):
            continue
        state[name] = r.dump(key)
    return state


def main(r):
    deleted_ids = populate(r, DELETED, "mail-limit", "mail-batch")
    for name in NEIGHBOURS:
        populate(r, name, f"{name}-limit", f"{name}-batch")

    deleted_keys = [f"rq:{kind}:{DELETED}" for kind in ("wip", "finished", "failed", "deferred", "ready", "scheduled", "canceled")]
    deleted_keys += [f"rq:queue:{DELETED}", f"rq:queue:{DELETED}:intermediate", "rq:group:mail-batch", "rq:rl:mail-limit"]

    def is_deleted_queue_key(name):
        return name in deleted_keys or name.startswith("rq:rl:mail-limit:") or any(i in name for i in deleted_ids)

    before = {k: v for k, v in snapshot(r).items() if not is_deleted_queue_key(k)}
    globals_before = {key: {m.decode() for m in r.smembers(key)} for key in ("rq:queues", "rq:groups", "rq:rl-keys")}

    from rq import Queue

    Queue(DELETED, connection=r).delete(delete_jobs=True)

    after = {k: v for k, v in snapshot(r).items() if not is_deleted_queue_key(k)}
    missing = sorted(set(before) - set(after))
    added = sorted(set(after) - set(before))
    changed = sorted(k for k in set(before) & set(after) if before[k] != after[k])
    assert not (missing or added or changed), f"other queues' keys changed: missing={missing} added={added} changed={changed}"

    queues_after = {m.decode() for m in r.smembers("rq:queues")}
    assert queues_after == globals_before["rq:queues"] - {f"rq:queue:{DELETED}"}, (
        f"the list of queues changed beyond the deleted one: {sorted(globals_before['rq:queues'] ^ queues_after)}"
    )
    for key, own in (("rq:groups", "mail-batch"), ("rq:rl-keys", "mail-limit")):
        after_members = {m.decode() for m in r.smembers(key)}
        assert globals_before[key] - {own} <= after_members <= globals_before[key], (
            f"{key} changed beyond the deleted queue's entry: before={sorted(globals_before[key])} after={sorted(after_members)}"
        )


check(main)
