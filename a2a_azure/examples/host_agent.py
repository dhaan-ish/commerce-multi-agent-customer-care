"""Example of running A2A Azure agents as servers"""

import asyncio
import logging
import os
from a2a_azure import (
    Agent, AgentSkill, AgentCard, AgentCapabilities,AgentServer, run_agent_server, HostAgent
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_host_agent_server():
    """Example of running a host agent as a server"""
    agent_endpoints = [
        {
            'url': 'http://localhost:5560',
            'name': 'CSV Agent',
            'function_name': 'analyze_csv_data',
            'description': 'Analyzes CSV files and provides data insights'
        },
        {
            'url': 'http://localhost:5561',
            'name': 'SQL Agent',
            'function_name': 'analyze_sql_data',
            'description': 'Executes SQL queries and provides data insights'
        }
    ]
    orchestration_skill = AgentSkill(
        id='data_orchestration',
        name='Data Orchestration',
        description='Orchestrates data analysis tasks across CSV and SQL agents.',
        tags=['orchestration', 'data', 'csv', 'sql'],
        examples=[
            'Analyze the CSV file and compare it with database records.',
            'Load customer data and cross-reference with SQL tables.',
            'Generate a report combining CSV and database insights.',
        ],
    )
    host_agent_card = AgentCard(
        name='Data Orchestrator',
        description='An orchestration agent that coordinates CSV and SQL analysis agents.',
        capabilities=AgentCapabilities(streaming=True),
        url='http://localhost:5570/',
        version='1.0.0',
        defaultInputModes=['text'],
        defaultOutputModes=['text'],
        skills=[orchestration_skill],
        supportsAuthenticatedExtendedCard=False,
    )
    host_agent = HostAgent(
        name="Data Orchestrator",
        description="Orchestrates data analysis across multiple specialized agents",
        agent_endpoints=agent_endpoints
    )
    await run_agent_server(
        agent=host_agent,
        agent_card=host_agent_card,
        host='0.0.0.0',
        port=5570
    )


if __name__ == '__main__':
    import sys
    asyncio.run(run_host_agent_server())