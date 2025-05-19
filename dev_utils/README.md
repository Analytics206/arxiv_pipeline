# Development Utilities

This directory contains various development and maintenance tools for the ArXiv Pipeline project.

## Metadata Generator (`metadata_generator.py`)

A powerful tool for generating comprehensive metadata about the project's codebase structure, including modules, classes, functions, and their relationships.

### Features

- **Automatic Project Root Detection**: Works from any directory within the project
- **Comprehensive Code Analysis**: Extracts classes, functions, methods, and their docstrings
- **YAML Output**: Generates well-structured YAML files for easy integration with other tools
- **Dependency Tracking**: Identifies imports and function calls between modules
- **Flexible Configuration**: Supports analyzing the entire project or specific subdirectories

### Installation

No additional installation is required beyond the project's dependencies.

### Usage

```bash
# Generate metadata for the entire project (saved to dev_utils/system_metadata.yaml by default)
python -m dev_utils.metadata_generator .

# Analyze a specific module (save to default location)
python -m dev_utils.metadata_generator src/llm_eval

# Specify a custom output location
python -m dev_utils.metadata_generator . -o custom_location/metadata.yaml
```

### Output Format

The generated YAML file includes:

- Project information (name, path)
- List of all Python modules with their components
- For each component (class/function/method):
  - Name and type
  - File location and line number
  - Docstring and metadata
  - Dependencies (imports and function calls)

### Advanced Usage

#### Excluding Directories

By default, the script excludes common directories like `venv`, `__pycache__`, etc. To modify this behavior, edit the `EXCLUDE_DIRS` set in `metadata_generator.py`.

#### Metadata in Docstrings

You can include YAML metadata in docstrings using the following format:

```python
def example_function():
    """
    This is a function with metadata.
    ---
    author: Your Name
    version: 1.0.0
    status: beta
    ---
    This is the actual docstring content.
    """
    pass
```

## Other Utilities

### `clear_neo4j.py`

Utility script to safely clear Neo4j database data.

```bash
python -m dev_utils.clear_neo4j [--dry-run] [--config path/to/config.yaml]
```

## Development Guidelines

When adding new utilities:

1. Place them in this directory
2. Follow the project's coding standards
3. Include comprehensive docstrings and type hints
4. Add usage examples to this README
5. Update the project's main README if the utility is user-facing

## Troubleshooting

- **Syntax Errors**: The script will skip files with syntax errors but log them
- **Encoding Issues**: Files are read with UTF-8 encoding with error replacement
- **Performance**: For large projects, consider analyzing specific subdirectories

## License

This project is part of the ArXiv Pipeline and follows the same licensing terms.