# CLI entry point
# cli/main.py
import click
import asyncio
import logging
import os
import sys
from typing import Dict, Any

from agent_core.config import load_config, create_default_config
from agents.manager import AgentManager

# Setup logging
def setup_logging(log_level: str = "INFO") -> None:
    """Setup logging configuration."""
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {log_level}")
    
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("logs/agent_system.log")
        ]
    )

# Create the Click command group
@click.group()
@click.option("--config", default="config/agent_config.yaml", help="Path to configuration file")
@click.option("--log-level", default="INFO", help="Logging level")
@click.pass_context
def cli(ctx, config, log_level):
    """Command line interface for AI Agent System."""
    setup_logging(log_level)
    
    # Create default config if it doesn't exist
    create_default_config(config)
    
    # Store configuration path in context
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = config

# Agent command group
@cli.group()
def agent():
    """Manage AI agents."""
    pass

@agent.command("list")
@click.pass_context
def list_agents(ctx):
    """List all configured agents and their status."""
    config_path = ctx.obj["config_path"]
    config = load_config(config_path)
    
    click.echo("Configured agents:")
    for agent_name, agent_config in config.get("agents", {}).items():
        status = "Enabled" if agent_config.get("enabled", True) else "Disabled"
        model = agent_config.get("model", "default")
        click.echo(f"- {agent_name} ({status}, Model: {model})")

@agent.command("start")
@click.argument("agent_name")
@click.pass_context
def start_agent(ctx, agent_name):
    """Start a specific agent."""
    config_path = ctx.obj["config_path"]
    
    # Run in event loop
    asyncio.run(_start_agent(config_path, agent_name))

async def _start_agent(config_path: str, agent_name: str) -> None:
    """Helper to start an agent asynchronously."""
    manager = AgentManager(config_path)
    await manager.initialize()
    
    # Check if agent exists
    config = load_config(config_path)
    if agent_name not in config.get("agents", {}):
        click.echo(f"Error: Agent '{agent_name}' not found in configuration")
        return
    
    # Start the agent
    result = await manager.start_agent(agent_name)
    
    if result:
        click.echo(f"Started agent: {agent_name}")
        
        # Keep the process running until interrupted
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            click.echo("Stopping agent...")
            await manager.stop_agent(agent_name)
            click.echo(f"Agent {agent_name} stopped")
    else:
        click.echo(f"Failed to start agent: {agent_name}")

@agent.command("stop")
@click.argument("agent_name")
@click.pass_context
def stop_agent(ctx, agent_name):
    """Stop a specific agent."""
    config_path = ctx.obj["config_path"]
    
    # Run in event loop
    asyncio.run(_stop_agent(config_path, agent_name))

async def _stop_agent(config_path: str, agent_name: str) -> None:
    """Helper to stop an agent asynchronously."""
    manager = AgentManager(config_path)
    await manager.initialize()
    
    result = await manager.stop_agent(agent_name)
    
    if result:
        click.echo(f"Stopped agent: {agent_name}")
    else:
        click.echo(f"Failed to stop agent: {agent_name}")

@agent.command("status")
@click.argument("agent_name", required=False)
@click.pass_context
def agent_status(ctx, agent_name):
    """Check the status of agents."""
    config_path = ctx.obj["config_path"]
    
    # Run in event loop
    asyncio.run(_agent_status(config_path, agent_name))

async def _agent_status(config_path: str, agent_name: str = None) -> None:
    """Helper to check agent status asynchronously."""
    manager = AgentManager(config_path)
    await manager.initialize()
    
    if agent_name:
        # Check specific agent
        status = manager.get_agent_status(agent_name)
        click.echo(f"Agent: {status['agent']}")
        click.echo(f"Status: {status['status']}")
        if status['last_run']:
            click.echo(f"Last run: {status['last_run']}")
    else:
        # List all agents
        statuses = manager.list_agents()
        for status in statuses:
            click.echo(f"Agent: {status['agent']}")
            click.echo(f"Status: {status['status']}")
            if status['last_run']:
                click.echo(f"Last run: {status['last_run']}")
            click.echo("")

# Configuration command group
@cli.group()
def config():
    """Manage system configuration."""
    pass

@config.command("show")
@click.pass_context
def show_config(ctx):
    """Show the current configuration."""
    config_path = ctx.obj["config_path"]
    config = load_config(config_path)
    
    # Display configuration sections
    click.echo("System Configuration:")
    for key, value in config.get("system", {}).items():
        click.echo(f"- {key}: {value}")
    
    click.echo("\nModel Providers:")
    default_provider = config.get("models", {}).get("default")
    click.echo(f"- Default: {default_provider}")
    
    for provider, provider_config in config.get("models", {}).get("providers", {}).items():
        enabled = provider_config.get("enabled", True)
        status = "Enabled" if enabled else "Disabled"
        click.echo(f"- {provider} ({status})")
        
        if enabled:
            models = provider_config.get("models", [])
            for model in models:
                name = model.get("name", model.get("repo_id", "unknown"))
                click.echo(f"  - {name}")
    
    click.echo("\nConfigured Agents:")
    for agent_name, agent_config in config.get("agents", {}).items():
        status = "Enabled" if agent_config.get("enabled", True) else "Disabled"
        model = agent_config.get("model", "default")
        click.echo(f"- {agent_name} ({status}, Model: {model})")

# Logs command group
@cli.group()
def logs():
    """View and manage logs."""
    pass

@logs.command("view")
@click.argument("agent_name", required=False)
@click.option("--lines", default=50, help="Number of lines to show")
@click.pass_context
def view_logs(ctx, agent_name, lines):
    """View logs for the system or a specific agent."""
    config_path = ctx.obj["config_path"]
    config = load_config(config_path)
    
    log_dir = config.get("system", {}).get("log_dir", "./logs")
    
    if agent_name:
        log_file = os.path.join(log_dir, f"{agent_name}.log")
        if not os.path.exists(log_file):
            log_file = os.path.join(log_dir, "agent_system.log")
            click.echo(f"No specific log for {agent_name}, showing system log")
    else:
        log_file = os.path.join(log_dir, "agent_system.log")
    
    # Check if log file exists
    if not os.path.exists(log_file):
        click.echo(f"Log file not found: {log_file}")
        return
    
    # Display log content
    try:
        with open(log_file, 'r') as file:
            # Get the last N lines
            content = file.readlines()
            tail = content[-lines:] if len(content) > lines else content
            for line in tail:
                click.echo(line.strip())
    except Exception as e:
        click.echo(f"Error reading log file: {str(e)}")

if __name__ == "__main__":
    cli(obj={})