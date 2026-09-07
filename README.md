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
┌──────────────────────────┐  ┌──────────────────────────┐
│   Kubernetes (Minikube)  │  │  Kubernetes (EKS)        │
│                          │  │  [Phase 6: Future]       │
│ ┌──────────────────────┐ │  │                          │
│ │ Namespace: fitcheck  │ │  │ ┌──────────────────────┐ │
│ │                      │ │  │ │ Managed Node Group   │ │
│ │ ┌────────────────┐   │ │  │ │ (w/ auto-scaling)    │ │
│ │ │ app (FastAPI)  │   │ │  │ │                      │ │
│ │ │ 2 replicas     │   │ │  │ │ ┌────────────────┐   │ │
│ │ │ 8000           │   │ │  │ │ │ app (FastAPI)  │   │ │
│ │ └────┬───────────┘   │ │  │ │ │ 3+ replicas    │   │ │
│ │      │               │ │  │ │ │ HPA triggered  │   │ │
│ │ ┌────▼───────────┐   │ │  │ │ └────────────────┘   │ │
│ │ │ postgres:16    │   │ │  │ │ ┌────────────────┐   │ │
│ │ │ 1 replica      │   │ │  │ │ │ postgres       │   │ │
│ │ │ PVC (1Gi)      │   │ │  │ │ │ RDS (managed)  │   │ │
│ │ └────────────────┘   │ │  │ │ └────────────────┘   │ │
│ │                      │ │  │ │                      │ │
│ │ ┌────────────────┐   │ │  │ │ ┌────────────────┐   │ │
│ │ │ CronJob:       │   │ │  │ │ │ CronJob:       │   │ │
│ │ │ weekly-        │   │ │  │ │ │ daily-         │   │ │
│ │ │ analysis       │   │ │  │ │ │ aggregation    │   │ │
│ │ │ (Sunday 00:00) │   │ │  │ │ │ (22:00 UTC)    │   │ │
│ │ │ curl /weekly   │   │ │  │ │ │ curl /weekly   │   │ │
│ │ └────────────────┘   │ │  │ │ └────────────────┘   │ │
│ │                      │ │  │ │                      │ │
│ │ ┌────────────────┐   │ │  │ │ ┌────────────────┐   │ │
│ │ │Prometheus      │   │ │  │ │ │Prometheus      │   │ │
│ │ │+ Grafana       │   │ │  │ │ │+ Grafana       │   │ │
│ │ └────────────────┘   │ │  │ │ │(+ Alertmanager)│   │ │
│ │                      │ │  │ │ │                     │ │
│ │ Alerts:              │ │  │ │ Alerts:              │ │
│ │ • app_down (30s)     │ │  │ │ • app_down           │ │
│ │ • job_failed (12h)   │ │  │ │ • job_stale (2d)     │ │
│ │                      │ │  │ │ • p95_latency_slo    │ │
│ └──────────────────────┘ │  │ └──────────────────────┘ │
└──────────────────────────┘  └──────────────────────────┘
```

## Build Phases

| Phase | What | Tech | Status |
|-------|------|------|--------|
| **1** | FastAPI app (SQLite) | FastAPI, SQLAlchemy, pytest | ✅ Done |
| **2a** | Containerize | Dockerfile (multi-stage), .dockerignore | ✅ Done |
| **2b** | Local dev env | Docker Compose, Postgres 16 | ✅ Done |
| **3** | CI pipeline | GitHub Actions (test → build → scan → push) | ✅ Done |
| **4** | Kubernetes manifests | `kubectl apply -f k8s/`, Secret mgmt | ✅ Done |
| **5** | Helm templating | Helm chart, CronJob parameterization | ✅ Done |
| **6** | AWS/EKS deploy | Terraform, EC2/EKS, CloudFormation | 🚧 Planned |

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

### 3. **Database Migrations as a Pre-Upgrade Hook** (Future)
*Phase 6 will add this.* For now, we're auto-creating tables on app startup (`Base.metadata.create_all`). That's **fine for a portfolio**, but a real system would have:

```yaml
# Helm hook (not yet implemented, shown for reference)
pre-upgrade:
  - kind: Job
    apiVersion: batch/v1
    metadata:
      annotations:
        helm.sh/hook: pre-upgrade
        helm.sh/hook-weight: "-5"  # run before app
    spec:
      # Run DB migrations
      containers:
        - image: fitcheck:{{ .Chart.AppVersion }}
          command: ["alembic", "upgrade", "head"]
```

This ensures migrations run *before* the new app version starts, preventing version skew.

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

## Monitoring & Observability (Phase 6)

### Prometheus Metrics

The app exports application metrics at `/metrics`:
- `checkins_created_total` (counter)
- `analysis_duration_seconds` (histogram)
- `cronjob_last_success_timestamp` (gauge)

### Grafana Dashboards

*Panels planned:*
- Check-ins created (7-day trend)
- App latency (p50/p95/p99)
- Pod memory/CPU usage
- CronJob success/failure rate

### Alerting Rules

```yaml
# Example (not yet enabled)
- alert: WeeklyAnalysisJobFailed
  expr: increase(fitcheck_cronjob_failures_total[8d]) > 0
  for: 10m
  annotations:
    summary: "Weekly analysis job has not succeeded in 8 days"
    dashboard: "http://grafana/d/fitcheck"
```

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

## Next Steps (Phase 6 & Beyond)

- [ ] Terraform module for EKS cluster + RDS
- [ ] Prometheus operator + custom metrics export from app
- [ ] Grafana dashboards + alerting rules
- [ ] Load testing with k6 to demonstrate HPA
- [ ] Migrate to Alembic for schema versioning
- [ ] Add SBOM (Software Bill of Materials) generation
- [ ] Blue-green deployment strategy in Helm

---

## License

MIT — use freely for learning or portfolio.

---

**Questions?** See the [design document](./DESIGN.md) (TBD) or check the git history: `git log --oneline | head -20`
