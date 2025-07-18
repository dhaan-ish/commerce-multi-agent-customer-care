"""Example of running A2A Azure agents as servers"""

import asyncio
import logging
import os
from a2a_azure import (
    Agent, AgentSkill, AgentCard, AgentCapabilities,AgentServer, run_agent_server, HostAgent
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_sql_agent_server():
    """Example of running a SQL agent as a server"""
    sql_analysis_skill = AgentSkill(
        id='sql_analysis',
        name='SQL Analysis',
        description='Loads SQL files and provides insights about the data.',
        tags=['sql', 'data', 'analysis', 'insights'],
        examples=[
            'Analyze the customer data in my SQL file.',
            'What are the column names and data types in this SQL?',
        ],
    )

    sql_agent_card = AgentCard(
        name='SQL_Analyzer_Agent',
        description='An agent that helps users load and analyze SQL files using MCP tools.',
        capabilities=AgentCapabilities(streaming=True),
        url='http://localhost:5561/',
        version='1.0.0',
        defaultInputModes=['text'],
        defaultOutputModes=['text'],
        skills=[sql_analysis_skill],
        supportsAuthenticatedExtendedCard=False,
    )

    sql_agent = Agent(
        name="SQL Analyzer",
        description="An agent specialized in analyzing SQL files",
        mcp_sse_urls=["http://localhost:8001/sse"],
        system_message="You are a SQL analysis expert. Use the available tools to analyze SQL data."
    )
    
    logger.info("Starting SQL Agent Server on port 5561.")
    
    server = AgentServer(
        agent=sql_agent,
        agent_card=sql_agent_card,
        host='0.0.0.0',
        port=5561
    )
    
    await server.start()

if __name__ == '__main__':
    import sys
    asyncio.run(run_sql_agent_server())