# UC15 — Production Configuration & Deployment Guide

## Executive Overview

This document defines the strict, fail-closed production configuration contracts for **UC15 GST Compliance Intelligence & Resolution Agent** when operating in `APP_ENV=production`.

---

## 1. Environment Variable Contracts

| Environment Variable | Allowed Values | Default (Dev) | Production Contract | Description |
|---|---|---|---|---|
| `APP_ENV` | `production`, `demo`, `development` | `development` | Mandatory `production` | Primary runtime environment selector. |
| `ENVIRONMENT` | `production`, `demo`, `development` | N/A | Alias for `APP_ENV` | Legacy compatibility alias. |
| `PERSISTENCE_BACKEND` | `postgres`, `sqlalchemy`, `db`, `sqlite`, `memory` | `sqlite` | Mandatory `postgres` | Relational persistence backend engine. |
| `DATABASE_URL` | PostgreSQL URI connection string | `sqlite:///...` | Mandatory Postgres URI | Database connection string. Must start with `postgresql://`. |
| `DEMO_MODE` | `false`, `true` | `false` | Mandatory `false` | Explicit flag isolating demo features. |
| `DATA_MODE` | `production`, `file`, `synthetic` | `file` | Mandatory `production` | Data origin mode. |
| `AI_MODE` | `live`, `fallback`, `mock` | `fallback` | `live` or `fallback` | AI execution mode. `mock` prohibited in production. |
| `LLM_API_KEY` | Secret API Key string | `None` | Mandatory if `AI_MODE=live` | API key for live LLM inference. |
| `ALLOWED_CORS_ORIGINS` | Comma-separated domain URIs | `http://127.0.0.1:8000` | Specific domains | Allowed cross-origin domains. Wildcards prohibited. |
| `SECRET_KEY` | Cryptographic secret string | `None` | Mandatory high-entropy key | Application encryption/signing secret. |

---

## 2. Fail-Closed Production Principles

In `APP_ENV=production`:

1. **No Silent SQLite Fallback:**
   If `PERSISTENCE_BACKEND=postgres` or `sqlalchemy` is specified, but `DATABASE_URL` is missing or points to a SQLite database (`sqlite://`), application startup **FAILS IMMEDIATELY** with a `RuntimeError`.

2. **No Mock AI in Production:**
   If `AI_MODE=mock` is set when `APP_ENV=production`, startup/readiness checks **FAIL IMMEDIATELY**.

3. **No Automatic Sample Case Population:**
   Automatic sample case generation is disabled in production. Investigation cases are created strictly through explicit statutory findings or human triage.

4. **Strict Authentication & Authorization:**
   All 78 business endpoints strictly enforce `AuthenticatedPrincipal` checks via `X-API-Key` or `Authorization: Bearer <token>` headers. Unauthenticated requests receive HTTP 401 Unauthorized.

---

## 3. Production Readiness Check

Run the production readiness validation:

```bash
python -c "from app.infrastructure.health import ApplicationHealthChecker; print(ApplicationHealthChecker.check_readiness())"
```
