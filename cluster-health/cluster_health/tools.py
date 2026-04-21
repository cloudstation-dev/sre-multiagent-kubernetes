"""Kubernetes tools for cluster health monitoring."""

from kubernetes import client, config
from kubernetes.client.rest import ApiException


def _get_k8s_client() -> tuple[client.CoreV1Api, client.AppsV1Api]:
    """Initialize Kubernetes client with in-cluster or local config."""
    try:
        # Try in-cluster config first (when running inside K8s)
        config.load_incluster_config()
    except config.ConfigException:
        # Fall back to kubeconfig for local development
        config.load_kube_config()

    return client.CoreV1Api(), client.AppsV1Api()


def get_pods(namespace: str = "default") -> str:
    """Get all pods in a namespace with their status.

    Args:
        namespace: The Kubernetes namespace to query. Use 'all' for all namespaces.

    Returns:
        A formatted string with pod names and their current status.
    """
    core_v1, _ = _get_k8s_client()

    try:
        if namespace == "all":
            pods = core_v1.list_pod_for_all_namespaces()
        else:
            pods = core_v1.list_namespaced_pod(namespace=namespace)

        if not pods.items:
            return f"No pods found in namespace '{namespace}'."

        result = []
        for pod in pods.items:
            ns = pod.metadata.namespace
            name = pod.metadata.name
            phase = pod.status.phase

            # Get container statuses
            container_statuses = []
            if pod.status.container_statuses:
                for cs in pod.status.container_statuses:
                    ready = "Ready" if cs.ready else "NotReady"
                    restarts = cs.restart_count
                    container_statuses.append(f"{cs.name}({ready}, restarts={restarts})")

            containers_info = ", ".join(container_statuses) if container_statuses else "No containers"
            result.append(f"- {ns}/{name}: {phase} [{containers_info}]")

        return f"Pods in '{namespace}':\n" + "\n".join(result)

    except ApiException as e:
        return f"Error fetching pods: {e.reason}"


def get_nodes() -> str:
    """Get all nodes in the cluster with their status and resource capacity.

    Returns:
        A formatted string with node information including status and resources.
    """
    core_v1, _ = _get_k8s_client()

    try:
        nodes = core_v1.list_node()

        if not nodes.items:
            return "No nodes found in the cluster."

        result = []
        for node in nodes.items:
            name = node.metadata.name

            # Get node conditions
            conditions = {c.type: c.status for c in node.status.conditions}
            ready = conditions.get("Ready", "Unknown")

            # Get capacity
            capacity = node.status.capacity
            cpu = capacity.get("cpu", "?")
            memory = capacity.get("memory", "?")

            # Get node roles
            labels = node.metadata.labels or {}
            roles = [k.replace("node-role.kubernetes.io/", "")
                    for k in labels if k.startswith("node-role.kubernetes.io/")]
            role_str = ",".join(roles) if roles else "worker"

            result.append(f"- {name}: Ready={ready}, Role={role_str}, CPU={cpu}, Memory={memory}")

        return "Cluster Nodes:\n" + "\n".join(result)

    except ApiException as e:
        return f"Error fetching nodes: {e.reason}"


def get_deployments(namespace: str = "default") -> str:
    """Get all deployments in a namespace with their replica status.

    Args:
        namespace: The Kubernetes namespace to query. Use 'all' for all namespaces.

    Returns:
        A formatted string with deployment information.
    """
    _, apps_v1 = _get_k8s_client()

    try:
        if namespace == "all":
            deployments = apps_v1.list_deployment_for_all_namespaces()
        else:
            deployments = apps_v1.list_namespaced_deployment(namespace=namespace)

        if not deployments.items:
            return f"No deployments found in namespace '{namespace}'."

        result = []
        for dep in deployments.items:
            ns = dep.metadata.namespace
            name = dep.metadata.name
            desired = dep.spec.replicas or 0
            ready = dep.status.ready_replicas or 0
            available = dep.status.available_replicas or 0

            status = "Healthy" if ready == desired else "Degraded"
            result.append(f"- {ns}/{name}: {ready}/{desired} ready, {available} available [{status}]")

        return f"Deployments in '{namespace}':\n" + "\n".join(result)

    except ApiException as e:
        return f"Error fetching deployments: {e.reason}"


def get_events(namespace: str = "default", limit: int = 10) -> str:
    """Get recent events in a namespace, useful for debugging issues.

    Args:
        namespace: The Kubernetes namespace to query. Use 'all' for all namespaces.
        limit: Maximum number of events to return (default 10).

    Returns:
        A formatted string with recent events.
    """
    core_v1, _ = _get_k8s_client()

    try:
        if namespace == "all":
            events = core_v1.list_event_for_all_namespaces()
        else:
            events = core_v1.list_namespaced_event(namespace=namespace)

        if not events.items:
            return f"No events found in namespace '{namespace}'."

        # Sort by last timestamp (most recent first)
        sorted_events = sorted(
            events.items,
            key=lambda e: e.last_timestamp or e.event_time or e.metadata.creation_timestamp,
            reverse=True
        )[:limit]

        result = []
        for event in sorted_events:
            ns = event.metadata.namespace
            kind = event.involved_object.kind
            name = event.involved_object.name
            reason = event.reason
            message = event.message[:100] + "..." if len(event.message) > 100 else event.message
            event_type = event.type  # Normal or Warning

            result.append(f"- [{event_type}] {ns}/{kind}/{name}: {reason} - {message}")

        return f"Recent events in '{namespace}' (last {limit}):\n" + "\n".join(result)

    except ApiException as e:
        return f"Error fetching events: {e.reason}"


def get_resource_usage(namespace: str = "default") -> str:
    """Get resource requests and limits for pods in a namespace.

    Args:
        namespace: The Kubernetes namespace to query.

    Returns:
        A formatted string with resource usage summary.
    """
    core_v1, _ = _get_k8s_client()

    try:
        if namespace == "all":
            pods = core_v1.list_pod_for_all_namespaces()
        else:
            pods = core_v1.list_namespaced_pod(namespace=namespace)

        if not pods.items:
            return f"No pods found in namespace '{namespace}'."

        result = []
        for pod in pods.items:
            if pod.status.phase != "Running":
                continue

            ns = pod.metadata.namespace
            name = pod.metadata.name

            total_cpu_req = 0
            total_mem_req = 0

            for container in pod.spec.containers:
                if container.resources and container.resources.requests:
                    cpu_req = container.resources.requests.get("cpu", "0")
                    mem_req = container.resources.requests.get("memory", "0")

                    # Simple parsing (could be more robust)
                    if cpu_req.endswith("m"):
                        total_cpu_req += int(cpu_req[:-1])
                    elif cpu_req.isdigit():
                        total_cpu_req += int(cpu_req) * 1000

            result.append(f"- {ns}/{name}: CPU request={total_cpu_req}m")

        if not result:
            return f"No running pods with resource requests in namespace '{namespace}'."

        return f"Resource requests in '{namespace}':\n" + "\n".join(result)

    except ApiException as e:
        return f"Error fetching resource usage: {e.reason}"
