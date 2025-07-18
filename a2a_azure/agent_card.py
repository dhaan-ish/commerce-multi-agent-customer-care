"""Agent Card and Skill definitions for A2A Azure agents"""

from typing import List
from dataclasses import dataclass, field
from a2a.types import AgentCard, AgentCapabilities, AgentSkill as A2AAgentSkill


__all__ = ['AgentCard', 'AgentCapabilities', 'AgentSkill']


AgentSkill = A2AAgentSkill 