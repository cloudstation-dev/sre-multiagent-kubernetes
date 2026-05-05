"""Cluster Health Crew - CrewAI implementation of cluster health monitoring."""

from typing import List

from crewai import Agent, Crew, Process, Task, LLM
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai.project import CrewBase, agent, crew, task

from .tools import get_pods, get_nodes, get_deployments, get_events, get_resource_usage

# Configure Gemini LLM for all agents
gemini_llm = LLM(
    model="gemini-2.5-flash-lite",
    temperature=0.7,
)


@CrewBase
class ClusterHealthCrew:
    """Cluster health monitoring crew using CrewAI."""

    agents: List[BaseAgent]
    tasks: List[Task]

    @agent
    def health_monitor(self) -> Agent:
        return Agent(
            config=self.agents_config["health_monitor"],  # type: ignore[index]
            verbose=True,
            llm=gemini_llm,
            tools=[get_pods, get_nodes, get_deployments, get_events, get_resource_usage],
        )

    @task
    def health_check_task(self) -> Task:
        return Task(
            config=self.tasks_config["health_check_task"]  # type: ignore[index]
        )

    @crew
    def crew(self) -> Crew:
        """Creates the cluster health monitoring crew."""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
            tracing=False,  # Disable interactive tracing for containerized environments
        )
