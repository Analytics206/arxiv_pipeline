#!/bin/bash
set -e

# Detect OS
case "$(uname -s)" in
  Linux*|Darwin*)
    echo "Setting up UV on Unix-like system"
    # Check if UV is installed
    if ! command -v uv &> /dev/null; then
        echo "Installing UV..."
        curl -LsSf https://astral.sh/uv/install.sh | sh
        # Add to path for the current session
        export PATH="$HOME/.cargo/bin:$PATH"
    fi
    ;;
  MINGW*|MSYS*|CYGWIN*)
    echo "Setting up UV on Windows"
    # For Windows, use pip to install UV if not present
    if ! command -v uv &> /dev/null; then
        echo "Installing UV..."
        pip install uv
    fi
    ;;
  *)
    echo "Unknown OS. Installing UV via pip"
    pip install uv
    ;;
esac

# Create virtual environment
echo "Creating virtual environment..."
uv venv

# Install dependencies
echo "Installing dependencies..."
uv pip install -e .

# Install dev dependencies
echo "Installing dev dependencies..."
uv pip install -e ".[dev]"

echo "Setup complete! You can activate the virtual environment with:"
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    echo ".venv\\Scripts\\activate.bat  # In CMD"
    echo ".venv\\Scripts\\Activate.ps1  # In PowerShell"
else
    echo "source .venv/bin/activate"
fi