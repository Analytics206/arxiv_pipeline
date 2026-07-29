#!/usr/bin/env bash
set -euo pipefail

# Detect OS
case "$(uname -s)" in
  Linux*|Darwin*)
    echo "Setting up uv on a Unix-like system"
    if ! command -v uv &> /dev/null; then
        echo "Installing uv..."
        curl -LsSf https://astral.sh/uv/install.sh | sh
        export PATH="$HOME/.local/bin:$PATH"
    fi
    ;;
  MINGW*|MSYS*|CYGWIN*)
    echo "Setting up uv on Windows"
    if ! command -v uv &> /dev/null; then
        echo "Install uv from https://docs.astral.sh/uv/getting-started/installation/"
        exit 1
    fi
    ;;
  *)
    echo "Unsupported operating system: $(uname -s)"
    exit 1
    ;;
esac

echo "Installing Python 3.13..."
uv python install 3.13

echo "Creating the environment and installing locked dependencies..."
uv sync --python 3.13 --extra agent --extra dev --frozen

echo "Setup complete! Activate the virtual environment with:"
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    echo ".venv\\Scripts\\activate.bat  # In CMD"
    echo ".venv\\Scripts\\Activate.ps1  # In PowerShell"
else
    echo "source .venv/bin/activate"
fi
