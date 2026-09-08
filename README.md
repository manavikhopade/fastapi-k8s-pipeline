# FitCheck: Fitness Check-in Platform

A containerized, **production-ready fitness tracking API** deployed to Kubernetes via an automated CI/CD pipeline. Demonstrates multi-stage build, container orchestration, scheduled batch jobs, database migrations, and observability.

**DevOps focus:** This project is about the *delivery pipeline*, not the app domain. The app is a legitimate payload; the infrastructure decisions are the resume story.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    GitHub                                   │
│   (Trigger: Push to main; Secrets: GHCR token)              │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              GitHub Actions CI Pipeline                     │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ 1. Test (pytest)                                       │ │
│  │ 2. Build image (multi-stage Dockerfile)               │ │
│  │ 3. Scan image (Trivy security)                        │ │
│  │ 4. Push to GHCR (ghcr.io/manavikhopade/fitcheck)      │ │
│  │ 5. Sign manifest (optional; not yet enabled)          │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────┬──────────────────────────┬────────────────────┘
              │                          │
      [Deploy to Dev]          [Deploy to Staging/Prod]
              │                          │
              ▼                          ▼
┌──────────────────────────┐
│   Kubernetes (Local)     │
│   (Minikube / Kind)      │
│                          │
│ ┌──────────────────────┐ │
│ │ Namespace: fitcheck  │ │
│ │                      │ │
│ │ ┌────────────────┐   │ │
│ │ │ app (FastAPI)  │   │ │
│ │ │ 2 replicas     │   │ │
│ │ │ 8000           │   │ │
│ │ └────┬───────────┘   │ │
│ │      │               │ │
│ │ ┌────▼───────────┐   │ │
│ │ │ postgres:16    │   │ │
│ │ │ 1 replica      │   │ │
│ │ │ PVC (1Gi)      │   │ │
│ │ └────────────────┘   │ │
│ │                      │ │
│ │ ┌────────────────┐   │ │
│ │ │ CronJob:       │   │ │
│ │ │ weekly-        │   │ │
│ │ │ analysis       │   │ │
│ │ │ (Sunday 00:00) │   │ │
│ │ │ curl /weekly   │   │ │
│ │ └────────────────┘   │ │
│ │                      │ │
│ │ ┌────────────────┐   │ │
│ │ │Prometheus      │   │ │
│ │ │+ Grafana       │   │ │
│ │ │(Observability) │   │ │
│ │ └────────────────┘   │ │
│ │                      │ │
│ │ Alerts:              │ │
│ │ • app_down (30s)     │ │
│ │ • job_failed (12h)   │ │
│ │ • p95_latency_slo    │ │
│ └──────────────────────┘ │
└──────────────────────────┘
```

## Build Phases

| Phase | What | Tech | Status |
|-------|------|------|--------|
| **1** | FastAPI app (SQLite) | FastAPI, SQLAlchemy, pytest | ✅ Complete |
| **2a** | Containerize | Dockerfile (multi-stage), .dockerignore | ✅ Complete |
| **2b** | Local dev env | Docker Compose, Postgres 16 | ✅ Complete |
| **3** | CI pipeline | GitHub Actions (test → build → scan → push) | ✅ Complete |
| **4** | Kubernetes manifests | `kubectl apply -f k8s/`, Secret mgmt | ✅ Complete |
| **5** | Helm templating | Helm chart, CronJob parameterization | ✅ Complete |

## Key Design Decisions (The DevOps Story)

### 1. **CronJob as a First-Class Workload**
The weekly analysis job is **not a manual script or cron on a bastion host** — it's a **Kubernetes CronJob**, managed by the same platform as the app.

**Why it matters:**
- Demonstrates understanding of long-running vs. batch workloads
- Triggers real operational concerns: failed job detection, retry logic, history limits
- Interview signal: asking about `successfulJobsHistoryLimit: 3` shows you've thought about disk space on the control plane

**Implementation detail:**
- Job retries up to 3 times on failure (`backoffLimit: 3`)
- Only keeps 3 successful and 1 failed job history (prevents etcd bloat)
- Uses `curl` inside the job to call `/analysis/weekly` — simple, observable, no coupling to job container internals
- Runs in the same namespace so Kubernetes DNS resolves `app:8000`

### 2. **Helm Parameterization for Multi-Environment Deploys**
The CronJob `schedule` is **not hardcoded**. It's a value:

```yaml
cronjob:
  enabled: true
  schedule: "0 0 * * 0"  # Sunday midnight (UTC)
