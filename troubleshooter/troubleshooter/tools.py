"""Kubernetes troubleshooting tools for debugging issues."""

from kubernetes import client, config
from kubernetes.client.rest import ApiException


def _get_k8s_client() -> client.CoreV1Api:
    """Initialize Kubernetes client with in-cluster or local config."""
    try:
        config.load_incluster_config()
    except config.ConfigException:
        config.load_kube_config()

    return client.CoreV1Api()


def get_pod_logs(pod_name: str, namespace: str = "default", lines: int = 50) -> str:
    """Get logs from a specific pod.

    Args:
        pod_name: Name of the pod to get logs from.
        namespace: The namespace where the pod is located.
        lines: Number of recent log lines to retrieve (default 50).

    Returns:
        The pod logs as a string.
    """
    core_v1 = _get_k8s_client()

    try:
        logs = core_v1.read_namespaced_pod_log(
            name=pod_name,
            namespace=namespace,
            tail_lines=lines,
        )

        if not logs:
            return f"No logs found for pod '{pod_name}' in namespace '{namespace}'."

        return f"Logs for pod '{namespace}/{pod_name}' (last {lines} lines):\n\n{logs}"

    except ApiException as e:
        if e.status == 404:
            return f"Pod '{pod_name}' not found in namespace '{namespace}'."
        return f"Error fetching logs: {e.reason}"


def get_previous_pod_logs(pod_name: str, namespace: str = "default", lines: int = 50) -> str:
    """Get logs from the previous instance of a pod (useful for crash analysis).

    Args:
        pod_name: Name of the pod to get logs from.
        namespace: The namespace where the pod is located.
        lines: Number of recent log lines to retrieve (default 50).

    Returns:
        The previous pod logs as a string.
    """
    core_v1 = _get_k8s_client()

    try:
        logs = core_v1.read_namespaced_pod_log(
            name=pod_name,
            namespace=namespace,
            tail_lines=lines,
            previous=True,
        )

        if not logs:
            return f"No previous logs found for pod '{pod_name}'."

        return f"Previous logs for pod '{namespace}/{pod_name}' (last {lines} lines):\n\n{logs}"

    except ApiException as e:
        if e.status == 400:
            return f"No previous container found for pod '{pod_name}'. The pod may not have restarted."
        if e.status == 404:
            return f"Pod '{pod_name}' not found in namespace '{namespace}'."
        return f"Error fetching previous logs: {e.reason}"


def describe_pod(pod_name: str, namespace: str = "default") -> str:
    """Get detailed information about a pod, similar to 'kubectl describe pod'.

    Args:
        pod_name: Name of the pod to describe.
        namespace: The namespace where the pod is located.

    Returns:
        Detailed pod information including conditions, events, and container status.
    """
    core_v1 = _get_k8s_client()

    try:
        pod = core_v1.read_namespaced_pod(name=pod_name, namespace=namespace)

        result = [f"Pod: {namespace}/{pod_name}"]
        result.append(f"Status: {pod.status.phase}")
        result.append(f"Node: {pod.spec.node_name or 'Not scheduled'}")
        result.append(f"IP: {pod.status.pod_ip or 'None'}")

        # Conditions
        result.append("\nConditions:")
        if pod.status.conditions:
            for cond in pod.status.conditions:
                result.append(f"  - {cond.type}: {cond.status} (Reason: {cond.reason or 'N/A'})")

        # Container statuses
        result.append("\nContainers:")
        if pod.status.container_statuses:
            for cs in pod.status.container_statuses:
                result.append(f"  - {cs.name}:")
                result.append(f"      Ready: {cs.ready}")
                result.append(f"      Restart Count: {cs.restart_count}")

                if cs.state.running:
                    result.append(f"      State: Running (since {cs.state.running.started_at})")
                elif cs.state.waiting:
                    result.append(f"      State: Waiting (Reason: {cs.state.waiting.reason})")
                    if cs.state.waiting.message:
                        result.append(f"      Message: {cs.state.waiting.message}")
                elif cs.state.terminated:
                    result.append(f"      State: Terminated (Reason: {cs.state.terminated.reason})")
                    result.append(f"      Exit Code: {cs.state.terminated.exit_code}")

        # Get related events
        events = core_v1.list_namespaced_event(
            namespace=namespace,
            field_selector=f"involvedObject.name={pod_name}"
        )

        if events.items:
            result.append("\nRecent Events:")
            sorted_events = sorted(
                events.items,
                key=lambda e: e.last_timestamp or e.metadata.creation_timestamp,
                reverse=True
            )[:5]
            for event in sorted_events:
                result.append(f"  - [{event.type}] {event.reason}: {event.message}")

        return "\n".join(result)

    except ApiException as e:
        if e.status == 404:
            return f"Pod '{pod_name}' not found in namespace '{namespace}'."
        return f"Error describing pod: {e.reason}"


