"""Shared helpers. Each criterion is its own program.

Exit status: 0 the behaviour holds, 1 it does not, 3 the grader could not
judge (for example, no Redis). Code under test that raises, or exits, counts
as the behaviour not holding.
"""

import os
import sys
import traceback


def connect():
    try:
        from redis import Redis

        connection = Redis.from_url(os.environ["REDIS_URL"])
        connection.ping()
        connection.flushall()
    except Exception as error:  # noqa: BLE001
        print("GRADER: cannot reach Redis:", error)
        sys.exit(3)
    return connection


def check(main):
    connection = connect()
    try:
        main(connection)
    except AssertionError as error:
        print("FAIL:", error)
        sys.exit(1)
    except BaseException:  # noqa: BLE001  (includes SystemExit raised by code under test)
        print("FAIL: the code under test raised")
        traceback.print_exc(file=sys.stdout)
        sys.exit(1)
    print("PASS")
    sys.exit(0)


def listed(connection):
    from rq import Queue

    return sorted(queue.name for queue in Queue.all(connection=connection))


def exists(connection, job):
    from rq.exceptions import NoSuchJobError
    from rq.job import Job

    try:
        Job.fetch(job.id, connection=connection)
    except NoSuchJobError:
        return False
    return True


def run_burst(connection, *queues):
    from rq import SimpleWorker

    SimpleWorker(list(queues), connection=connection).work(burst=True)
