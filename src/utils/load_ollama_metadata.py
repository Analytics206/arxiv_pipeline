import requests
import json
import os
from pathlib import Path

# Configuration
OUTPUT_DIR = Path(__file__).parent.parent / "model_metadata_viewer"
OUTPUT_FILE = OUTPUT_DIR / "ollama_models_data.json"

# Ensure output directory exists
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def fetch_ollama_models():
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=10)
        response.raise_for_status()  # Raises an HTTPError for bad responses
        
        models_data = response.json().get("models", [])
        if not models_data:
            print("Warning: No models found in Ollama.")
            return {"models": []}
        
        models = []
        for model in models_data:
            models.append({
                "modelId": model.get("name"),
                "digest": model.get("digest"),
                "size": model.get("size", 0),
                "modified_at": model.get("modified_at", "N/A"),
                "tags": model.get("tags", []),
                "parameters": {},
                "benchmark_scores": {}
            })
        
        return {"models": models}
        
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to Ollama API: {str(e)}")
        return {"models": []}
    except json.JSONDecodeError:
        print("Error: Invalid JSON response from Ollama API")
        return {"models": []}

def save_to_json(data, filename):
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Successfully saved data to {filename}")
        return True
    except Exception as e:
        print(f"Error saving to {filename}: {str(e)}")
        return False

if __name__ == "__main__":
    print("Fetching installed Ollama models...")
    data = fetch_ollama_models()
    
    if data["models"]:
        if save_to_json(data, OUTPUT_FILE):
            print(f"Saved {len(data['models'])} Ollama models to {OUTPUT_FILE}")
        else:
            print("Failed to save Ollama model data.")
    else:
        print("No Ollama models found or error occurred while fetching.")
