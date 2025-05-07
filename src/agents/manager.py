# agents/manager.py
import asyncio
from typing import Dict, Any, List, Optional
import importlib
import logging
import yaml
import os

from agent_core.models.base import ModelInterface
from agent_core.config import load_config
from agents.base_agent import BaseAgent

class AgentManager:
    """Manages the lifecycle of all agents in the system."""
    
    def __init__(self, config_path: str = "config/agent_config.yaml"):
        self.logger = logging.getLogger("agent_manager")
        self.config = load_config(config_path)
        self.agents: Dict[str, BaseAgent] = {}
        self.model_instances: Dict[str, ModelInterface] = {}
        self.tasks = []
    
    async def initialize(self) -> None:
        """Initialize the agent manager."""
        self.logger.info("Initializing agent manager")
        
        # Initialize model interfaces
        await self._initialize_models()
        
        # Initialize agents
        await self._initialize_agents()
    
    async def _initialize_models(self) -> None:
        """Initialize model interfaces based on configuration."""
        model_config = self.config.get("models", {})
        default_provider = model_config.get("default", "ollama")
        
        for provider_name, provider_config in model_config.get("providers", {}).items():
            if not provider_config.get("enabled", True):
                continue
                
            # Import the appropriate model interface
            try:
                module = importlib.import_module(f"agent_core.models.{provider_name}")
                model_class = getattr(module, f"{provider_name.capitalize()}ModelInterface")
                
                # Initialize the model interface
                model_interface = model_class()
                await model_interface.initialize(provider_config)
                
                self.model_instances[provider_name] = model_interface
                self.logger.info(f"Initialized model interface for {provider_name}")
            except Exception as e:
                self.logger.error(f"Failed to initialize model interface for {provider_name}: {str(e)}", exc_info=True)
    
    async def _initialize_agents(self) -> None:
        """Initialize agents based on configuration."""
        agent_configs = self.config.get("agents", {})
        
        for agent_name, agent_config in agent_configs.items():
            if not agent_config.get("enabled", True):
                continue
                
            # Determine which model to use
            model_name = agent_config.get("model")
            model_provider = self._get_model_provider(model_name)
            
            if model_provider not in self.model_instances:
                self.logger.error(f"Model provider {model_provider} not initialized, skipping agent {agent_name}")
                continue
            
            # Import the appropriate agent class
            try:
                if agent_name == "code_documentation":
                    module = importlib.import_module("agents.code_doc.agent")
                    agent_class = getattr(module, "CodeDocAgent")
                elif agent_name == "research_analysis":
                    module = importlib.import_module("agents.research.agent")
                    agent_class = getattr(module, "ResearchAnalysisAgent")
                else:
                    # Try to dynamically import a custom agent
                    module = importlib.import_module(f"agents.{agent_name}.agent")
                    agent_class = getattr(module, f"{agent_name.title().replace('_', '')}Agent")
                
                # Initialize the agent
                agent = agent_class(agent_config, self.model_instances[model_provider])
                self.agents[agent_name] = agent
                self.logger.info(f"Initialized agent {agent_name}")
            except Exception as e:
                self.logger.error(f"Failed to initialize agent {agent_name}: {str(e)}", exc_info=True)
    
    def _get_model_provider(self, model_name: str) -> str:
        """Determine which provider owns a specific model."""
        model_config = self.config.get("models", {})
        default_provider = model_config.get("default", "ollama")
        
        # Check each provider for the model
        for provider_name, provider_config in model_config.get("providers", {}).items():
            models = provider_config.get("models", [])
            for model in models:
                name = model.get("name", model.get("repo_id", ""))
                if name == model_name:
                    return provider_name
        
        # Fall back to default provider
        return default_provider
    
    async def start_agent(self, agent_name: str) -> bool:
        """Start a specific agent."""
        if agent_name not in self.agents:
            self.logger.error(f"Agent {agent_name} not found")
            return False
            
        agent = self.agents[agent_name]
        
        # Start the agent in a separate task
        task = asyncio.create_task(agent.start())
        self.tasks.append(task)
        
        self.logger.info(f"Started agent {agent_name}")
        return True
    
    async def stop_agent(self, agent_name: str) -> bool:
        """Stop a specific agent."""
        if agent_name not in self.agents:
            self.logger.error(f"Agent {agent_name} not found")
            return False
            
        agent = self.agents[agent_name]
        await agent.stop()
        
        self.logger.info(f"Stopped agent {agent_name}")
        return True
    
    async def stop_all_agents(self) -> None:
        """Stop all running agents."""
        for agent_name, agent in self.agents.items():
            await agent.stop()
            
        # Wait for all tasks to complete
        for task in self.tasks:
            try:
                await task
            except asyncio.CancelledError:
                pass
            
        self.tasks = []
        self.logger.info("Stopped all agents")
    
    def get_agent_status(self, agent_name: str) -> Dict[str, Any]:
        """Get the status of a specific agent."""
        if agent_name not in self.agents:
            return {"agent": agent_name, "status": "not_found"}
            
        agent = self.agents[agent_name]
        
        return {
            "agent": agent_name,
            "status": "running" if agent.is_running else "stopped",
            "last_run": agent.last_run.isoformat() if agent.last_run else None
        }
    
    def list_agents(self) -> List[Dict[str, Any]]:
        """List all agents and their status."""
        return [self.get_agent_status(agent_name) for agent_name in self.agents]