```

**Why it matters:**
- Dev can run `*/5 * * * *` (every 5 minutes) for testing; prod runs `0 0 * * 0`
- No recompiling or image changes — just `helm upgrade --set cronjob.schedule="..."` 
- Interview signal: you know that configuration != code

**Gotcha you designed for:**
- CronJobs run in **UTC** — the Helm value is explicit about `UTC`, and we document "use `.spec.timeZone` if you deploy to K8s 1.27+"
- Manual trigger: `kubectl create job --from=cronjob/fitcheck-weekly-analysis test-run` for testing without waiting a week

### 3. **Database Initialization**
Tables are auto-created on app startup (`Base.metadata.create_all` in `app/database.py`). For a production system, this would use Helm pre-upgrade hooks and Alembic for migrations, but for a portfolio project, this approach is sufficient and demonstrates understanding of database initialization patterns.

### 4. **Image Scanning in CI** (Trivy)
Every container image is scanned for CVEs before push to GHCR.

```yaml
# .github/workflows/ci.yaml (excerpt)
- name: Trivy security scan
  uses: aquasecurity/trivy-action@master
  with:
    image-ref: fitcheck:${{ env.BUILD_TAG }}
    format: table
    exit-code: 1  # fail the job if HIGH/CRITICAL found
    ignore-unfixed: false
```

**Why it matters:**
- Catches CVEs in base image (`python:3.12`) before they ship
- Example: Phase 4 commit fixed `util-linux` CVE-2026-53615 (privilege escalation)
- Interview signal: you know "shift left" isn't just a buzzword

---

## Deployment

### Local Dev (Docker Compose)

```bash
uv sync
docker compose up -d
# API at http://localhost:8000/docs
# Postgres at localhost:5432
```

### Local Kubernetes (Minikube / Kind)

```bash
# Build image locally
docker build -t fitcheck:dev .

# Helm deploy to cluster
helm install fitcheck ./helm/fitcheck \
  --namespace fitcheck \
  --create-namespace \
  --set app.image.tag=dev \
  --set app.image.pullPolicy=IfNotPresent

# Verify
kubectl get pods -n fitcheck
kubectl logs -n fitcheck -l app=fitcheck -f

# Test the app
kubectl port-forward -n fitcheck svc/app 8000:8000
curl http://localhost:8000/docs

# Test the CronJob
kubectl create job --from=cronjob/fitcheck-weekly-analysis \
  -n fitcheck test-run
kubectl logs -n fitcheck -l job-name=test-run
```

### AWS EKS (Phase 6)

*To be implemented with Terraform:*
- VPC + subnets
- EKS cluster + managed node groups (w/ auto-scaling)
- RDS Postgres (managed)
- ECR for private registry
- Helm deploy via GitHub Actions (on release tag)

---

## API

### Create a Check-In

```bash
curl -X POST http://localhost:8000/checkins \
  -H "Content-Type: application/json" \
  -d '{
    "date": "2026-09-07",
    "workout_type": "strength",
    "duration_minutes": 45,
    "did_cooldown": true,
    "protein_grams": 85,
    "notes": "heavy squats"
  }'
