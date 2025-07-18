# a2a_azure

A Python package for building and orchestrating AI agents with Azure OpenAI and MCP (Model Context Protocol) integration. This package provides a flexible framework for creating individual agents with specific capabilities and host agents that can orchestrate multiple specialized agents.

## Features

- 🤖 **Agent Creation**: Build AI agents powered by Azure OpenAI with custom personalities and capabilities
- 🔌 **MCP Integration**: Connect agents to multiple MCP (Model Context Protocol) servers for extended functionality
- 🎯 **Dynamic Tool Generation**: Automatically generate unique tools for each agent endpoint in host agents
- 🔄 **Agent Orchestration**: Create host agents that coordinate multiple specialized agents
- 🚀 **Easy Server Deployment**: Built-in server functionality using uvicorn and A2A protocol
- 📝 **Context Management**: Maintain conversation history across multiple interactions

## Installation

```bash
pip install a2a_azure
```

## Requirements

- Python 3.8+
- Azure OpenAI API credentials
- Required packages (automatically installed):
  - `semantic-kernel`
  - `a2a`
  - `httpx`
  - `uvicorn`
  - `python-dotenv`

## Environment Setup

Create a `.env` file with your Azure OpenAI credentials. The environment variables must be named exactly as shown below:

```env
API_KEY=your_azure_openai_api_key
END_POINT=your_azure_openai_endpoint
DEPLOYMENT=your_deployment_name
API_VERSION=your_api_version
```

**Note**: The environment variable names are case-sensitive and must match exactly as shown above.

Example with actual values:
```env
API_KEY=1234567890abcdef1234567890abcdef
END_POINT=https://your-resource.openai.azure.com/
DEPLOYMENT=gpt-4
API_VERSION=2024-02-15-preview
```

## Quick Start

### Creating a Simple Agent

```python
from a2a_azure import Agent, AgentCard, AgentCapabilities, AgentSkill, start_agent_server

# Create an agent
agent = Agent(
    name="Weather Assistant",
    description="An agent that provides weather information",
    mcp_sse_urls=[],  # Add MCP server URLs if needed
    system_message="You are a helpful weather assistant."
)

# Define agent capabilities
weather_skill = AgentSkill(
    id='weather_info',
    name='Weather Information',
    description='Provides current weather data and forecasts',
    tags=['weather', 'forecast', 'temperature'],
    examples=[
        'What\'s the weather like today?',
        'Will it rain tomorrow?',
        'Current temperature in New York?'
    ]
)

# Create agent card
agent_card = AgentCard(
    name='Weather_Assistant',
    description='A helpful weather information agent',
    capabilities=AgentCapabilities(streaming=True),
    url='http://localhost:8080/',
    version='1.0.0',
    defaultInputModes=['text'],
    defaultOutputModes=['text'],
    skills=[weather_skill],
    supportsAuthenticatedExtendedCard=False
)

# Start the server
start_agent_server(agent, agent_card, port=8080)
```

### Creating a Host Agent

Host agents can orchestrate multiple specialized agents:

```python
from a2a_azure import HostAgent, run_agent_server
import asyncio

# Define endpoints for specialized agents
agent_endpoints = [
    {
        'url': 'http://localhost:5001',
        'name': 'Data Analyzer',
        'function_name': 'analyze_data',
        'description': 'Performs data analysis and visualization'
    },
    {
        'url': 'http://localhost:5002',
        'name': 'Report Generator',
        'function_name': 'generate_report',
        'description': 'Creates comprehensive reports from analyzed data'
    }
]

# Create host agent
host_agent = HostAgent(
    name="Data Orchestrator",
    description="Orchestrates data analysis and reporting tasks",
    agent_endpoints=agent_endpoints
)

# Create host agent card
host_card = AgentCard(
    name='Data_Orchestrator',
    description='Orchestrates multiple data processing agents',
    capabilities=AgentCapabilities(streaming=True),
    url='http://localhost:6000/',
    version='1.0.0',
    defaultInputModes=['text'],
    defaultOutputModes=['text'],
    skills=[...],  # Add appropriate skills
    supportsAuthenticatedExtendedCard=False
)

# Run the host agent server
async def main():
    await run_agent_server(host_agent, host_card, port=6000)

asyncio.run(main())
```

