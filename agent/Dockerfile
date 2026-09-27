# Used only by the "staging" Compose profile, which runs all six agents on the master's
# computer until each member's own computer is connected. Members run the agent with Python
# directly (see agent-node/README.md), so Docker is not required on their machines.
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY *.py ./

CMD ["python", "agent.py"]
