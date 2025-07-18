"""Server functionality for A2A Azure agents"""

import asyncio
import logging
from typing import Optional, Union
import uvicorn
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore

from .agent import Agent
from .host_agent import HostAgent
from .agent_executor import A2AAgentExecutor
from .host_agent_executor import HostAgentExecutor
from .agent_card import AgentCard

logger = logging.getLogger(__name__)


async def run_agent_server(
    agent: Union[Agent, HostAgent],
    agent_card: AgentCard,
    host: str = '0.0.0.0',
    port: int = 8000,
    log_level: str = "info"
):
    """
    Run an agent as a server using uvicorn.
    
    Args:
        agent: The Agent or HostAgent instance to serve
        agent_card: The AgentCard describing the agent
        host: The host to bind to (default: '0.0.0.0')
        port: The port to bind to (default: 8000)
        log_level: The logging level (default: "info")
    """
    logger.info(f"Starting {agent.name} Server on {host}:{port}")
    
    if hasattr(agent, 'initialize_plugins'):
        await agent.initialize_plugins()
    
    if isinstance(agent, HostAgent):
        executor = HostAgentExecutor(agent)
    else:
        executor = A2AAgentExecutor(agent)
    
    request_handler = DefaultRequestHandler(
        agent_executor=executor,
        task_store=InMemoryTaskStore(),
    )
    
    server = A2AStarletteApplication(
        agent_card=agent_card,
        http_handler=request_handler,
    )
    
    try:
        await uvicorn.Server(
            uvicorn.Config(
                server.build(),
                host=host,
                port=port,
                log_level=log_level
            )
        ).serve()
    finally:
        if hasattr(agent, 'cleanup'):
            await agent.cleanup()
            logger.info(f"{agent.name} cleaned up successfully.")


def start_agent_server(
    agent: Union[Agent, HostAgent],
    agent_card: AgentCard,
    host: str = '0.0.0.0',
    port: int = 8000,
    log_level: str = "info"
):
    """
    Start an agent server (synchronous wrapper).
    
    Args:
        agent: The Agent or HostAgent instance to serve
        agent_card: The AgentCard describing the agent
        host: The host to bind to (default: '0.0.0.0')
        port: The port to bind to (default: 8000)
        log_level: The logging level (default: "info")
    """
    asyncio.run(run_agent_server(agent, agent_card, host, port, log_level))


class AgentServer:
    """
    A class to manage agent servers with more control.
    """
    
    def __init__(
        self,
        agent: Union[Agent, HostAgent],
        agent_card: AgentCard,
        host: str = '0.0.0.0',
        port: int = 8000,
        log_level: str = "info"
    ):
        """
        Initialize the agent server.
        
        Args:
            agent: The Agent or HostAgent instance to serve
            agent_card: The AgentCard describing the agent
            host: The host to bind to
            port: The port to bind to
            log_level: The logging level
        """
        self.agent = agent
        self.agent_card = agent_card
        self.host = host
        self.port = port
        self.log_level = log_level
        self.server = None
    
    async def start(self):
        """Start the agent server asynchronously."""
        logger.info(f"Starting {self.agent.name} Server on {self.host}:{self.port}")
        
        if hasattr(self.agent, 'initialize_plugins'):
            await self.agent.initialize_plugins()
        
        if isinstance(self.agent, HostAgent):
            executor = HostAgentExecutor(self.agent)
        else:
            executor = A2AAgentExecutor(self.agent)
        
        request_handler = DefaultRequestHandler(
            agent_executor=executor,
            task_store=InMemoryTaskStore(),
        )
        
        app = A2AStarletteApplication(
            agent_card=self.agent_card,
            http_handler=request_handler,
        )
        
        config = uvicorn.Config(
            app.build(),
            host=self.host,
            port=self.port,
            log_level=self.log_level
        )
        self.server = uvicorn.Server(config)
        
        try:
            await self.server.serve()
        finally:
            await self.cleanup()
    
    async def cleanup(self):
        """Clean up agent resources."""
        if hasattr(self.agent, 'cleanup'):
            await self.agent.cleanup()
            logger.info(f"{self.agent.name} cleaned up successfully.")
    
    def run(self):
        """Run the server synchronously."""
        asyncio.run(self.start()) 