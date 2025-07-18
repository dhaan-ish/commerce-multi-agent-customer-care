"""Example of running A2A Azure agents as servers"""

import asyncio
import logging
from a2a_azure import (
    Agent, AgentSkill, AgentCard, AgentCapabilities,AgentServer, run_agent_server, HostAgent
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def run_csv_agent_server():
    """Example of running a CSV agent as a server"""
    
    csv_analysis_skill = AgentSkill(
        id='csv_analysis',
        name='CSV Analysis',
        description='Loads CSV files and provides insights about the data.',
        tags=['csv', 'data', 'analysis', 'insights'],
        examples=[
            'Load the sales.csv file and give me a summary.',
            'Analyze the customer data in my CSV file.',
            'What are the column names and data types in this CSV?',
        ],
    )
    
    csv_agent_card = AgentCard(
        name='CSV_Analyzer_Agent',
        description='An agent that helps users load and analyze CSV files using MCP tools.',
        capabilities=AgentCapabilities(streaming=True),
        url='http://localhost:5560/',
        version='1.0.0',
        defaultInputModes=['text'],
        defaultOutputModes=['text'],
        skills=[csv_analysis_skill],
        supportsAuthenticatedExtendedCard=False,
    )
    
    csv_agent = Agent(
        name="CSV Analyzer",
        description="An agent specialized in analyzing CSV files",
        mcp_sse_urls=["http://localhost:8000/sse"],
        system_message="You are a CSV analysis expert. Use the available tools to analyze CSV data."
    )
    
    logger.info("Starting CSV Agent Server on port 5560.")
    
    server = AgentServer(
        agent=csv_agent,
        agent_card=csv_agent_card,
        host='0.0.0.0',
        port=5560
    )
    
    await server.start()

if __name__ == '__main__':
    import sys
    asyncio.run(run_csv_agent_server())