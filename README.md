# Workshop: SRE Multi-Agent System with Kagent

A hands-on workshop to build and deploy a multi-agent SRE system using kagent and the A2A (Agent-to-Agent) protocol.

## Workshop Objectives

- Build 3 specialized AI agents for SRE tasks
- Deploy agents to Kubernetes using kagent
- Demonstrate Agent-to-Agent (A2A) communication
- Interact with agents via the kagent UI

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    User Request                         │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│              SRE Coordinator Agent                      │
│  ─────────────────────────────────────────────────────  │
│  • Receives user requests                               │
│  • Classifies intent (monitoring vs debugging)          │
│  • Delegates to specialized agents via A2A              │
│  • Returns unified response                             │
└─────────────────────┬───────────────────────────────────┘
                      │ A2A Protocol
          ┌───────────┴───────────┐
          ▼                       ▼
┌─────────────────────┐ ┌─────────────────────┐
│  Cluster Health     │ │   Troubleshooter    │
│      Agent          │ │       Agent         │
│ ─────────────────── │ │ ─────────────────── │
│ • Pod status        │ │ • Log analysis      │
│ • Node health       │ │ • CrashLoop debug   │
│ • Deployments       │ │ • Error diagnosis   │
│ • Events            │ │ • Fix suggestions   │
│ • Resource usage    │ │ • Connectivity      │
└─────────────────────┘ └─────────────────────┘
          │                       │
          └───────────┬───────────┘
                      │
                      ▼
          ┌─────────────────────┐
          │   Kubernetes API    │
          │     (via RBAC)      │
          └─────────────────────┘
```

## Prerequisites

- [ ] Kubernetes cluster with kagent installed
- [ ] Install ghcr.io/kagent-dev/kagent/kagent-adk:0.9.0-beta3
- [ ] Docker to build images
- [ ] kubectl configured for your cluster
- [ ] Google Cloud account with Gemini API key

---

## Step 1 - Setup a k8s cluster using kind

You need to have installed kind tool. 

```
kind create cluster --config kind-config.yaml --name <cluster-name>
```

After you can check the k8s control plane is running: `kubectl cluster-info --context kind-<cluster-name>`



## Step 2: Get Google API Key

1. Go to https://aistudio.google.com/apikey
2. Click "Create API Key"
3. Copy and save the key (you'll need it in Step 2)
4. Run the command in your terminal: `export GOOGLE_API_KEY=<your_key>`
---

## Step 3: Install Kagent

```
helm install kagent-crds oci://ghcr.io/kagent-dev/kagent/helm/kagent-crds \
  --namespace kagent \
  --create-namespace
```

```
helm install kagent oci://ghcr.io/kagent-dev/kagent/helm/kagent \
  --namespace kagent \
  --set providers.default=gemini \
  --set providers.gemini.apiKey=$GOOGLE_API_KEY
```
---


## Step 4: Build the Docker Images

Run the `docker pull ghcr.io/kagent-dev/kagent/kagent-adk:0.9.0-beta3`. 

What is kagent-adk? It is the 'Agent Development Kit.' It is designed to facilitate the development and deployment of intelligent agents that interact directly with Kubernetes clusters.

Navigate to the `sre-agents` directory and build each agent:

### 3.1 Cluster Health Agent

```bash
cd cluster-health
docker build -t <your-registry>/cluster-health-agent:v1 .
docker push <your-registry>/cluster-health-agent:v1
```

### 3.2 Troubleshooter Agent

```bash
cd ../troubleshooter
docker build -t <your-registry>/troubleshooter-agent:v1 .
docker push <your-registry>/troubleshooter-agent:v1
```

### 3.3 SRE Coordinator

```bash
cd ../coordinator
docker build -t <your-registry>/sre-coordinator:v1 .
docker push <your-registry>/sre-coordinator:v1
```

---

## Step 4: Configure the Deployment

Edit `deploy-all.yaml` and replace the image references with your registry:

```yaml
# Line ~62: Cluster Health Agent
image: <your-registry>/cluster-health-agent:v1

# Line ~116: Troubleshooter Agent
image: <your-registry>/troubleshooter-agent:v1

