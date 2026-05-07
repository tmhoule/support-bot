# Support Bot

RAG chatbot over a private GitHub markdown repo, for tier-1 support technicians.

Answers are grounded in your architecture docs and (optionally) a vetted internet search backend. Conversations are persisted to SQLite for admin review.

## Quick start (dev)

1. Copy `.env.example` to `.env` and fill in values. **`PORT` must not be `3000`.**
2. `docker compose up --build`
3. Visit http://localhost:8080

## Admin

Pages under `/admin/*` require the `X-Admin-Token` header (value from the `ADMIN_TOKEN` env var). NetIQ SAML SSO is planned but not yet implemented.

## Tests

```
pip install -e ".[dev]"
pytest
```

## Reference

Spec: `/Users/todd/docs/superpowers/specs/2026-05-07-support-tech-chatbot-design.md`
Plan: `/Users/todd/docs/superpowers/plans/2026-05-07-support-tech-chatbot.md`