def find_failing_pods(namespace: str = "default") -> str:
    """Find pods that are in a failing state (CrashLoopBackOff, Error, etc.).

    Args:
        namespace: The namespace to search. Use 'all' for all namespaces.

    Returns:
        A list of failing pods with their error reasons.
    """
    core_v1 = _get_k8s_client()

    try:
        if namespace == "all":
            pods = core_v1.list_pod_for_all_namespaces()
        else:
            pods = core_v1.list_namespaced_pod(namespace=namespace)

        failing_pods = []

        for pod in pods.items:
            ns = pod.metadata.namespace
            name = pod.metadata.name
            issues = []

            # Check pod phase
            if pod.status.phase in ["Failed", "Unknown"]:
                issues.append(f"Phase: {pod.status.phase}")

            # Check container statuses
            if pod.status.container_statuses:
                for cs in pod.status.container_statuses:
                    if cs.state.waiting:
                        reason = cs.state.waiting.reason
                        if reason in ["CrashLoopBackOff", "ImagePullBackOff", "ErrImagePull",
                                     "CreateContainerError", "InvalidImageName"]:
                            issues.append(f"{cs.name}: {reason}")
                    elif cs.state.terminated:
                        if cs.state.terminated.exit_code != 0:
                            issues.append(
                                f"{cs.name}: Terminated with exit code {cs.state.terminated.exit_code}"
                            )

                    # High restart count
                    if cs.restart_count >= 5:
                        issues.append(f"{cs.name}: High restart count ({cs.restart_count})")

            if issues:
                failing_pods.append(f"- {ns}/{name}:\n    " + "\n    ".join(issues))

        if not failing_pods:
            return f"No failing pods found in namespace '{namespace}'."

        return f"Failing pods in '{namespace}':\n" + "\n".join(failing_pods)

    except ApiException as e:
        return f"Error finding failing pods: {e.reason}"


