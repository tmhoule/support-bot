# Support Bot

A tier-2 IT support assistant used by tier-1 technicians. Grounds answers in a private GitHub markdown repo of architecture and configuration docs.

## Run

1. Copy `.env.example` to `.env` and fill in values. `PORT` must not be `3000`.
2. `docker compose up --build`
3. Open http://localhost:8080

## Test

```
pip install -e ".[dev]"
pytest
```
