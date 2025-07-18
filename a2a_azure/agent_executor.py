"""Agent Executor for A2A Azure agents"""

import logging
from typing import Optional
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.utils import new_agent_text_message, new_task
from .agent import Agent

logger = logging.getLogger(__name__)



class A2AAgentExecutor(AgentExecutor):
    """Executor for A2A Azure Agent."""

    def __init__(self, agent: Agent):
        """
        Initialize the agent executor.
        
        Args:
            agent: An instance of the Agent class
        """
        logger.info(f"Initializing A2AAgentExecutor for {agent.name}.")
        self.agent = agent
        logger.info(f"A2AAgentExecutor initialized successfully for {agent.name}.")

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """
        Execute the agent request.
        
        Args:
            context: The request context
            event_queue: The event queue for responses
        """
        user_input = context.get_user_input()
        task = context.current_task
        context_id = context.context_id
        
        if not task:
            task = new_task(context.message)
            await event_queue.enqueue_event(task)

        logger.info(f"Executing {self.agent.name} with user input: {user_input} with task: {task.id} and context ID: {context_id}")
        try:
            result = await self.agent.process_request(user_input, context_id)
            await event_queue.enqueue_event(new_agent_text_message(result))
            logger.info(f"{self.agent.name} executed successfully.")
        except Exception as e:
            logger.error(f"Error during {self.agent.name} execution: {e}")
            await event_queue.enqueue_event(new_agent_text_message(f"Error: {str(e)}"))

    async def cancel(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        """Cancel operation (not supported)."""
        logger.warning("Cancel operation requested but not supported.")
        raise Exception('Cancel operation not supported.') 