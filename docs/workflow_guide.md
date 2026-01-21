# 🔄 Complete Workflow Guide

## Table of Contents
1. [Setup & Installation](#setup--installation)
2. [Development Workflow](#development-workflow)
3. [Incident Response Workflow](#incident-response-workflow)
4. [CI/CD Pipeline Flow](#cicd-pipeline-flow)
5. [Daily Operations](#daily-operations)

---

## 🚀 Setup & Installation

### Prerequisites Checklist
- [ ] Azure account with appropriate permissions
- [ ] Azure CLI installed (`az --version`)
- [ ] Terraform >= 1.5.0 installed
- [ ] kubectl installed
- [ ] Helm >= 3.12.0 installed
- [ ] Docker Desktop (for local development)
- [ ] Python 3.9+ installed
- [ ] Git configured

### Step 1: Clone Repository

```bash
git clone https://github.com/yourusername/ai-autonomous-devops.git
cd ai-autonomous-devops
```

### Step 2: Configure Azure Credentials

```bash
# Login to Azure
az login

# Set subscription
az account set --subscription "Your-Subscription-Name"

# Create service principal for Terraform
az ad sp create-for-rbac --name "terraform-aiops" \
  --role="Contributor" \
  --scopes="/subscriptions/YOUR_SUBSCRIPTION_ID"

# Save the output (appId, password, tenant)
```

### Step 3: Setup Environment Variables

```bash
# Copy example env file
cp .env.example .env

# Edit .env file
nano .env
```

Required variables in `.env`:
```env
# Azure
AZURE_SUBSCRIPTION_ID=your-subscription-id
AZURE_TENANT_ID=your-tenant-id
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-client-secret

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://your-openai.openai.azure.com/
AZURE_OPENAI_KEY=your-api-key
AZURE_OPENAI_DEPLOYMENT=gpt-4

# Database
POSTGRES_HOST=your-postgres-host
POSTGRES_DB=aiops
POSTGRES_USER=aiops
POSTGRES_PASSWORD=secure-password

# Slack (optional)
SLACK_BOT_TOKEN=xoxb-your-token
SLACK_APP_TOKEN=xapp-your-token

# Monitoring
PROMETHEUS_URL=http://prometheus:9090
LOKI_URL=http://loki:3100
```

### Step 4: Deploy Infrastructure with Terraform

```bash
cd infra/terraform

# Initialize Terraform
terraform init

# Create terraform.tfvars
cat > terraform.tfvars <<EOF
prefix              = "aiops"
environment         = "production"
location            = "eastus"
kubernetes_version  = "1.28"
db_admin_username   = "aiopsadmin"
db_admin_password   = "YourSecurePassword123!"
EOF

# Plan deployment
terraform plan -out=tfplan

# Apply (this takes 15-20 minutes)
terraform apply tfplan

# Save outputs
terraform output -json > outputs.json
```

### Step 5: Configure kubectl

```bash
# Get AKS credentials
az aks get-credentials \
  --resource-group aiops-rg \
  --name aiops-aks \
  --overwrite-existing

# Verify connection
kubectl get nodes
```

### Step 6: Install Observability Stack

```bash
cd ../../

# Add Helm repositories
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update

# Create monitoring namespace
kubectl create namespace monitoring

# Install Prometheus
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --values observability/prometheus/values.yaml \
  --wait

# Install Loki
helm install loki grafana/loki-stack \
  --namespace monitoring \
  --values observability/loki/values.yaml \
  --wait

# Verify installations
kubectl get pods -n monitoring
```

### Step 7: Deploy AI Engine

```bash
# Build and push Docker image
cd ai-engine
docker build -t aiopsacr.azurecr.io/aiops/ai-engine:v1.0 .

# Login to ACR
az acr login --name aiopsacr

# Push image
docker push aiopsacr.azurecr.io/aiops/ai-engine:v1.0

# Deploy with Helm
cd ../infra/helm
helm install ai-engine ./ai-engine \
  --namespace production \
  --create-namespace \
  --set image.tag=v1.0 \
  --wait

# Verify deployment
kubectl get pods -n production
kubectl logs -n production -l app=ai-engine
```

### Step 8: Setup ChatOps (Optional)

```bash
cd ../../chatops/slack-bot

# Install dependencies
pip install -r requirements.txt

# Run bot
python bot.py
```

---

## 💻 Development Workflow

### Local Development Setup

```bash
# Start local environment with Docker Compose
docker-compose up -d

# Check all services are running
docker-compose ps

# View logs
docker-compose logs -f ai-engine

# Access services:
# - AI Engine API: http://localhost:8000
# - Grafana: http://localhost:3000 (admin/admin)
# - Prometheus: http://localhost:9090
```

### Making Code Changes

```bash
# Create feature branch
git checkout -b feature/new-rca-algorithm

# Make changes to code
nano ai-engine/llm/rca_agent.py

# Run tests locally
cd ai-engine
pytest tests/unit/ -v

# Format code
black .
flake8 .

# Commit changes
git add .
git commit -m "feat: improve RCA analysis algorithm"

# Push to remote
git push origin feature/new-rca-algorithm

# Create Pull Request on GitHub
```

### Testing Changes

```bash
# Unit tests
pytest tests/unit/ -v --cov

# Integration tests (requires running services)
pytest tests/integration/ -v

# End-to-end tests
pytest tests/e2e/ -v

# Load testing
locust -f tests/load/locustfile.py --host=http://localhost:8000
```

---

## 🚨 Incident Response Workflow

### Automatic Flow (No Human Intervention)

```
1. Prometheus detects metric anomaly (CPU > 90%)
   ↓
2. Alert sent to AI Engine webhook
   ↓
3. AI Engine:
   - Fetches logs from Loki
   - Fetches metrics from Prometheus
   - Analyzes with GPT-4
   ↓
4. RCA Generated:
   - Root Cause: Memory leak in order-service
   - Confidence: 92%
   - Severity: High
   ↓
5. Fix Generator creates Helm update:
   resources:
     limits:
       memory: 2Gi  # (was 1Gi)
   ↓
6. Auto-remediation (if confidence > 85%):
   - Create Git branch: auto-fix/INC-2024-001
   - Apply Helm upgrade
   - Run validation tests
   ↓
7. CI/CD Pipeline:
   - Build & test
   - Deploy to staging
   - Validate
   - Deploy to production
   ↓
8. Notification sent to Slack:
   ✅ Incident INC-2024-001 resolved in 4 minutes
```

### Manual Investigation Flow

```bash
# 1. Query incident via Slack
@aiops-bot show me incidents in last 1h

# 2. Get details
@aiops-bot analyze incident INC-2024-001

# 3. Check anomalies
/anomalies payment-service

# 4. Get recommendations
@aiops-bot what caused the latency spike at 2pm?

# Response from AI:
🔍 Analysis Complete
Cause: Database connection pool exhausted
Impact: +450ms latency (p95)
Recommendation: Increase pool size 50→100
Confidence: 0.89

# 5. Apply fix
/remediate INC-2024-001 --approve

# 6. Monitor
kubectl get pods -n production -w
```

---

## 🔄 CI/CD Pipeline Flow

### Trigger Points
1. **Push to `develop` branch** → Deploy to Staging
2. **Push to `main` branch** → Deploy to Production
3. **Pull Request** → Run tests only

### Pipeline Stages

#### Stage 1: Build & Test (5-10 minutes)
```yaml
Jobs:
  - Unit Tests (Python)
  - Security Scanning (Bandit, Safety)
  - Code Quality (Black, Flake8)
  - Build Docker Image
  - Push to ACR
```

#### Stage 2: Deploy to Staging (3-5 minutes)
```yaml
Steps:
  - Helm upgrade (staging namespace)
  - Wait for rollout
  - Smoke tests
  - API integration tests
```

#### Stage 3: AI/ML Validation (2-3 minutes)
```yaml
Tests:
  - Validate anomaly detection model accuracy
  - Test LLM prompt responses
  - Check model inference latency
```

#### Stage 4: Production Deployment (10-15 minutes)
```yaml
Strategy: Blue-Green Deployment
Steps:
  1. Deploy "green" version (new)
  2. Wait for health checks
  3. Run smoke tests
  4. Monitor error rates for 5 minutes
  5. Switch traffic from blue → green
  6. Monitor for 10 minutes
  7. Remove old "blue" deployment
  
Rollback if:
  - Error rate > 1%
  - Response time > 2x baseline
  - Health check failures
```

### Manual Pipeline Trigger

```bash
# Trigger via Azure CLI
az pipelines run \
  --name "ai-autonomous-devops-CI" \
  --branch main

# Monitor pipeline
az pipelines runs show --id <run-id>
```

---

## 📅 Daily Operations

### Morning Checks (9:00 AM)

```bash
# 1. Check overnight incidents
kubectl get incidents -n production --since=24h

# Or via Slack:
/incidents 24h

# 2. Review Grafana dashboard
# Open: http://grafana.yourdomain.com/d/aiops-overview

# 3. Check ML model performance
curl http://ai-engine.production.svc.cluster.local:8000/metrics | grep aiops_model

# 4. Review auto-remediation success rate
curl http://ai-engine/api/v1/stats/remediation
```

### Weekly Maintenance (Monday 10:00 AM)

```bash
# 1. Retrain anomaly detection model
python ai-engine/anomaly-detection/train_model.py \
  --data-range=7d \
  --output=models/anomaly_detector_$(date +%Y%m%d).pkl

# 2. Update LLM prompts if needed
# Edit: ai-engine/llm/prompt_templates.py

# 3. Review and update alert thresholds
# Edit: observability/prometheus/alerts/sre-alerts.yaml
kubectl apply -f observability/prometheus/alerts/sre-alerts.yaml

# 4. Check for dependency updates
cd ai-engine
pip list --outdated
```

### Monthly Tasks (1st of Month)

```bash
# 1. Generate incident report
python scripts/generate_incident_report.py --month=last

# 2. Review AI model drift
python scripts/check_model_drift.py

# 3. Update documentation
python scripts/generate_api_docs.py

# 4. Disaster recovery test
# - Test backup restoration
# - Verify runbooks
# - Update on-call schedules
```

---

## 🎯 Key Metrics to Monitor

### SRE Metrics
- **MTTR** (Mean Time To Resolution): Target < 5 minutes
- **MTTD** (Mean Time To Detection): Target < 1 minute
- **Auto-remediation Success Rate**: Target > 85%
- **False Positive Rate**: Target < 5%

### AI/ML Metrics
- **Model Accuracy**: Target > 90%
- **LLM Confidence Score**: Average > 0.85
- **Inference Latency**: Target < 2 seconds
- **Token Usage**: Monitor costs

### Infrastructure Metrics
- **API Response Time**: p95 < 500ms
- **Error Rate**: < 0.1%
- **Resource Utilization**: 60-80% (optimal)
- **Pod Restart Count**: < 5 per day

---

## 🆘 Troubleshooting

### AI Engine Not Starting

```bash
# Check logs
kubectl logs -n production -l app=ai-engine --tail=100

# Common issues:
# 1. Azure OpenAI connection
kubectl exec -n production ai-engine-xxx -- \
  curl https://your-openai.openai.azure.com/

# 2. Database connection
kubectl exec -n production ai-engine-xxx -- \
  nc -zv postgres 5432

# 3. Check secrets
kubectl get secret ai-engine-secrets -n production -o yaml
```

### Prometheus Not Scraping Metrics

```bash
# Check targets
kubectl port-forward -n monitoring prometheus-0 9090:9090
# Open: http://localhost:9090/targets

# Check service discovery
kubectl get servicemonitor -n production

# Verify annotations on pods
kubectl get pods -n production -o yaml | grep prometheus
```

### Grafana Dashboard Not Showing Data

```bash
# Test Prometheus datasource
kubectl port-forward -n monitoring grafana-xxx 3000:3000

# In Grafana UI:
# Configuration → Data Sources → Prometheus → Test

# Check Loki datasource
# Configuration → Data Sources → Loki → Test
```

---

## 📚 Additional Resources

- **API Documentation**: http://ai-engine.yourdomain.com/docs
- **Grafana Dashboards**: http://grafana.yourdomain.com
- **Runbooks**: `docs/runbooks/`
- **Architecture Diagrams**: `docs/architecture.md`
- **Incident Playbooks**: `docs/playbooks/`

---

## 🎓 Learning Path

1. **Week 1**: Setup local environment, understand architecture
2. **Week 2**: Deploy to staging, run test scenarios
3. **Week 3**: Customize LLM prompts, tune ML models
4. **Week 4**: Production deployment, monitoring setup
5. **Week 5+**: Optimize, add new features, expand coverage

---

**Questions?** Open an issue on GitHub or reach out to the team!