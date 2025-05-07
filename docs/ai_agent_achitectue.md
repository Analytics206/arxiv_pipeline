┌─────────────────────────────────────┐     ┌──────────────────────────────┐
│          Agent Management           │     │         Data Sources         │
│  ┌────────────┐    ┌────────────┐   │     │  ┌─────────┐  ┌─────────┐   │
│  │ Code Doc   │    │ Research   │   │     │  │         │  │         │   │
│  │ Agent      │◄───┤ Analysis   │   │     │  │ MongoDB │  │ Neo4j   │   │
│  └────────────┘    │ Agent      │   │     │  │         │  │         │   │
│        ▲           └────────────┘   │     │  └─────────┘  └─────────┘   │
│        │                ▲           │     │        ▲          ▲         │
└────────┼────────────────┼───────────┘     └────────┼──────────┼─────────┘
         │                │                          │          │
         │                │                          │          │
┌────────┼────────────────┼──────────────────────────┼──────────┼─────────┐
│        │   Agent Core   │                          │          │         │
│   ┌────▼───────────────▼─────┐              ┌──────▼──────────▼─────┐   │
│   │                          │              │                       │   │
│   │     Model Interface      │◄─────────────┤    Data Processors    │   │
│   │                          │              │                       │   │
│   └──────────────┬───────────┘              └───────────────────────┘   │
│                  │                                                      │
│   ┌──────────────▼───────────┐              ┌───────────────────────┐   │
│   │                          │              │                       │   │
│   │   Configuration Manager  │◄─────────────┤    Logging System     │   │
│   │                          │              │                       │   │
│   └──────────────────────────┘              └───────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘

## 2. Agent Core Module
agent_core/
├── __init__.py
├── config.py          # Configuration loading and validation
├── models/            # Model interfaces
│   ├── __init__.py
│   ├── base.py        # Abstract base class
│   ├── ollama.py      # Ollama integration
│   ├── huggingface.py # HuggingFace integration
│   └── claude.py      # Claude integration
├── logging_utils.py   # Logging setup and utilities
└── data/              # Data processing utilities
    ├── __init__.py
    ├── mongodb.py
    ├── neo4j.py
    └── qdrant.py

## 3. Agent Implementations
agents/
├── __init__.py
├── base_agent.py      # Base agent class
├── code_doc/          # Code documentation agent
│   ├── __init__.py
│   ├── agent.py       # Main agent implementation
│   ├── git_monitor.py # Git integration
│   ├── code_parser.py # Code parsing utilities
│   └── templates/     # Prompt templates
├── research/          # Research paper analysis agent
│   ├── __init__.py
│   ├── agent.py       # Main agent implementation
│   ├── paper_processor.py
│   ├── concept_mapper.py
│   └── templates/     # Prompt templates
└── manager.py         # Agent lifecycle management

## 4. Deployment and Orchestration
deployment/
├── docker-compose.yml        # Main compose file
├── Dockerfile.agent-base     # Base Docker image for agents
├── Dockerfile.code-agent     # Code documentation agent
├── Dockerfile.research-agent # Research paper agent
└── scripts/
    ├── setup.sh              # Setup script
    └── start_agents.sh       # Agent startup script

## 5. CLI Interface
cli/
├── __init__.py
├── main.py          # CLI entry point
├── commands/        # CLI command implementations
│   ├── __init__.py
│   ├── agent.py     # Agent management commands
│   ├── config.py    # Configuration commands
│   └── logs.py      # Log viewing commands
└── utils.py         # CLI utilities