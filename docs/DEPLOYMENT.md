# UC15 — GST Compliance Intelligence & Resolution Agent
## Enterprise Production Operations, Deployment & Troubleshooting Manual (Sprint 19)

---

## 1. System Overview

UC15 is an enterprise-grade GST Compliance Intelligence & Resolution Agent built on PostgreSQL persistence, relational compliance domain models, bounded AI investigation loop, secure RBAC tool execution, structured data quality ingestion, and an AI evaluation framework.

---

## 2. Configuration & Secret Management

Configuration is loaded from environment variables (`.env` or container runtime environment):

| Environment Variable | Default Value | Description |
|----------------------|---------------|-------------|
| `ENVIRONMENT` | `development` | `development`, `test`, or `production` |
| `PERSISTENCE_BACKEND` | `sqlite` | `sqlite`, `memory`, or `postgresql` |
| `DATABASE_URL` | `sqlite:///./app_data.db` | Target database connection URI |
| `DB_POOL_SIZE` | `10` | SQLAlchemy connection pool size |
| `DB_MAX_OVERFLOW` | `20` | Maximum pool overflow connections |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `ALLOWED_CORS_ORIGINS` | `http://localhost:8000` | Allowed origins for CORS policy |

> **IMPORTANT**: In production, secrets (API keys, DB passwords) must be injected via environment variables or secret vaults. Never commit secrets to source control.

---

## 3. Database Setup & Alembic Migrations

To apply database schema migrations:

```bash
# Upgrade database schema to latest head (005_s19_operations_schema)
alembic upgrade head

# Check current migration version
alembic current
```

Migration Chain:
* `001_s14_initial_schema`: Initial relational GST schema
* `002_s15_workflow_schema`: Case lifecycle & decision schema
* `003_s17_data_quality_schema`: Ingestion jobs & data quality schema
* `004_s18_investigation_intelligence`: Investigation steps & evaluation schema
* `005_s19_operations_schema`: Operations alerts & performance benchmark schema

---

## 4. Local Container Deployment (Docker Compose)

To launch the application with PostgreSQL container:

```bash
# Start application & PostgreSQL
docker-compose up -d --build

# View logs
docker-compose logs -f app

# Verify Health & Readiness
curl http://localhost:8000/health
curl http://localhost:8000/ready
```

---

## 5. Operations & Health Monitoring

Endpoints:
* `GET /health` or `/api/health`: Process status
* `GET /ready` or `/api/ready`: Database connectivity & readiness
* `GET /live` or `/api/live`: Liveness check
* `GET /api/operations/dashboard`: Operations Center overview metrics
* `GET /api/operations/alerts`: Operational actionable alerts
* `GET /api/operations/review-queue`: Review queue DTOs pending human review
* `GET /api/operations/readiness-gate`: Formal 17-category readiness gate assessment report

---

## 6. Backup & Disaster Recovery

### Creating a Snapshot Backup
```python
from app.db.backup import BackupManager
backup_info = BackupManager.create_backup()
print("Backup created:", backup_info["snapshot_file"])
```

### Restore Verification
```python
from app.db.backup import BackupManager
success = BackupManager.verify_restore(backup_info, "scratch/test_restore.db")
print("Restore status:", success)
```

---

## 7. Troubleshooting Common Issues

### Issue 1: Database Connection Failure (`503 Not Ready`)
* **Symptom**: `/ready` endpoint returns status 503.
* **Resolution**: Verify `DATABASE_URL` is correct and PostgreSQL service is reachable. Check firewall settings and credentials.

### Issue 2: AI Agent Permission Denied (`403 Forbidden`)
* **Symptom**: AI agent receives 403 when invoking human-only resolution APIs.
* **Resolution**: Expected security boundary behavior. AI Agents are strictly restricted from human-only actions (`case:approve`, `case:reject`, `case:resolve`, `case:close`).

---
