# Configuration loading and validation
# agent_core/config.py
import os
import yaml
import logging
from typing import Dict, Any, Optional
import re
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def load_config(config_path: str) -> Dict[str, Any]:
    """
    Load and validate configuration from a YAML file.
    Replaces environment variables in the format ${ENV_VAR}.
    """
    logger = logging.getLogger("config")
    
    if not os.path.exists(config_path):
        logger.error(f"Configuration file not found: {config_path}")
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    try:
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
        
        # Replace environment variables
        config = _replace_env_vars(config)
        
        # Validate configuration
        _validate_config(config)
        
        return config
    except yaml.YAMLError as e:
        logger.error(f"Error parsing YAML configuration: {str(e)}")
        raise ValueError(f"Invalid YAML configuration: {str(e)}")
    except Exception as e:
        logger.error(f"Error loading configuration: {str(e)}")
        raise

def _replace_env_vars(obj: Any) -> Any:
    """Recursively replace environment variables in strings."""
    if isinstance(obj, str):
        # Find all ${ENV_VAR} patterns
        env_vars = re.findall(r'\${([^}]+)}', obj)
        for env_var in env_vars:
            env_value = os.environ.get(env_var)
            if env_value is not None:
                obj = obj.replace(f"${{{env_var}}}", env_value)
        return obj
    elif isinstance(obj, dict):
        return {k: _replace_env_vars(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_replace_env_vars(item) for item in obj]
    else:
        return obj

def _validate_config(config: Dict[str, Any]) -> None:
    """Validate the configuration structure."""
    logger = logging.getLogger("config")
    
    # Check for required top-level sections
    required_sections = ["system", "models", "agents"]
    for section in required_sections:
        if section not in config:
            logger.warning(f"Missing required section in configuration: {section}")
    
    # Validate system section
    system_config = config.get("system", {})
    if not isinstance(system_config, dict):
        raise ValueError("System configuration must be a dictionary")
    
    # Validate models section
    models_config = config.get("models", {})
    if not isinstance(models_config, dict):
        raise ValueError("Models configuration must be a dictionary")
    
    # Check if default model provider is specified
    default_provider = models_config.get("default")
    if not default_provider:
        logger.warning("No default model provider specified")
    
    # Validate providers
    providers = models_config.get("providers", {})
    if not isinstance(providers, dict):
        raise ValueError("Model providers must be a dictionary")
    
    if default_provider and default_provider not in providers:
        logger.warning(f"Default provider '{default_provider}' not found in providers")
    
    # Validate agents section
    agents_config = config.get("agents", {})
    if not isinstance(agents_config, dict):
        raise ValueError("Agents configuration must be a dictionary")
    
    # Validate each agent configuration
    for agent_name, agent_config in agents_config.items():
        if not isinstance(agent_config, dict):
            raise ValueError(f"Configuration for agent '{agent_name}' must be a dictionary")
        
        # Check if model is specified
        if "model" not in agent_config:
            logger.warning(f"No model specified for agent '{agent_name}'")

def create_default_config(output_path: str) -> None:
    """Create a default configuration file if none exists."""
    if os.path.exists(output_path):
        return
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    default_config = {
        "system": {
            "log_level": "INFO",
            "log_dir": "./logs",
            "agent_storage_dir": "./agent_data"
        },
        "models": {
            "default": "ollama",
            "providers": {
                "ollama": {
                    "base_url": "http://localhost:11434",
                    "models": [
                        {
                            "name": "llama3",
                            "parameters": {
                                "temperature": 0.7,
                                "max_tokens": 4096
                            }
                        }
                    ]
                }
            }
        },
        "agents": {
            "code_documentation": {
                "enabled": True,
                "model": "llama3",
                "watch_paths": ["./src"],
                "ignore_patterns": ["*.pyc", "__pycache__"],
                "update_frequency": "on_change"
            }
        }
    }
    
    with open(output_path, 'w') as file:
        yaml.dump(default_config, file, default_flow_style=False)