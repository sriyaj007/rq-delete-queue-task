FROM python:3.12-slim@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b

RUN apt-get update \
 && apt-get install -y --no-install-recommends redis-server=5:8.0.2-3+deb13u3 redis-tools=5:8.0.2-3+deb13u3 git procps util-linux \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.lock /opt/grader/requirements.lock
RUN pip install --no-cache-dir -r /opt/grader/requirements.lock

COPY rq-src.tar.gz /tmp/rq-src.tar.gz
RUN mkdir -p /workspace \
 && tar -xzf /tmp/rq-src.tar.gz -C /workspace \
 && rm /tmp/rq-src.tar.gz \
 && cd /workspace/repo \
 && git init -q -b main \
 && git add -A \
 && GIT_AUTHOR_DATE=2026-11-20T00:00:00Z GIT_COMMITTER_DATE=2026-11-20T00:00:00Z \
    git -c user.name=baseline -c user.email=baseline@example.invalid commit -q -m "rq 399ad6307feb" \
 && pip install --no-cache-dir --no-deps --no-build-isolation -e /workspace/repo \
 && git config --system --add safe.directory /workspace/repo \
 && groupadd -g 1000 grader && useradd -u 1000 -g 1000 -M -d /tmp/grader-home -s /usr/sbin/nologin grader

COPY verify.py config.json test.sh /tests/
COPY checks/ /tests/checks/
RUN chmod 755 /tests/test.sh && chmod -R a+rX,go-w /tests

WORKDIR /workspace/repo
CMD ["sleep", "infinity"]