def analyze_crashloop(pod_name: str, namespace: str = "default") -> str:
    """Analyze a pod in CrashLoopBackOff state and suggest possible fixes.

    Args:
        pod_name: Name of the crashing pod.
        namespace: The namespace where the pod is located.

    Returns:
        Analysis of the crash and suggested fixes.
    """
    core_v1 = _get_k8s_client()

    try:
        pod = core_v1.read_namespaced_pod(name=pod_name, namespace=namespace)

        result = [f"CrashLoop Analysis for {namespace}/{pod_name}:"]
        result.append("=" * 50)

        suggestions = []

        # Check container statuses
        if pod.status.container_statuses:
            for cs in pod.status.container_statuses:
                result.append(f"\nContainer: {cs.name}")
                result.append(f"  Restart Count: {cs.restart_count}")

                if cs.state.waiting and cs.state.waiting.reason == "CrashLoopBackOff":
                    result.append("  Status: CrashLoopBackOff")

                if cs.last_state.terminated:
                    term = cs.last_state.terminated
                    result.append(f"  Last Exit Code: {term.exit_code}")
                    result.append(f"  Last Termination Reason: {term.reason}")

                    # Analyze exit codes
                    if term.exit_code == 1:
                        suggestions.append("Exit code 1: Application error. Check the logs for stack traces or error messages.")
                    elif term.exit_code == 137:
                        suggestions.append("Exit code 137: OOMKilled - Container ran out of memory. Increase memory limits.")
                    elif term.exit_code == 139:
                        suggestions.append("Exit code 139: Segmentation fault. Check for bugs in native code.")
                    elif term.exit_code == 143:
                        suggestions.append("Exit code 143: SIGTERM received. Container was gracefully terminated.")
                    elif term.reason == "OOMKilled":
                        suggestions.append("OOMKilled: Container exceeded memory limits. Increase memory limits in the deployment.")

        # Check for common issues
        if pod.spec.containers:
            for container in pod.spec.containers:
                # No resource limits
                if not container.resources or not container.resources.limits:
                    suggestions.append(f"Container '{container.name}' has no resource limits. Consider adding them.")

                # Check for liveness probe issues
                if container.liveness_probe:
                    suggestions.append("Has liveness probe - verify probe configuration is appropriate.")

        # Try to get recent logs
        try:
            logs = core_v1.read_namespaced_pod_log(
                name=pod_name,
                namespace=namespace,
                tail_lines=20,
                previous=True
            )
            if logs:
                result.append("\nLast logs before crash:")
                result.append("-" * 30)
                result.append(logs[-1000:])  # Limit log size
        except ApiException:
            result.append("\nCould not retrieve previous logs.")

        result.append("\nSuggested Actions:")
        result.append("-" * 30)
        if suggestions:
            for i, suggestion in enumerate(suggestions, 1):
                result.append(f"{i}. {suggestion}")
        else:
            result.append("1. Check the application logs for error messages")
            result.append("2. Verify environment variables and configuration")
            result.append("3. Ensure required services/dependencies are available")

        return "\n".join(result)

    except ApiException as e:
        if e.status == 404:
            return f"Pod '{pod_name}' not found in namespace '{namespace}'."
        return f"Error analyzing pod: {e.reason}"


def check_pod_connectivity(pod_name: str, namespace: str = "default") -> str:
    """Check network-related information for a pod.

    Args:
        pod_name: Name of the pod to check.
        namespace: The namespace where the pod is located.

    Returns:
        Network connectivity information for the pod.
    """
    core_v1 = _get_k8s_client()

    try:
        pod = core_v1.read_namespaced_pod(name=pod_name, namespace=namespace)

        result = [f"Network Info for {namespace}/{pod_name}:"]

        result.append(f"Pod IP: {pod.status.pod_ip or 'Not assigned'}")
        result.append(f"Host IP: {pod.status.host_ip or 'Unknown'}")
        result.append(f"Node: {pod.spec.node_name or 'Not scheduled'}")

        # Check DNS policy
        result.append(f"DNS Policy: {pod.spec.dns_policy or 'ClusterFirst'}")

        # List services that might route to this pod
        services = core_v1.list_namespaced_service(namespace=namespace)
        matching_services = []

        pod_labels = pod.metadata.labels or {}

        for svc in services.items:
            if svc.spec.selector:
                # Check if service selector matches pod labels
                if all(pod_labels.get(k) == v for k, v in svc.spec.selector.items()):
                    ports = [f"{p.port}->{p.target_port}" for p in svc.spec.ports]
                    matching_services.append(f"  - {svc.metadata.name}: {', '.join(ports)}")

        if matching_services:
            result.append("\nServices routing to this pod:")
            result.extend(matching_services)
        else:
            result.append("\nNo services found routing to this pod.")

        return "\n".join(result)

    except ApiException as e:
        if e.status == 404:
            return f"Pod '{pod_name}' not found in namespace '{namespace}'."
        return f"Error checking connectivity: {e.reason}"