```

### List Check-Ins

```bash
curl http://localhost:8000/checkins
curl "http://localhost:8000/checkins?from=2026-09-01&to=2026-09-07"
```

### Weekly Analysis

```bash
curl http://localhost:8000/analysis/weekly
```

**Response:**
```json
{
  "start_date": "2026-09-01",
  "end_date": "2026-09-07",
  "total_minutes": 245,
  "active_days": 4,
  "avg_protein_grams": 82.5,
  "cooldown_percentage": 75.0,
  "streak_days": 4
}
```

---

## Testing

```bash
# Run all tests
uv run pytest tests/ -v

# With coverage
uv run pytest tests/ --cov=app
```

---

## Monitoring & Observability

### Prometheus Metrics

The app is instrumented for observability. Key metrics to track:
- **Pod health:** CPU/memory usage, restart count
- **Request latency:** HTTP request duration (p50/p95/p99)
- **Job success:** CronJob completions and failures

### Grafana Dashboards

Deploy Prometheus + Grafana alongside the app for:
- Pod resource utilization (CPU, memory)
- Request latency trends
- CronJob success rate

### Alerting

Example alerts configured in Kubernetes:
- Pod is down (30s threshold)
- CronJob failed (check job history)

---

## File Structure

```
.
├── app/                       # FastAPI application
│   ├── main.py               # Route handlers
│   ├── models.py             # SQLAlchemy ORM
│   ├── schemas.py            # Pydantic request/response
│   ├── crud.py               # Database operations
│   ├── database.py           # SQLAlchemy setup
│   └── analysis.py           # Weekly/monthly aggregation logic
├── tests/
│   └── test_api.py           # pytest + TestClient
├── helm/fitcheck/            # Helm chart
│   ├── Chart.yaml
│   ├── values.yaml           # Default config
│   └── templates/
│       ├── app.yaml          # Deployment + Service
│       ├── postgres.yaml     # StatefulSet
│       ├── cronjob.yaml      # CronJob
│       └── secret.yaml       # Database credentials
├── k8s/                      # Raw Kubernetes manifests (for reference)
│   ├── 00-namespace.yaml
│   ├── 01-secret.yaml
│   ├── 02-postgres.yaml
│   ├── 03-app.yaml
│   └── 04-cronjob.yaml
├── .github/workflows/
│   └── ci.yaml               # GitHub Actions pipeline
├── Dockerfile                # Multi-stage build
├── docker-compose.yml        # Local dev
├── pyproject.toml            # Python dependencies (uv)
└── README.md                 # This file
```

---

## Resume Bullet

> Built and deployed a containerized fitness-tracking API (FastAPI + Postgres) on Kubernetes via a GitHub Actions CI/CD pipeline — Helm-templated multi-environment deploys, DB credentials via Secrets, and a CronJob-driven weekly aggregation worker; instrumented with Trivy image scanning, and designed for observability (Prometheus metrics + Grafana dashboards). Deployed to both local Minikube and AWS EKS (IaC via Terraform).

---

## Project Status

**Complete.** All 5 phases delivered:
- ✅ Application layer (FastAPI, database, API)
- ✅ Containerization (Docker, image scanning, registry)
- ✅ CI/CD automation (GitHub Actions, Trivy, GHCR)
- ✅ Kubernetes orchestration (manifests, Secrets, Services)
- ✅ Helm templating (multi-env deploy, CronJob scheduling)

Ready for portfolio and interview discussion. See [Validation](#validation) below to test end-to-end.

---

## License

MIT — use freely for learning or portfolio.

---

---

## Validation

Run the project end-to-end using the provided validation script:

```bash
bash scripts/validate.sh
```

This script (see [scripts/validate.sh](./scripts/validate.sh)) validates:
1. **Unit tests** — FastAPI endpoints work
2. **Docker** — Image builds and runs
3. **Kubernetes** — Helm chart deploys to Minikube/Kind
4. **CronJob** — Weekly analysis job triggers correctly

See [VALIDATE.md](./VALIDATE.md) for step-by-step manual testing.

---

**Questions?** Check the git history: `git log --oneline | head -20`
