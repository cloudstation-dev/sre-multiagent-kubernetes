"""SRE Coordinator Agent - Routes requests to specialized agents via A2A."""

import os
from typing import Optional

import httpx
from google.adk import Agent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.tools.base_tool import BaseTool

from kagent.adk._remote_a2a_tool import KAgentRemoteA2AToolset, KAgentRemoteA2ATool

# Agent URLs - these are the K8s service URLs for the other agents
# Format: http://<service-name>.<namespace>:<port>
CLUSTER_HEALTH_URL = os.getenv(
    "CLUSTER_HEALTH_AGENT_URL",
    "http://cluster-health-agent.kagent:8080/.well-known/agent-card.json"
)
TROUBLESHOOTER_URL = os.getenv(
    "TROUBLESHOOTER_AGENT_URL",
    "http://troubleshooter-agent.kagent:8080/.well-known/agent-card.json"
)


class ResettableA2AToolset(KAgentRemoteA2AToolset):
    """A2A Toolset that recreates the httpx client if it was closed."""

    def __init__(self, *, name: str, description: str, agent_card_url: str):
        self._toolset_name = name
        self._description = description
        self._agent_card_url = agent_card_url
        self._my_httpx_client: Optional[httpx.AsyncClient] = None
        self._my_tool: Optional[KAgentRemoteA2ATool] = None
        # Initialize parent with a temporary client - we'll recreate as needed
        temp_client = httpx.AsyncClient(timeout=60.0)
        super().__init__(
            name=name,
            description=description,
            agent_card_url=agent_card_url,
            httpx_client=temp_client,
        )
        self._my_httpx_client = temp_client
        self._my_tool = self._tool  # Save reference to the tool created by parent

    def _ensure_client(self) -> None:
        """Recreate the httpx client if it was closed."""
        if self._my_httpx_client is None or self._my_httpx_client.is_closed:
            self._my_httpx_client = httpx.AsyncClient(timeout=60.0)
            # Recreate the tool with the new client
            self._my_tool = KAgentRemoteA2ATool(
                name=self._toolset_name,
                description=self._description,
                agent_card_url=self._agent_card_url,
                httpx_client=self._my_httpx_client,
            )
            # Update parent references
            self._httpx_client = self._my_httpx_client
            self._tool = self._my_tool

    async def get_tools(self, readonly_context: Optional[ReadonlyContext] = None) -> list[BaseTool]:
        self._ensure_client()
        return [self._my_tool]

    async def close(self) -> None:
        """Close the httpx client - it will be recreated on next use."""
        if self._my_httpx_client is not None:
            try:
                await self._my_httpx_client.aclose()
            except Exception:
                pass
            self._my_httpx_client = None


def create_coordinator_agent() -> Agent:
    """Factory function to create the coordinator agent with A2A toolsets."""
    cluster_health_toolset = ResettableA2AToolset(
        name="ask_cluster_health_agent",
        description=(
            "Delegates to the Cluster Health Agent for monitoring tasks. "
            "Use this for: checking pod status, node health, deployments, "
            "events, and resource usage in the Kubernetes cluster. "
            "Example: 'Check if all pods are running in the production namespace'"
        ),
        agent_card_url=CLUSTER_HEALTH_URL,
    )

    troubleshooter_toolset = ResettableA2AToolset(
        name="ask_troubleshooter_agent",
        description=(
            "Delegates to the Troubleshooter Agent for debugging issues. "
            "Use this for: analyzing pod failures, CrashLoopBackOff, viewing logs, "
            "diagnosing errors, and getting fix suggestions. "
            "Example: 'Why is pod X crashing?' or 'Show me the logs for pod Y'"
        ),
        agent_card_url=TROUBLESHOOTER_URL,
    )

    return Agent(
        model="gemini-2.5-flash-lite",
        name="sre_coordinator_agent",
        description=(
            "SRE Coordinator that routes requests to specialized Kubernetes agents. "
            "Can delegate to Cluster Health Agent for monitoring and "
            "Troubleshooter Agent for debugging issues."
        ),
        instruction="""
You are an SRE Coordinator Agent. Your role is to understand user requests and
delegate them to the most appropriate specialized agent.

You have access to two specialized agents via A2A (Agent-to-Agent) protocol:

1. **Cluster Health Agent** (ask_cluster_health_agent):
   - Monitors cluster state
   - Checks pod, node, and deployment status
   - Views events and resource usage
   - Use for questions like:
     * "What's the status of pods in namespace X?"
     * "Are all nodes healthy?"
     * "Show me recent events"
     * "What deployments are running?"

2. **Troubleshooter Agent** (ask_troubleshooter_agent):
   - Debugs issues and failures
   - Analyzes logs and CrashLoopBackOff
   - Suggests fixes
   - Use for questions like:
     * "Why is pod X failing?"
     * "Show me the logs for pod Y"
     * "What's causing the OOMKilled error?"
     * "Help me fix the CrashLoopBackOff"

**Decision Logic:**
- If the user asks about STATUS, HEALTH, or general MONITORING -> Cluster Health Agent
- If the user asks about ERRORS, FAILURES, LOGS, or DEBUGGING -> Troubleshooter Agent
- If unsure, start with Cluster Health to understand the current state

**Response Guidelines:**
1. First, acknowledge what the user is asking for
2. Explain which agent you're delegating to and why
3. Call the appropriate agent tool with a clear request
4. Summarize the response for the user
5. Suggest next steps if appropriate

**Example Interaction:**
User: "Why is my app not working?"
You: "I'll help investigate. Let me first check the cluster status, then look for any
failing pods. I'm delegating to the Cluster Health Agent to get an overview..."

Remember: You are the user's single point of contact. Make the multi-agent
coordination seamless and provide a unified, helpful response.
""",
        tools=[
            cluster_health_toolset,
            troubleshooter_toolset,
        ],
    )


# Export for kagent-adk discovery
# Note: Each call creates fresh httpx clients to avoid closed client issues
root_agent = create_coordinator_agent()
