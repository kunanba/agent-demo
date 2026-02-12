# Cloud Deployment Guide

This document outlines deployment strategies for the Financial Document Analysis Agent across major cloud providers: Azure, AWS, and GCP.

## Azure Deployment (Recommended)

### Architecture

```
Azure Front Door
      ↓
Azure Container Apps (Agent API / Streamlit)
      ↓
├─ Azure OpenAI Service (GPT-4, GPT-4 Vision)
├─ Azure AI Search (Hybrid Search)
├─ Azure Cosmos DB (Conversation State)
├─ Azure Blob Storage (Documents, Images)
├─ Azure Monitor (Logging, Tracing)
├─ Azure Key Vault (Secrets)
└─ Azure Entra ID (Authentication)
```

### Services Breakdown

#### 1. Compute - Azure Container Apps

**Service**: Streamlit UI + Agent API

**Configuration**:
```yaml
apiVersion: apps/v1
kind: Deployment
spec:
  replicas: 3
  resources:
    requests:
      cpu: "1"
      memory: "2Gi"
    limits:
      cpu: "2"
      memory: "4Gi"
  
  environmentVariables:
    - name: AZURE_OPENAI_ENDPOINT
      valueFrom: keyVault
```

**Scaling**:
- Min: 2 instances
- Max: 10 instances
- CPU scaling: 70% threshold
- HTTP scaling: 100 concurrent requests

**Cost**: $100-500/month (B1-B3 tier)

#### 2. AI Services - Azure OpenAI

**Models Deployed**:
- GPT-4 (gpt-4, 10K TPM)
- GPT-4 Vision (gpt-4-vision, 5K TPM)

**Configuration**:
- Region: East US (availability)
- SKU: Standard
- Rate limiting: Built-in
- Content filtering: Enabled

**Cost**: $0.03/1K tokens (GPT-4), usage-based

#### 3. Search - Azure AI Search

**Tier**: Standard (S1)

**Index Configuration**:
- Documents: 10K-100K
- Vector dimensions: 384
- Hybrid search enabled
- Semantic reranking enabled

**Scaling**:
- Replicas: 2 (HA)
- Partitions: 1

**Cost**: $250/month (S1 tier)

#### 4. State - Azure Cosmos DB

**Purpose**: Conversation state, session management

**Configuration**:
- API: MongoDB
- Consistency: Session
- Throughput: 400 RU/s (autoscale)

**Collections**:
- `conversations`: Chat history
- `sessions`: User sessions

**Cost**: $24/month (serverless) or $50/month (400 RU/s)

#### 5. Storage - Azure Blob Storage

**Purpose**: Document storage, uploaded images

**Configuration**:
- Tier: Hot
- Redundancy: LRS
- Lifecycle policies: Archive after 90 days

**Containers**:
- `documents`: PDFs, source files
- `images`: Charts, uploaded images
- `processed`: Chunked data

**Cost**: $0.02/GB/month + operations

#### 6. Observability - Azure Monitor

**Components**:
- Application Insights (APM)
- Log Analytics (logs)
- OpenTelemetry integration

**Metrics Tracked**:
- Request latency (p50, p95, p99)
- Error rates
- Tool usage statistics
- Document retrieval performance
- LLM token usage

**Alerts**:
- Latency > 10s
- Error rate > 5%
- Service health

**Cost**: $2-10/GB ingested

#### 7. Security - Azure Key Vault & Entra ID

**Key Vault**:
- OpenAI API keys
- Search API keys
- Connection strings
- Certificates

**Entra ID**:
- User authentication (OAuth 2.0)
- RBAC for resource access
- Service principal for services

**Cost**: $0.03/10K operations

### Deployment Process

#### 1. Infrastructure Setup (Bicep/Terraform)

```bash
# Login to Azure
az login

# Create resource group
az group create --name rg-financial-agent --location eastus

# Deploy infrastructure
az deployment group create \
  --resource-group rg-financial-agent \
  --template-file infrastructure/azure/main.bicep \
  --parameters @parameters.json

# Store secrets
az keyvault secret set \
  --vault-name kv-financial-agent \
  --name openai-api-key \
  --value $OPENAI_API_KEY
```

#### 2. Build and Push Container

