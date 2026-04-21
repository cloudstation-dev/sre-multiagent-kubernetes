# SRE Coordinator Agent

Orchestrator agent that receives user requests and delegates to specialized agents via A2A protocol.

## Delegated Agents

- **Cluster Health Agent** - For monitoring and status checks
- **Troubleshooter Agent** - For debugging and error analysis

## A2A Communication

The coordinator discovers and communicates with other agents using the A2A (Agent-to-Agent) protocol:

1. Receives user request
2. Analyzes intent (monitoring vs debugging)
3. Calls appropriate agent via A2A
4. Returns unified response

## Environment Variables

- `CLUSTER_HEALTH_AGENT_URL` - URL to cluster health agent card
- `TROUBLESHOOTER_AGENT_URL` - URL to troubleshooter agent card
