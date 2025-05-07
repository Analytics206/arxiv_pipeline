# Base agent class
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import asyncio
import logging
from datetime import datetime

class BaseAgent(ABC):
    """Base class for all agents."""
    
    def __init__(self, name: str, config: Dict[str, Any], model_interface: ModelInterface):
        self.name = name
        self.config = config
        self.model = model_interface
        self.logger = logging.getLogger(f"agent.{name}")
        self.is_running = False
        self.last_run = None
        
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the agent."""
        pass
    
    @abstractmethod
    async def run_cycle(self) -> Dict[str, Any]:
        """Run a single cycle of the agent's operation."""
        pass
    
    async def start(self) -> None:
        """Start the agent."""
        if self.is_running:
            self.logger.warning(f"Agent {self.name} is already running")
            return
            
        self.logger.info(f"Starting agent {self.name}")
        self.is_running = True
        await self.initialize()
        
        try:
            while self.is_running:
                start_time = datetime.now()
                results = await self.run_cycle()
                end_time = datetime.now()
                
                self.logger.info(f"Agent {self.name} completed cycle in {end_time - start_time}")
                self.last_run = end_time
                
                if self.config.get("update_frequency") == "on_change":
                    # Wait for the next event trigger
                    await asyncio.sleep(1)
                else:
                    # Sleep for the configured interval
                    interval = self._get_interval_seconds()
                    await asyncio.sleep(interval)
        except Exception as e:
            self.logger.error(f"Agent {self.name} encountered an error: {str(e)}", exc_info=True)
            self.is_running = False
    
    async def stop(self) -> None:
        """Stop the agent."""
        self.logger.info(f"Stopping agent {self.name}")
        self.is_running = False
    
    def _get_interval_seconds(self) -> int:
        """Get the interval in seconds based on configuration."""
        frequency = self.config.get("update_frequency", "hourly")
        if frequency == "hourly":
            return 3600
        elif frequency == "daily":
            return 86400
        else:
            return 3600  # Default to hourly