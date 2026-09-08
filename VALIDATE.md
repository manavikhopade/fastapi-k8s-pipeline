# FitCheck End-to-End Validation

Complete end-to-end test of all 5 phases. Designed for GitHub Codespaces (or local dev environment).

**Total time:** ~15 minutes

---

## Phase 1-2: Application + Containers

### Step 1: Install dependencies

```bash
uv sync
```

**Expected:** No errors. `.venv` folder created with all dependencies.

---

### Step 2: Run unit tests

```bash
uv run pytest tests/ -v
```

**Expected output:**
```
tests/test_api.py::test_create_checkin PASSED
tests/test_api.py::test_list_checkins PASSED
tests/test_api.py::test_analysis_weekly PASSED
...
====== 5 passed in 0.45s ======
```

**Validates:** Phase 1 — application endpoints work

---

### Step 3: Run app locally (no Docker)

```bash
uv run uvicorn app.main:app --reload &
```

Then test:

```bash
# Wait 2 seconds for app to start
sleep 2

# Health check
curl http://localhost:8000/health
```

**Expected:**
```json
{"status": "ok"}
```

Stop the background app:

```bash
pkill -f uvicorn
```

**Validates:** Phase 1 — app runs; Phase 2a — import path setup correct

---

### Step 4: Build Docker image

```bash
docker build -t fitcheck:dev .
```

**Expected:** Build completes, no errors. Final line: `Successfully tagged fitcheck:dev`

**Validates:** Phase 2a — Dockerfile is correct

---

### Step 5: Run app in Docker (with SQLite)

```bash
docker run --rm -p 8000:8000 fitcheck:dev &
sleep 2

# Test health
curl http://localhost:8000/health
```

**Expected:**
```json
{"status": "ok"}
```

Stop container:

```bash
docker stop $(docker ps -q --filter ancestor=fitcheck:dev)
```

**Validates:** Phase 2a — container runs

---

### Step 6: Docker Compose (app + PostgreSQL)

```bash
docker compose up --build -d
sleep 5  # wait for postgres to be ready

# Check both containers are running
docker compose ps
```

**Expected:**
```
NAME                  IMAGE              STATUS
fitcheck-app-1        fitcheck:dev       Up
fitcheck-postgres-1   postgres:16        Up
```

---

### Step 7: Test API with Postgres backend

**Create a check-in:**

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

**Expected:** Status 201, returns JSON with `"id": 1`

**Verify data persisted:**

```bash
curl http://localhost:8000/checkins
```

**Expected:** Returns list with one check-in (the one you just created)

**Get weekly analysis:**

```bash
curl http://localhost:8000/analysis/weekly
```

**Expected:** Returns summary:
```json
{
  "start_date": "2026-09-01",
  "end_date": "2026-09-07",
  "total_minutes": 45,
  "active_days": 1,
  "avg_protein_grams": 85.0,
  "cooldown_percentage": 100.0,
  "streak_days": 1
}
```

**Validates:** Phase 2b — Docker Compose networking, PostgreSQL driver, data persistence

---

### Step 8: Test data persistence across container restart

```bash
# Stop containers (keep volumes)
docker compose down

# Restart
docker compose up -d
sleep 5

# Query data (should still be there)
curl http://localhost:8000/checkins
```

**Expected:** The check-in you created earlier is still there.

**Validates:** Phase 2b — PVC volumes persist data

---

### Step 9: Clean up Docker Compose

```bash
docker compose down -v
```

**Expected:** All containers and volumes removed

---

## Phase 3: CI/CD Pipeline (GitHub Actions)

*This phase already validated on GitHub.* Check:

```bash
git log --all --grep="Phase 3" --oneline
```

**Expected:** Shows commit `09d3788 Phase 3: GitHub Actions CI ...`

**Proof it worked:**

