# Agent image: rq at commit 399ad6307febe64b20b818f71743b8337d3a1428, a local
# Redis server and the test dependencies. No grader, no reference solution.
FROM python:3.12-slim@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b

RUN apt-get update \
 && apt-get install -y --no-install-recommends redis-server=5:8.0.2-3+deb13u3 git procps curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.lock /opt/task-tools/requirements.lock
RUN pip install --no-cache-dir -r /opt/task-tools/requirements.lock

# The repository at the pinned commit, as a fresh history of one commit.
COPY rq-src.tar.gz /tmp/rq-src.tar.gz
RUN mkdir -p /workspace \
 && tar -xzf /tmp/rq-src.tar.gz -C /workspace \
 && rm /tmp/rq-src.tar.gz \
 && cd /workspace/repo \
 && git init -q -b main \
 && git add -A \
 && GIT_AUTHOR_DATE=2026-11-20T00:00:00Z GIT_COMMITTER_DATE=2026-11-20T00:00:00Z \
    git -c user.name=baseline -c user.email=baseline@example.invalid commit -q -m "rq 399ad6307feb" \
 && pip install --no-cache-dir --no-deps --no-build-isolation -e /workspace/repo

# A root-owned copy of the baseline history, so that capturing the submission
# ignores whatever the agent does to the checkout's own .git.
COPY capture.py /opt/task-tools/capture.py
RUN cp -a /workspace/repo/.git /opt/task-tools/baseline.git \
 && chown -R root:root /opt/task-tools \
 && chmod -R u=rwX,go=rX /opt/task-tools \
 && ln -s "$(readlink -f /usr/local/bin/python3)" /opt/task-tools/python \
 && groupadd -g 1000 agent && useradd -u 1000 -g 1000 -m -d /home/agent -s /bin/bash agent \
 && chown -R 1000:1000 /workspace/repo \
 && mkdir -p /workspace/submissions && chown 1000:1000 /workspace/submissions

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 LANG=C.UTF-8
WORKDIR /workspace/repo
# Agent harnesses, installed at build time because the container has no
# network while the agent works (Harbor only lets the model API through).
USER 1000:1000
RUN curl -fsSL https://downloads.claude.ai/claude-code-releases/bootstrap.sh | bash -s -- 2.1.325 \
 && "$HOME/.local/bin/claude" --version

# Run with: -a claude-code, or -a mini-swe-agent --ak skip_install=true
RUN python3 -m pip install --user --no-cache-dir uv==0.13.9 \
 && "$HOME/.local/bin/uv" tool install --python 3.12 mini-swe-agent==2.4.6 \
      --with 'litellm[mcp]' --with orjson --with fastapi \
 && "$HOME/.local/bin/mini-swe-agent" --help > /dev/null

# The container's own processes (its idle command, and Redis, started as
# uid 1000) are not the agent's. Harbor runs the agent as uid 1000
# ([agent] user in task.toml), so the capture step can stop every uid 1000
# process without touching the container itself.
USER root
CMD ["sh", "-c", "setpriv --reuid=1000 --regid=1000 --clear-groups redis-server --daemonize yes --save '' --appendonly no --dir /tmp && exec sleep infinity"]