### Agent with MCP Integration

Connect your agent to MCP servers for extended capabilities:

```python
# Create an agent with MCP connections
agent = Agent(
    name="CSV Analyzer",
    description="Analyzes CSV files using MCP tools",
    mcp_sse_urls=[
        "http://localhost:8000/sse",  # CSV analysis MCP server
        "http://localhost:8001/sse"   # Additional tools server
    ],
    system_message="You are a CSV analysis expert with access to specialized tools."
)
```

## Advanced Usage

### Dynamic Agent Addition

Add new agents to a host dynamically:

```python
host_agent.add_agent_endpoint(
    url='http://localhost:5003',
    name='Database Agent',
    function_name='query_database',
    description='Executes database queries and returns results'
)
```

### Custom System Messages

Provide custom instructions to your agents:

```python
agent = Agent(
    name="Custom Assistant",
    description="A customized assistant",
    system_message="""You are an expert assistant with the following guidelines:
    1. Always be concise and clear
    2. Provide examples when explaining concepts
    3. Ask for clarification when requests are ambiguous
    """
)
```

### Using AgentServer Class

For more control over the server lifecycle:

```python
from a2a_azure import AgentServer

server = AgentServer(
    agent=agent,
    agent_card=agent_card,
    host='0.0.0.0',
    port=8080,
    log_level='info'
)

# Run asynchronously
await server.start()

# Or run synchronously
server.run()
```

## API Reference

### Agent Class

```python
Agent(
    name: str,
    description: str,
    mcp_sse_urls: List[str] = None,
    system_message: str = None
)
```

**Parameters:**
- `name`: The agent's display name
- `description`: Description of the agent's purpose
- `mcp_sse_urls`: List of MCP SSE server URLs to connect to
- `system_message`: Custom system prompt for the agent

**Methods:**
- `async process_request(user_input: str, context_id: str) -> str`: Process a user request
- `async initialize_plugins()`: Initialize MCP connections
- `async cleanup()`: Clean up resources

### HostAgent Class

```python
HostAgent(
    name: str = "Host Agent",
    description: str = "An orchestration agent...",
    agent_endpoints: List[Dict[str, str]] = None,
    system_message: str = None
)
```

**Parameters:**
- `name`: The host agent's name
- `description`: Description of the host agent
- `agent_endpoints`: List of agent endpoint configurations
- `system_message`: Custom system prompt

**Agent Endpoint Format:**
```python
{
    'url': 'http://localhost:5000',
    'name': 'Agent Name',
    'function_name': 'unique_function_name',  # Required, must be unique
    'description': 'What this agent does'
}
```

### Server Functions

```python
# Async function for running in async context
await run_agent_server(
    agent: Union[Agent, HostAgent],
    agent_card: AgentCard,
    host: str = '0.0.0.0',
    port: int = 8000,
    log_level: str = 'info'
)

# Sync wrapper for simple usage
start_agent_server(
    agent: Union[Agent, HostAgent],
    agent_card: AgentCard,
    host: str = '0.0.0.0',
    port: int = 8000,
    log_level: str = 'info'
)
```

## Best Practices

1. **Unique Function Names**: Always provide unique `function_name` values for each agent endpoint in host agents
2. **Resource Cleanup**: Always call `cleanup()` on agents when shutting down to properly close MCP connections
3. **Error Handling**: Implement proper error handling for agent communication failures
4. **Context Management**: Use consistent context IDs to maintain conversation history
5. **MCP Servers**: Ensure MCP servers are running before connecting agents to them

## Examples

Check the [examples](examples/) directory for more detailed examples:
- Basic agent creation
- Host agent orchestration
- MCP integration patterns
- Multi-agent systems

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Built on top of [Semantic Kernel](https://github.com/microsoft/semantic-kernel)
- Uses the [A2A Protocol](https://github.com/a2aproject/) for agent communication
- Integrates with [MCP](https://modelcontextprotocol.com/) for extended functionality 