```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src/ ./src/
COPY data/ ./data/

EXPOSE 8501

CMD ["streamlit", "run", "src/ui/app.py", "--server.port=8501"]
```

```bash
# Build
docker build -t financial-agent:latest .

# Tag for ACR
docker tag financial-agent:latest myacr.azurecr.io/financial-agent:latest

# Push
az acr login --name myacr
docker push myacr.azurecr.io/financial-agent:latest
```

#### 3. Deploy to Container Apps

```bash
az containerapp create \
  --name financial-agent \
  --resource-group rg-financial-agent \
  --image myacr.azurecr.io/financial-agent:latest \
  --target-port 8501 \
  --ingress external \
  --min-replicas 2 \
  --max-replicas 10 \
  --cpu 1.0 --memory 2.0Gi \
  --env-vars "AZURE_OPENAI_ENDPOINT=secretref:openai-endpoint"
```

### Cost Estimate (Monthly)

| Service | Configuration | Cost |
|---------|--------------|------|
| Container Apps | 2-10 instances, B2 | $200-500 |
| Azure OpenAI | ~1M tokens/month | $30-100 |
| Azure AI Search | S1, 2 replicas | $250 |
| Cosmos DB | 400 RU/s | $50 |
| Blob Storage | 100 GB | $2 |
| Monitor + Insights | 10 GB logs | $10 |
| Key Vault | Secrets storage | $1 |
| **Total** | | **$543-913/month** |

### Monitoring & Operations

**Dashboards**:
- Azure Portal dashboard with key metrics
- Grafana for custom visualizations
- Streamlit admin page for agent stats

**Alerts**:
- PagerDuty integration for critical issues
- Email for warnings
- Slack for informational

**Backup**:
- Cosmos DB: Continuous backup (7 days)
- Blob Storage: Soft delete (7 days)

---

## AWS Deployment

### Architecture

```
CloudFront
      ↓
ECS Fargate (Agent)
      ↓
├─ Amazon Bedrock (Claude/GPT-4)
├─ OpenSearch Service (Vector Search)
├─ DynamoDB (State)
├─ S3 (Storage)
├─ CloudWatch (Observability)
├─ Secrets Manager
└─ Cognito (Auth)
```

### Key Services

1. **Compute**: ECS Fargate
   - Serverless containers
   - Auto-scaling based on CPU/memory
   - Cost: ~$50-200/month

2. **LLM**: Amazon Bedrock
   - Claude 3 or GPT-4 (via Bedrock)
   - Pay-per-token pricing
   - Cost: $30-100/month

3. **Search**: OpenSearch Service
   - Vector search plugin
   - t3.small instances (dev), m5.large (prod)
   - Cost: $100-300/month

4. **State**: DynamoDB
   - On-demand pricing
   - Session and conversation storage
   - Cost: $10-30/month

5. **Storage**: S3
   - Standard tier for active documents
   - Glacier for archives
   - Cost: $5-20/month

6. **Observability**: CloudWatch + X-Ray
   - Logs, metrics, traces
   - Cost: $10-50/month

**Total Monthly Cost**: $205-700

### Deployment

```bash
# Build and push to ECR
aws ecr get-login-password | docker login --username AWS --password-stdin $ECR_URI
docker build -t financial-agent .
docker tag financial-agent:latest $ECR_URI/financial-agent:latest
docker push $ECR_URI/financial-agent:latest

# Deploy via ECS
aws ecs create-service \
  --cluster financial-agent-cluster \
  --service-name agent-service \
  --task-definition agent-task:1 \
  --desired-count 2 \
  --launch-type FARGATE
```

### Key Differences from Azure

- **LLM**: Bedrock instead of Azure OpenAI (may need model adjustments)
- **Search**: OpenSearch requires custom vector implementation vs Azure AI Search
- **Auth**: Cognito instead of Entra ID
- **Networking**: VPC, security groups vs VNet, NSGs

---

## GCP Deployment

### Architecture

```
Cloud Load Balancer
      ↓
Cloud Run (Agent)
      ↓
├─ Vertex AI (PaLM 2 / GPT-4 via Model Garden)
├─ Vertex AI Search (Vector Search)
├─ Firestore (State)
├─ Cloud Storage (Docs)
├─ Cloud Logging + Trace (Observability)
├─ Secret Manager
└─ Identity Platform (Auth)
```

