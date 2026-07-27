if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Output "Installing uv..."
    Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
    $uvBin = Join-Path $env:USERPROFILE ".local\bin"
    if (Test-Path $uvBin) {
        $env:PATH = "$uvBin;$env:PATH"
    }
}

Write-Output "Installing Python 3.13..."
uv python install 3.13

Write-Output "Creating the environment and installing locked dependencies..."
uv sync --python 3.13 --extra agent --extra legacy --extra dev --frozen

Write-Output "Setup complete! You can activate the virtual environment with:"
Write-Output "Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass  # Only if scripts are disabled"
Write-Output ".venv\Scripts\activate.ps1  # In PowerShell"
Write-Output "# OR"
Write-Output ".venv\Scripts\activate.bat  # In Command Prompt"