# Line ~139: SRE Coordinator
image: <your-registry>/sre-coordinator:v1
```

---

## Step 5: Deploy the Agents

```bash
kubectl apply -f deploy-all.yaml
```

This will create:
- ServiceAccounts and RBAC permissions
- Three Agent custom resources
- Deployments and Services for each agent

---

## Step 6: Verify the Deployment

### Check the agents are registered

```bash
kubectl get agents -n kagent
```

Expected output:
```
NAME                   AGE
cluster-health-agent   1m
troubleshooter-agent   1m
sre-coordinator        1m
```

### Check the pods are running

```bash
kubectl get pods -n kagent | grep -E "(cluster-health|troubleshooter|coordinator)"
```

Expected output:
```
cluster-health-agent-xxxxx   1/1     Running   0   1m
troubleshooter-agent-xxxxx   1/1     Running   0   1m
sre-coordinator-xxxxx        1/1     Running   0   1m
```

### Check the services exist

```bash
kubectl get svc -n kagent | grep -E "(cluster-health|troubleshooter|coordinator)"
```

---

## Step 7: Access the Kagent UI

Start port-forwarding to the kagent UI:

```bash
kubectl port-forward -n kagent svc/kagent-ui 3000:8080
```

Open your browser and navigate to: **http://localhost:3000**

---

## Step 8: Test the Agents

### Option A: Direct Agent Access (Recommended for testing)

1. Open http://localhost:3000
2. Select **cluster-health-agent** from the agent list
3. Send a message: `What pods are running in the kagent namespace?`
4. The agent will query the Kubernetes API and respond

### Option B: Via the Coordinator (A2A demonstration)

1. Select **sre-coordinator** from the agent list
2. Ask: `Is my cluster healthy?`
3. The coordinator will:
   - Analyze your request
   - Delegate to the Cluster Health Agent via A2A
   - Return a unified response

### Option C: Troubleshooting Flow

1. Select **sre-coordinator**
2. Ask: `Why are pods failing in the default namespace?`
3. The coordinator will delegate to the Troubleshooter Agent

---

## Example Prompts

| Agent | Example Prompts |
|-------|-----------------|
| **Cluster Health** | "Show me all pods in kube-system namespace" |
| **Cluster Health** | "Are all nodes healthy?" |
| **Cluster Health** | "What deployments are running?" |
| **Cluster Health** | "Show me recent warning events" |
| **Troubleshooter** | "Why is pod nginx-xxx crashing?" |
| **Troubleshooter** | "Show me logs from pod my-app" |
| **Troubleshooter** | "Find all failing pods" |
| **Troubleshooter** | "Analyze the CrashLoopBackOff for pod X" |
| **Coordinator** | "Check my cluster health and report any issues" |
| **Coordinator** | "Debug the failing pods in production namespace" |

---

## Agent Tools Reference

### Cluster Health Agent

| Tool | Description |
|------|-------------|
| `get_pods(namespace)` | List pods and their status |
| `get_nodes()` | Get node status and capacity |
| `get_deployments(namespace)` | List deployments and replica status |
| `get_events(namespace)` | Recent cluster events |
| `get_resource_usage(namespace)` | Resource requests/limits summary |

### Troubleshooter Agent

| Tool | Description |
|------|-------------|
| `get_pod_logs(pod, namespace)` | Get current pod logs |
| `get_previous_pod_logs(pod, namespace)` | Logs from previous crashed container |
| `describe_pod(pod, namespace)` | Detailed pod information |
| `find_failing_pods(namespace)` | Find pods in error states |
| `analyze_crashloop(pod, namespace)` | Comprehensive CrashLoopBackOff analysis |
| `check_pod_connectivity(pod, namespace)` | Network configuration check |

---

## Troubleshooting

### Pods not starting

Check the pod logs:
```bash
kubectl logs -n kagent -l app.kubernetes.io/name=cluster-health-agent
```

Check pod events:
```bash
kubectl describe pod -n kagent -l app.kubernetes.io/name=cluster-health-agent
```

### RBAC permission errors

Verify the ServiceAccount has correct permissions:
```bash
kubectl auth can-i list pods --as=system:serviceaccount:kagent:cluster-health-agent-sa
```

### Model 503 errors

The Gemini model is experiencing high demand. Wait a few minutes and try again.

### A2A connection errors

Verify the agent services exist and are accessible:
```bash
kubectl get svc -n kagent | grep -E "(cluster-health|troubleshooter)"
```

Test connectivity from coordinator:
```bash
kubectl exec -n kagent deploy/sre-coordinator -- \
  curl -s http://cluster-health-agent.kagent:8080/.well-known/agent-card.json
```

---

## RBAC Permissions Summary

| Agent | Resources | Verbs |
|-------|-----------|-------|
| Cluster Health | pods, nodes, events, services, deployments | get, list, watch |
| Troubleshooter | pods, pods/log, events, services | get, list, watch |
| Coordinator | None (HTTP only to other agents) | - |

---

## Cleanup

To remove all deployed resources:

```bash
# Delete the agents and RBAC
kubectl delete -f deploy-all.yaml

# Delete the API key secret
kubectl delete secret kagent-google -n kagent
```

---

## What You Learned

- How to build custom agents with kagent-adk
- How to deploy BYO (Bring Your Own) agents to Kubernetes
- How the A2A protocol enables agent-to-agent communication
- How to use RBAC to give agents Kubernetes API access
- How to interact with agents via the kagent UI

---

## Next Steps

- Add more specialized agents (e.g., cost analyzer, security scanner)
- Implement custom tools for your specific use cases
- Explore streaming responses for real-time output
- Add memory/context persistence for multi-turn conversations
