Please make your changes directly in /workspace/repo.

Deleting a queue does not get rid of it.

Last Tuesday we retired the legacy-billing queue with `delete(delete_jobs=True)`. It
dropped out of rq info and we moved on. By Thursday it was back. A reminder somebody had
scheduled on it weeks ago came due and the scheduler put it straight back on the queue,
jobs our shared rate limit had been holding back got their turn and landed there as well,
and Priya's exports, on another queue under the same limit, spent the afternoon waiting
for a slot behind jobs of a queue that no longer existed.

Nor did the history go anywhere. We opened a fresh queue under the old name to try the
move and it already had finished, failed and canceled jobs in it, results and all. Over
in invoicing a job that depended on one of the deleted jobs is still waiting on something
that will never run. What happens to jobs like that we leave to you; stuck forever is the
one answer we do not want. Those are only the ones we tripped over.

Deleting a queue with its jobs means all of them, whatever each was doing at the time. One
that is running right then can finish, with the rate limit still counting it until it
does. Asking to keep the jobs keeps them. Nothing that belongs to any other queue changes,
however close its name.

Do not touch the repository's own tests and keep them passing; anything you add belongs
in a file of its own.

Finish with a final response when your changes are ready.
