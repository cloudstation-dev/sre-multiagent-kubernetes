# Troubleshooter Agent

Kubernetes troubleshooting agent specialized in debugging pod failures, analyzing logs, and suggesting fixes.

## Tools

- `get_pod_logs(pod, namespace, lines)` - Get pod logs
- `get_previous_pod_logs(pod, namespace, lines)` - Get logs from crashed container
- `describe_pod(pod, namespace)` - Detailed pod information
- `find_failing_pods(namespace)` - Find pods in error states
- `analyze_crashloop(pod, namespace)` - Analyze CrashLoopBackOff issues
- `check_pod_connectivity(pod, namespace)` - Check network configuration

## Usage

This agent is designed to be deployed via kagent and accessed via A2A protocol.
