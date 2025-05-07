# Ollama integration# agent_core/models/ollama.py
import aiohttp
import json
from typing import Dict, Any, List, Optional
import logging

from agent_core.models.base import ModelInterface

class OllamaModelInterface(ModelInterface):
    """Interface for interacting with Ollama models."""
    
    def __init__(self):
        self.base_url = "http://localhost:11434"
        self.available_models = []
        self.logger = logging.getLogger("models.ollama")
    
    async def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize the Ollama interface with the given configuration."""
        self.base_url = config.get("base_url", self.base_url)
        self.logger.info(f"Initializing Ollama interface with base URL: {self.base_url}")
        
        # Store available models configuration
        self.available_models = config.get("models", [])
        
        # Test connection
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/api/tags") as response:
                    if response.status == 200:
                        models_data = await response.json()
                        installed_models = [model["name"] for model in models_data.get("models", [])]
                        self.logger.info(f"Connected to Ollama. Available models: {installed_models}")
                    else:
                        self.logger.warning(f"Connected to Ollama but got status code: {response.status}")
        except Exception as e:
            self.logger.error(f"Failed to connect to Ollama at {self.base_url}: {str(e)}")
            # Continue anyway - the model might not be running yet but could start later
    
    async def generate(self, 
                      prompt: str, 
                      system_prompt: Optional[str] = None,
                      parameters: Optional[Dict[str, Any]] = None) -> str:
        """Generate text from the given prompt using an Ollama model."""
        # Use default parameters from config or empty dict
        params = {
            "temperature": 0.7,
            "max_tokens": 2048,
        }
        
        # Get model parameters if provided
        model_name = parameters.get("model") if parameters else None
        if not model_name:
            # Use first available model if none specified
            if self.available_models:
                model_name = self.available_models[0].get("name")
            else:
                model_name = "llama3"  # Default fallback
        
        # Update with model-specific parameters from config
        for model_config in self.available_models:
            if model_config.get("name") == model_name:
                model_params = model_config.get("parameters", {})
                params.update(model_params)
                break
        
        # Override with request-specific parameters
        if parameters:
            params.update(parameters)
        
        # Prepare the request payload
        payload = {
            "model": model_name,
            "prompt": prompt,
            "stream": False,
            **params
        }
        
        # Add system prompt if provided
        if system_prompt:
            payload["system"] = system_prompt
        
        try:
            self.logger.info(f"Generating text with Ollama model {model_name}")
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.base_url}/api/generate", json=payload) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        self.logger.error(f"Ollama API error: {response.status} - {error_text}")
                        return f"Error generating text: {response.status}"
                    
                    response_data = await response.json()
                    return response_data.get("response", "")
        except Exception as e:
            self.logger.error(f"Failed to generate text with Ollama: {str(e)}")
            return f"Error: {str(e)}"
    
    async def shutdown(self) -> None:
        """Clean up resources."""
        # Nothing to clean up for Ollama
        self.logger.info("Shutting down Ollama interface")