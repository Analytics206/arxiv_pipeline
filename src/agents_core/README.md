# AI Agent System for Research Papers and Code Documentation

This system provides configurable AI agents for:
1. Automatic code documentation and change tracking
2. Research paper analysis and concept mapping

## Setup

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Configure agents in `config/agent_config.yaml`

3. Start agents:
   ```
   python -m cli.main agent start code_documentation
   ```

## Docker Deployment

```
cd deployment
docker-compose up -d
```

## Configuration

Edit `config/agent_config.yaml` to configure:
- Model providers (Ollama, HuggingFace, Claude)
- Agent settings
- Monitoring paths and data sources

## CLI Commands

- List agents: `python -m cli.main agent list`
- Start agent: `python -m cli.main agent start <agent_name>`
- Stop agent: `python -m cli.main agent stop <agent_name>`
- Agent status: `python -m cli.main agent status <agent_name>`
- View configuration: `python -m cli.main config show`
- View logs: `python -m cli.main logs view <agent_name>`