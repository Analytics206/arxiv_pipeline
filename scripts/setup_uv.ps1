# Check if uv is installed
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Output "Installing uv..."
    # For Windows, install using pip
    pip install uv
}

# Create virtual environment
Write-Output "Creating virtual environment..."
uv venv

# Install dependencies using uv
Write-Output "Installing dependencies..."
uv pip install -e .

# Install dev dependencies 
Write-Output "Installing dev dependencies..."
uv pip install -e ".[dev]"

Write-Output "Setup complete! You can activate the virtual environment with:"
Write-Output ".venv\Scripts\activate.ps1  # In PowerShell"
Write-Output "# OR"
Write-Output ".venv\Scripts\activate.bat  # In Command Prompt"