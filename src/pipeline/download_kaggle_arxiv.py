"""
Kaggle arXiv Dataset Downloader

This script downloads the arXiv dataset from Kaggle and saves it to the specified directory.
It's designed to work with the ArXiv Pipeline project's architecture.

Configuration is loaded from config/default.yaml and secure/kaggle.json.
"""

import os
import sys
import json
import logging
import argparse
import zipfile
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, Union, List

import yaml
import kaggle
from kaggle.api.kaggle_api_extended import KaggleApi
from dotenv import load_dotenv
import pandas as pd

# Configure basic logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger(__name__)

class ConfigError(Exception):
    """Raised when there is an error in the configuration."""
    pass

def load_config() -> Dict[str, Any]:
    """
    Load configuration from default.yaml and kaggle.json.
    
    Returns:
        Dict containing the merged configuration.
    """
    try:
        # Load main config
        config_path = Path(__file__).parent.parent.parent / "config" / "default.yaml"
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Load kaggle.json credentials
        creds_path = Path(__file__).parent.parent.parent / config['kaggle']['credentials']['path']
        if not creds_path.exists():
            raise ConfigError(f"Kaggle credentials not found at {creds_path}")
            
        with open(creds_path, 'r') as f:
            creds = json.load(f)
            
        # Merge credentials into config
        config['kaggle']['credentials'].update(creds)
        
        # Set up logging level from config
        log_level = getattr(logging, config['kaggle']['logging']['level'].upper())
        logger.setLevel(log_level)
        
        return config
        
    except Exception as e:
        logger.error(f"Failed to load configuration: {str(e)}")
        raise ConfigError(f"Configuration error: {str(e)}")

def setup_environment(config: Dict[str, Any]) -> None:
    """
    Set up environment variables and Kaggle credentials.
    
    Args:
        config: Configuration dictionary
    """
    # Load environment variables from .env file if it exists
    load_dotenv()
    
    # Set Kaggle credentials path
    creds_path = Path(config["kaggle"]["credentials"]["path"])
    kaggle_dir = Path.home() / ".kaggle"
    
    try:
        # Create .kaggle directory if it doesn't exist
        kaggle_dir.mkdir(exist_ok=True, mode=0o700)  # Set proper permissions
        
        if creds_path.exists():
            # Copy the credentials to the .kaggle directory
            dest_file = kaggle_dir / "kaggle.json"
            import shutil
            shutil.copy2(creds_path, dest_file)
            
            # Set proper permissions (read/write for user only)
            dest_file.chmod(0o600)
            
            logger.info(f"Kaggle credentials set up in: {dest_file}")
        else:
            logger.warning(f"Kaggle credentials not found at: {creds_path}")
            logger.info("Please make sure you have a valid kaggle.json file in the secure/ directory")
            
    except Exception as e:
        logger.error(f"Error setting up Kaggle credentials: {str(e)}")
        logger.info("You may need to manually set up your Kaggle credentials")
        logger.info("1. Go to https://www.kaggle.com/account")
        logger.info("2. Scroll down to 'API' section")
        logger.info("3. Click 'Create New API Token'")
        logger.info(f"4. Save the kaggle.json file to: {creds_path}")
        raise

def ensure_directory_exists(directory: str) -> Path:
    """
    Ensure the download directory exists, create it if it doesn't.
    
    Args:
        directory: Path to the directory
        
    Returns:
        Path: Path object for the directory
    """
    path = Path(directory)
    try:
        path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Using download directory: {path.absolute()}")
        return path
    except Exception as e:
        logger.error(f"Failed to create directory {directory}: {str(e)}")
        raise

def download_dataset(dataset_name: str, download_path: Path, version: str = "1") -> Path:
    """
    Download and extract the arXiv dataset from Kaggle.
    
    Args:
        dataset_name: Name of the Kaggle dataset (e.g., "Cornell-University/arxiv")
        download_path: Directory where the dataset will be saved
        version: Dataset version (default: "1")
        
    Returns:
        Path: Path to the downloaded dataset directory
        
    Raises:
        RuntimeError: If the dataset download or extraction fails
    """
    try:
        # Initialize Kaggle API
        api = KaggleApi()
        api.authenticate()
        
        # Ensure download directory exists
        download_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Downloading dataset {dataset_name}...")
        
        # Download the dataset files
        zip_path = download_path / f"{dataset_name.split('/')[-1]}.zip"
        
        # Download the dataset
        api.dataset_download_files(
            dataset=dataset_name,
            path=str(download_path),
            unzip=False
        )
        
        # Check if the zip file exists
        if not zip_path.exists():
            # Sometimes the zip file has a different name
            zip_files = list(download_path.glob("*.zip"))
            if not zip_files:
                raise FileNotFoundError("No zip file found after download")
            zip_path = zip_files[0]
        
        logger.info(f"Extracting {zip_path} to {download_path}...")
        
        # Extract the zip file
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(download_path)
        
        # Remove the zip file after extraction
        zip_path.unlink()
        
        logger.info(f"Successfully downloaded and extracted dataset to: {download_path}")
        return download_path
        
    except Exception as e:
        error_msg = f"Failed to download dataset {dataset_name}: {str(e)}"
        logger.error(error_msg)
        logger.info("\nTroubleshooting tips:")
        logger.info("1. Make sure you have a valid kaggle.json in the secure/ directory")
        logger.info("2. Verify you have accepted the dataset's terms on Kaggle")
        logger.info("3. Check if the dataset name is correct")
        logger.info(f"4. Try visiting the dataset page: https://www.kaggle.com/datasets/{dataset_name}")
        logger.info("5. Ensure you have sufficient disk space (the arXiv dataset is ~8GB)")
        logger.info("6. Make sure you have the latest kaggle package: pip install --upgrade kaggle")
        raise RuntimeError(error_msg) from e

def main() -> None:
    """Main function to handle the download process."""
    try:
        # Parse command line arguments
        parser = argparse.ArgumentParser(description="Download arXiv dataset from Kaggle")
        parser.add_argument(
            "--path",
            type=str,
            help="Path to download the dataset (overrides config)",
        )
        parser.add_argument(
            "--dataset",
            type=str,
            help="Dataset name (e.g., 'Cornell-University/arxiv')",
        )
        parser.add_argument(
            "--version",
            type=str,
            default="1",
            help="Dataset version (default: 1)",
        )
        args = parser.parse_args()

        # Load configuration
        config = load_config()
        
        # Set up environment
        setup_environment(config)
        
        # Get parameters from args or config
        download_path = Path(args.path) if args.path else Path(config["kaggle"]["download_path"])
        dataset_name = args.dataset if args.dataset else config["kaggle"]["dataset"]
        version = args.version if args.version else config["kaggle"].get("version", "1")
        
        logger.info(f"Using dataset: {dataset_name} (version: {version})")
        logger.info(f"Download path: {download_path}")
        
        # Ensure download directory exists
        download_path = ensure_directory_exists(str(download_path))
        
        # Download the dataset
        result_path = download_dataset(
            dataset_name=dataset_name,
            download_path=download_path,
            version=version
        )
        
        logger.info(f"\nDownload completed successfully!")
        logger.info(f"Dataset saved to: {result_path}")
        
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
