FROM python:3.12-slim

# SEC-13: Hardened non-root, offline execution sandbox image
RUN pip install --no-cache-dir pytest==8.3.5 \
    && groupadd --gid 10001 sandbox \
    && useradd --uid 10001 --gid 10001 --create-home --shell /usr/sbin/nologin sandbox \
    && mkdir -p /sandbox /tmp \
    && chown sandbox:sandbox /sandbox

WORKDIR /sandbox
USER 10001:10001

CMD ["python", "-m", "pytest", "--tb=short", "-q", "."]
