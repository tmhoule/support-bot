# Support Bot

A RAG chatbot that answers tier-1 IT troubleshooting questions from a private GitHub markdown repo of architecture docs.

## Run

1. Copy `.env.example` to `.env` and fill in values. `PORT` must not be `3000`.
2. `docker compose up --build`
3. Open http://localhost:8080

## Test

```
pip install -e ".[dev]"
pytest
```
