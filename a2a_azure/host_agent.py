"""Host Agent class for orchestrating multiple A2A Azure agents"""

import asyncio
import logging
import os
import re
from typing import List, Dict, Any, Type
from uuid import uuid4
from dotenv import load_dotenv

from semantic_kernel.agents.chat_completion.chat_completion_agent import ChatCompletionAgent, ChatHistoryAgentThread
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.contents.chat_message_content import ChatMessageContent
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.functions.kernel_function_decorator import kernel_function
from a2a.client import A2ACardResolver, A2AClient
from a2a.types import MessageSendParams, SendMessageRequest
import httpx

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_agent_tool_class(agent_name: str, agent_url: str, agent_description: str, function_name: str) -> Type:
    """
    Dynamically create a tool class for a specific agent.
    
    Args:
        agent_name: The name of the agent
        agent_url: The URL of the agent
        agent_description: Description of what the agent does
        function_name: The unique function name for this agent
        
    Returns:
        A dynamically created tool class
    """
    class_name = re.sub(r'[^0-9A-Za-z]', '', agent_name) + 'Tool'
    
    class DynamicAgentTool:
        def __init__(self):
            self.agent_url = agent_url
            self.agent_name = agent_name
            self.agent_description = agent_description
            self.function_name = function_name
        
        async def _send_to_agent(self, user_input: str) -> str:
            """
            Send a request to the remote agent.
            
            Args:
                user_input: The input to send to the agent
                
            Returns:
                The response from the agent
            """
            async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as httpx_client:
                try:
                    resolver = A2ACardResolver(httpx_client=httpx_client, base_url=self.agent_url)
                    agent_card = await resolver.get_agent_card()
                    
                    client = A2AClient(httpx_client=httpx_client, agent_card=agent_card)
                    
                    request = SendMessageRequest(
                        id=str(uuid4()),
                        params=MessageSendParams(
                            message={
                                "messageId": uuid4().hex,
                                "role": "user",
                                "parts": [{"text": user_input}],
                                "contextId": str(uuid4()),
                            }
                        )
                    )
                    
                    logger.info(f"Sending request to {self.agent_name} agent: {user_input}")
                    response = await client.send_message(request)
                    result = response.model_dump(mode='json', exclude_none=True)
                    logger.info(f"{self.agent_name} agent response: {result}")
                    
                    if "error" in result:
                        error_message = result["error"].get("message", "Unknown error occurred")
                        logger.error(f"{self.agent_name} agent returned error: {error_message}")
                        return f"Error from {self.agent_name} agent: {error_message}"
                    
                    if "result" in result and "parts" in result["result"] and len(result["result"]["parts"]) > 0:
                        return result["result"]["parts"][0]["text"]
                    else:
                        logger.error(f"Unexpected response format from {self.agent_name} agent: {result}")
                        return f"Error: Unexpected response format from {self.agent_name} agent"
                        
                except httpx.ReadTimeout:
                    logger.error(f"Timeout waiting for {self.agent_name} agent response.")
                    return f"Error: The {self.agent_name} agent is taking longer than expected. Please try again."
                except Exception as e:
                    logger.error(f"Error connecting to {self.agent_name} agent: {e}")
                    return f"Error connecting to {self.agent_name} agent: {str(e)}"
    
    DynamicAgentTool.__name__ = class_name
    DynamicAgentTool.__qualname__ = class_name
    
    decorated_function = kernel_function(
        description=f"Send a request to {agent_name}: {agent_description}",
        name=function_name
    )(DynamicAgentTool._send_to_agent)
    
    setattr(DynamicAgentTool, function_name, decorated_function)
    
    return DynamicAgentTool


class HostAgent:
    """
    Host Agent that orchestrates multiple remote agents.
    
    Attributes:
        name: The host agent's name
        description: The host agent's description
        agent_endpoints: List of dictionaries containing agent information
        system_message: The system message for the host agent
    """
    
    def __init__(
        self,
        name: str = "Host Agent",
        description: str = "An orchestration agent that coordinates multiple specialized agents",
        agent_endpoints: List[Dict[str, str]] = None,
        system_message: str = None
    ):
        """
        Initialize the Host Agent.
        
        Args:
            name: The host agent's name
            description: The host agent's description
            agent_endpoints: List of dicts with 'url', 'name', 'description', and 'function_name' for each agent
            system_message: The system message for the host agent
        """
        logger.info(f"Initializing {name}.")
        
        self.name = name
        self.description = description
        self.agent_endpoints = agent_endpoints or []
        
        for endpoint in self.agent_endpoints:
            if 'function_name' not in endpoint:
                raise ValueError(f"Agent endpoint for {endpoint.get('name', 'Unknown')} must include 'function_name'")
        
        self.agent_id = re.sub(r'[^0-9A-Za-z_-]', '_', name)
        
        self.agent_tools = []
        for endpoint in self.agent_endpoints:
            tool_class = create_agent_tool_class(
                agent_name=endpoint['name'],
                agent_url=endpoint['url'],
                agent_description=endpoint.get('description', ''),
                function_name=endpoint['function_name']
            )
            tool_instance = tool_class()
            self.agent_tools.append(tool_instance)
            logger.info(f"Created {tool_class.__name__} with function '{endpoint['function_name']}'")
        
        if system_message is None:
            agent_descriptions = "\n".join([
                f"- {endpoint['name']} (use function '{endpoint['function_name']}'): {endpoint.get('description', 'No description provided')}"
                for endpoint in self.agent_endpoints
            ])
            system_message = (
                f"You are {name}. {description}\n\n"
                f"You have access to the following specialized agents:\n{agent_descriptions}\n\n"
                f"Use these agents to help answer user requests by delegating tasks to the appropriate agent."
            )
        
        self.system_message = system_message
        
        self.chat_agent = ChatCompletionAgent(
            service=AzureChatCompletion(
                api_key=os.getenv("API_KEY"),
                endpoint=os.getenv("END_POINT"),
                deployment_name=os.getenv("DEPLOYMENT"),
                api_version=os.getenv("API_VERSION"),
            ),
            name=self.agent_id,
            plugins=self.agent_tools
        )
        
        self.history_store: Dict[str, ChatHistory] = {}
        
        logger.info(f"{name} initialized successfully with {len(self.agent_tools)} connected agents.")
    
    async def orchestrate(self, user_input: str, context_id: str) -> str:
        """
        Orchestrate the request across multiple agents.
        
        Args:
            user_input: The user's request
            context_id: The context ID for the request
            
        Returns:
            The orchestrated response
        """
        logger.info(f"Received orchestration request: {user_input} with context ID: {context_id}")
        
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
        
        logger.info(f"{self.name} response: {response.content.content}")
        
        return response.content.content
    
    def add_agent_endpoint(self, url: str, name: str, function_name: str, description: str = ""):
        """
        Add a new agent endpoint dynamically.
        
        Args:
            url: The URL of the agent
            name: The name of the agent
            function_name: The unique function name for this agent
            description: Description of what the agent does
        """
        endpoint = {'url': url, 'name': name, 'function_name': function_name, 'description': description}
        self.agent_endpoints.append(endpoint)
        
        tool_class = create_agent_tool_class(
            agent_name=name,
            agent_url=url,
            agent_description=description,
            function_name=function_name
        )
        
        tool_instance = tool_class()
        self.agent_tools.append(tool_instance)
        
        self.chat_agent.plugins = self.agent_tools
        
        logger.info(f"Added new agent endpoint: {name} at {url} with function '{function_name}'") 