### Key Services

1. **Compute**: Cloud Run
   - Fully managed serverless
   - Pay per request
   - Auto-scaling
   - Cost: $20-100/month

2. **LLM**: Vertex AI
   - PaLM 2, GPT-4 (Model Garden)
   - Token-based pricing
   - Cost: $30-100/month

3. **Search**: Vertex AI Search
   - Managed vector search
   - Semantic retrieval
   - Cost: $100-250/month

4. **State**: Firestore
   - NoSQL document database
   - Real-time sync
   - Cost: $10-30/month

5. **Storage**: Cloud Storage
   - Multi-regional buckets
   - Lifecycle policies
   - Cost: $5-20/month

6. **Observability**: Cloud Logging + Trace
   - Native OpenTelemetry support
   - Cost: $10-40/month

**Total Monthly Cost**: $175-540

### Deployment

```bash
# Build and deploy to Cloud Run
gcloud builds submit --tag gcr.io/PROJECT_ID/financial-agent

gcloud run deploy financial-agent \
  --image gcr.io/PROJECT_ID/financial-agent \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --min-instances 1 \
  --max-instances 10 \
  --memory 2Gi \
  --cpu 2
```

### Key Differences

- **Serverless-first**: Cloud Run vs containerized deployments
- **LLM**: Vertex AI (PaLM) is Google-native, GPT-4 via Model Garden
- **Search**: Vertex AI Search is more integrated
- **Auth**: Identity Platform vs Entra ID / Cognito

---

## Multi-Cloud Comparison

| Aspect | Azure | AWS | GCP |
|--------|-------|-----|-----|
| **Best For** | Enterprise, Microsoft stack | AWS-native orgs, broad services | ML/AI workloads, cost-efficiency |
| **LLM** | Azure OpenAI (native GPT-4) | Bedrock (Claude, Titan) | Vertex AI (PaLM, GPT via Garden) |
| **Search** | Azure AI Search (best hybrid) | OpenSearch (DIY) | Vertex AI Search (managed) |
| **Ease of Setup** | Medium | Medium-Hard | Easy |
| **Cost** | $543-913/mo | $205-700/mo | $175-540/mo |
| **Observability** | Azure Monitor (excellent) | CloudWatch + X-Ray | Cloud Logging (good) |
| **Auth** | Entra ID (enterprise) | Cognito | Identity Platform |

## Security Best Practices (All Clouds)

### 1. Access Control
- Principle of least privilege
- Service accounts for inter-service communication
- API key rotation (30-90 days)
- MFA for all admin access

### 2. Network Security
- Private endpoints for databases
- VPC/VNet isolation
- Web Application Firewall (WAF)
- DDoS protection

### 3. Data Protection
- Encryption at rest (AES-256)
- Encryption in transit (TLS 1.3)
- Customer-managed keys (CMK)
- Data residency compliance

### 4. Monitoring
- Failed authentication alerts
- Unusual API usage patterns
- Data exfiltration detection
- Compliance audit logs

### 5. Compliance
- GDPR readiness (data deletion)
- SOC 2 controls
- PII detection and masking
- Audit trail retention (1+ year)

## Cost Optimization Strategies

1. **Reserved Instances**: 30-40% savings on compute
2. **Spot/Preemptible**: 70% savings for batch processing
3. **Auto-scaling**: Scale down during off-hours
4. **Storage Tiering**: Move old data to cold storage
5. **CDN Caching**: Reduce compute requests
6. **Serverless**: Pay only for actual usage

## Production Checklist

- [ ] Infrastructure as Code (Terraform/Bicep)
- [ ] CI/CD pipeline (GitHub Actions / Azure DevOps)
- [ ] Automated testing (unit, integration, e2e)
- [ ] Load testing (100+ concurrent users)
- [ ] Security scanning (Snyk, SonarQube)
- [ ] Disaster recovery plan (RTO < 4hr, RPO < 1hr)
- [ ] Runbook for common issues
- [ ] On-call rotation setup
- [ ] Cost monitoring and alerts
- [ ] Performance baselines established
