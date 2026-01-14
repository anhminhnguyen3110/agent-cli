"""Middleware for the DeepAgent."""

from agentscli.middleware.filesystem import FilesystemMiddleware
from agentscli.middleware.memory import MemoryMiddleware
from agentscli.middleware.skills import SkillsMiddleware
from agentscli.middleware.subagents import CompiledSubAgent, SubAgent, SubAgentMiddleware

__all__ = [
    "CompiledSubAgent",
    "FilesystemMiddleware",
    "MemoryMiddleware",
    "SkillsMiddleware",
    "SubAgent",
    "SubAgentMiddleware",
]