- Image built and pushed to ghcr.io (`git show 09d3788` shows `docker push`)
- Tests ran before build (`exit-code: 1` in Trivy means security gate blocked bad images)
- Check [GitHub Actions tab](https://github.com/manavikhopade/fastapi-k8s-pipeline/actions) to see all runs

**Validates:** Phase 3 — CI pipeline ran on every commit

---

## Phase 4-5: Kubernetes + Helm

### Step 10: Start Kubernetes

**Option A: Minikube**

```bash
minikube start
```

**Option B: Kind**

```bash
kind create cluster --name fitcheck
kubectl cluster-info
```

**Expected:** Cluster is reachable

---

### Step 11: Load image into cluster

```bash
docker build -t fitcheck:dev .

# For Minikube:
minikube image load fitcheck:dev

# For Kind:
kind load docker-image fitcheck:dev --name fitcheck
```

**Verify:**

```bash
kubectl run test-image --image=fitcheck:dev --restart=Never --rm -it -- sh -c "echo 'OK'" && sleep 1
```

**Expected:** Pod runs and exits cleanly

---

### Step 12: Deploy with Helm

```bash
# Create namespace
kubectl create namespace fitcheck

# Deploy
helm install fitcheck ./helm/fitcheck \
  --namespace fitcheck \
  --set app.image.tag=dev \
  --set app.image.pullPolicy=IfNotPresent \
  --set cronjob.schedule="*/5 * * * *"  # Run every 5 min for testing

# Wait for pods
kubectl get pods -n fitcheck -w
```

**Expected:** After ~30 seconds:
```
NAME                   READY   STATUS    RESTARTS   AGE
fitcheck-app-5d4f...   1/1     Running   0          10s
fitcheck-app-7b2k...   1/1     Running   0          10s
fitcheck-postgres-0    1/1     Running   0          15s
```

Press `Ctrl+C` to stop watching.

**Validates:** Phase 4 & 5 — Kubernetes resources deployed

---

### Step 13: Test app on Kubernetes

```bash
# Port-forward to the service
kubectl port-forward -n fitcheck svc/app 8000:8000 &
sleep 2

# Health check
curl http://localhost:8000/health
```

**Expected:**
```json
{"status": "ok"}
```

**Create a check-in:**

```bash
curl -X POST http://localhost:8000/checkins \
  -H "Content-Type: application/json" \
  -d '{
    "date": "2026-09-08",
    "workout_type": "cycling",
    "duration_minutes": 60,
    "did_cooldown": true,
    "protein_grams": 90
  }'
```

**Expected:** Status 201, returns JSON with ID

**Stop port-forward:**

```bash
pkill -f "port-forward"
```

**Validates:** Phase 4-5 — app deployed and reachable on K8s

---

### Step 14: Test CronJob

```bash
# Trigger the job manually (instead of waiting for schedule)
kubectl create job --from=cronjob/fitcheck-weekly-analysis \
  -n fitcheck manual-test-run

# Watch it run
kubectl get jobs -n fitcheck -w
```

**Expected:** Job shows `1/1` (one pod completed successfully)

**Check the job output:**

```bash
kubectl logs -n fitcheck -l job-name=manual-test-run
```

**Expected output** (from curl inside the job):
```json
{
  "start_date": "2026-09-01",
  "end_date": "2026-09-08",
  "total_minutes": 60,
  "active_days": 2,
  ...
}
```

**Validates:** Phase 5 — CronJob template works, can call app internally

---

### Step 15: Inspect Kubernetes resources

```bash
# Check all deployed resources
kubectl get all -n fitcheck

# Check Secrets
kubectl get secrets -n fitcheck

# Check ConfigMaps
kubectl get cm -n fitcheck

# Describe the Deployment
kubectl describe deployment fitcheck-app -n fitcheck
```

**Expected:** All resources exist, replicas are ready

**Validates:** Phase 4-5 — Secrets, Services, Deployments all created correctly

---

### Step 16: Clean up Kubernetes

```bash
# Remove Helm release
helm uninstall fitcheck -n fitcheck

# Delete namespace
kubectl delete namespace fitcheck

# Optionally stop Minikube
minikube stop

# Or delete Kind cluster
kind delete cluster --name fitcheck
```

---

## Summary: What Was Validated

| Phase | Component | Test | Status |
|-------|-----------|------|--------|
| 1 | FastAPI app | Unit tests + local run | ✅ |
| 2a | Dockerfile | Build + run container | ✅ |
| 2b | Docker Compose | Multi-container + persistence | ✅ |
| 3 | GitHub Actions | CI pipeline (proven by commits) | ✅ |
| 4 | K8s manifests | Deploy to cluster | ✅ |
| 5 | Helm chart | Multi-env, CronJob trigger | ✅ |

**All 5 phases working end-to-end.**

---

## What Each Phase Demonstrates (Interview Context)

- **Phase 1:** API design, database modeling, SQLAlchemy ORM
- **Phase 2a:** Multi-stage Dockerfile, image optimization, CVE scanning
- **Phase 2b:** Docker Compose networking, persistent volumes, database drivers
- **Phase 3:** GitHub Actions CI, automated testing, image registry security
- **Phase 4:** Kubernetes manifests, Secret management, Service networking
- **Phase 5:** Helm templating, multi-environment config, CronJob scheduling

This is a **complete, production-adjacent DevOps pipeline.**

---

## Troubleshooting

**Minikube won't start:**
```bash
minikube delete
minikube start
```

**Pods stuck in ImagePullBackOff:**
```bash
# Make sure image is loaded into the cluster
minikube image load fitcheck:dev
kubectl describe pod <pod-name> -n fitcheck
```

**CronJob not showing in Helm:**
```bash
helm get values fitcheck -n fitcheck
# Check if cronjob.enabled=true
```

**Port-forward not working:**
```bash
# Make sure the service exists
kubectl get svc -n fitcheck
# Make sure a pod is running
kubectl get pods -n fitcheck
```
