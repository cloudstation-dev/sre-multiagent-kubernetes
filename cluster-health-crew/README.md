# Cluster Health Crew

A Kubernetes cluster health monitoring agent built with **CrewAI** that exposes an A2A (Agent-to-Agent) interface.

## Purpose

This agent demonstrates A2A protocol interoperability by implementing the same functionality as the `cluster-health` ADK agent but using the CrewAI framework. The SRE Coordinator can communicate with both agents using the same A2A protocol, regardless of the underlying framework.

## Features

- **Pod Monitoring**: Get pod status across namespaces
- **Node Health**: Check node conditions and capacity
- **Deployment Status**: Monitor replica availability
- **Event Tracking**: View recent cluster events
- **Resource Usage**: Analyze resource requests/limits

## Architecture

```
┌─────────────────────────────────────────────┐
│          SRE Coordinator                    │
│              (ADK)                          │
└─────────────────┬───────────────────────────┘
                  │ A2A Protocol
      ┌───────────┴───────────┬───────────────┐
      ▼                       ▼               ▼
┌─────────────┐     ┌─────────────┐   ┌─────────────┐
│ cluster-    │     │ cluster-    │   │troubleshooter│
│ health      │     │ health-crew │   │             │
│   (ADK)     │     │  (CrewAI)   │   │   (ADK)     │
└─────────────┘     └─────────────┘   └─────────────┘
```

## Build & Deploy

```bash
# Build the Docker image (must be built from python/ directory to include workspace packages)
cd /path/to/kagent/python
docker build -f samples/adk/sre-agents/cluster-health-crew/Dockerfile \
  -t <your-registry>/cluster-health-crew:v2 .
docker push <your-registry>/cluster-health-crew:v2

# Update deploy-all.yaml with your image tag, then deploy to Kubernetes
kubectl apply -f samples/adk/sre-agents/deploy-all.yaml
```

## Local Development

```bash
# Install dependencies
uv pip install -e .

# Set environment variables
export GOOGLE_API_KEY=your-key

# Run locally
python -m cluster_health_crew.main
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GOOGLE_API_KEY` | Google Gemini API key | Required |
| `PORT` | Server port | 8080 |
| `HOST` | Server host | 0.0.0.0 |

## Tools

| Tool | Description |
|------|-------------|
| `get_pods(namespace)` | List pods and their status |
| `get_nodes()` | Get node status and capacity |
| `get_deployments(namespace)` | List deployments and replica status |
| `get_events(namespace, limit)` | Recent cluster events |
| `get_resource_usage(namespace)` | Resource requests/limits summary |
