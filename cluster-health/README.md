# Cluster Health Agent

Kubernetes cluster health monitoring agent that provides visibility into pod status, node health, deployments, events, and resource usage.

## Tools

- `get_pods(namespace)` - List pods and their status
- `get_nodes()` - Get node status and capacity
- `get_deployments(namespace)` - List deployments and replica status
- `get_events(namespace, limit)` - Get recent cluster events
- `get_resource_usage(namespace)` - Get resource requests summary

## Usage

This agent is designed to be deployed via kagent and accessed via A2A protocol.
