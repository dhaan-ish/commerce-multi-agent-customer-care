"""Base Agent class for A2A Azure agents"""

import asyncio
import logging
import os
import re
from typing import List, Optional, Dict
from uuid import uuid4
from dotenv import load_dotenv

from semantic_kernel.agents.chat_completion.chat_completion_agent import ChatCompletionAgent, ChatHistoryAgentThread
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.contents.chat_message_content import ChatMessageContent
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.connectors.mcp import MCPSsePlugin

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Agent:
    """
    Base Agent class for creating agents with MCP integration.
    
    Attributes:
        name: The agent's name
        description: The agent's description
        mcp_sse_urls: List of MCP SSE URLs for plugin connections
        system_message: The system message for the agent
    """
    
    def __init__(
        self,
        name: str,
        description: str,
        mcp_sse_urls: List[str] = None,
        system_message: str = None
    ):
        """
        Initialize the Agent.
        
        Args:
            name: The agent's name
            description: The agent's description
            mcp_sse_urls: List of MCP SSE URLs for plugin connections
            system_message: The system message for the agent
        """
        logger.info(f"Initializing {name} Agent.")
        
        self.name = name
        self.description = description
        self.mcp_sse_urls = mcp_sse_urls or []
        self.system_message = system_message or f"You are {name}. {description}"
        
        self.agent_id = re.sub(r'[^0-9A-Za-z_-]', '_', name)
        
        self.mcp_plugins = []
        self._plugins_initialized = False
        
        self.chat_agent = None
        self._service = AzureChatCompletion(
            api_key=os.getenv("API_KEY"),
            endpoint=os.getenv("END_POINT"),
            deployment_name=os.getenv("DEPLOYMENT"),
            api_version=os.getenv("API_VERSION"),
        )
        
        self.history_store: Dict[str, ChatHistory] = {}
        
        logger.info(f"{name} Agent initialized successfully.")
    
    async def initialize_plugins(self):
        """Initialize MCP plugins from the provided URLs"""
        if self._plugins_initialized:
            return
            
        for url in self.mcp_sse_urls:
            try:
                plugin = MCPSsePlugin(
                    name=f"RemoteTools_{self.agent_id}_{len(self.mcp_plugins)}",
                    url=url,
                )
                await plugin.__aenter__()
                self.mcp_plugins.append(plugin)
                logger.info(f"MCP Plugin initialized successfully for {self.name}. Connected to: {url}")
            except Exception as e:
                logger.warning(f"Failed to initialize MCP plugin for {url}: {e}")
        
        self.chat_agent = ChatCompletionAgent(
            service=self._service,
            name=self.agent_id,
            plugins=self.mcp_plugins if self.mcp_plugins else []
        )
        
        self._plugins_initialized = True
    
    async def process_request(self, user_input: str, context_id: str) -> str:
        """
        Process a user request.
        
        Args:
            user_input: The user's input
            context_id: The context ID for the request
            
        Returns:
            The agent's response
        """
        await self.initialize_plugins()
        
        if not self.chat_agent:
            raise RuntimeError("Chat agent not initialized. Call initialize_plugins() first.")
        
        logger.info(f"Received request for {self.name}: {user_input} with context ID: {context_id}")
        
        if not user_input:
            logger.error("User input is empty.")
            raise ValueError("User input cannot be empty.")
        
        chat_history = self.history_store.get(context_id)
        if chat_history is None:
            chat_history = ChatHistory(
                messages=[],
                system_message=self.system_message
            )
            self.history_store[context_id] = chat_history
            logger.info(f"Created new ChatHistory for context ID: {context_id}")
        
        chat_history.messages.append(ChatMessageContent(role="user", content=user_input))
        
        thread = ChatHistoryAgentThread(chat_history=chat_history, thread_id=str(uuid4()))
        response = await self.chat_agent.get_response(message=user_input, thread=thread)
        
        chat_history.messages.append(ChatMessageContent(role="assistant", content=response.content.content))
        
        logger.info(f"{self.name} agent response: {response.content.content}")
        
        return response.content.content
    
    async def cleanup(self):
        """Clean up MCP plugins"""
        for plugin in self.mcp_plugins:
            try:
                await plugin.__aexit__(None, None, None)
                logger.info(f"MCP Plugin cleaned up for {self.name}.")
            except Exception as e:
                logger.error(f"Error cleaning up MCP plugin: {e}") 