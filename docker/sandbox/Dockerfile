FROM python:3.12-slim

# No network at runtime (--network none), so install everything we need here.
RUN pip install --no-cache-dir pytest==8.3.5

WORKDIR /sandbox

# Entry point: run pytest on whatever files are mounted into /sandbox
CMD ["python", "-m", "pytest", "--tb=short", "-q", "."]
