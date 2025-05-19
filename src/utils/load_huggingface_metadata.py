import requests
import json
import os
from datetime import datetime
from pathlib import Path

# Configuration
API_URL = "https://huggingface.co/api/models"
QUERY_LIMIT = 100  # Max models per request
OUTPUT_DIR = Path(__file__).parent.parent / "model_metadata_viewer"
OUTPUT_FILE = OUTPUT_DIR / "open_models_data.json"

# Ensure output directory exists
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Optional filter keywords (you can modify these)
FILTERS = {
    "private": False,  # Only public models
    "pipeline_tag": None  # E.g., "text-generation", "image-classification"
}

def fetch_models(limit=QUERY_LIMIT, filters=None):
    params = {
        "limit": limit,
    }
    if filters:
        params.update(filters)

    response = requests.get(API_URL, params=params)
    response.raise_for_status()
    return response.json()

def extract_model_info(model_data):
    extracted = []
    for model in model_data:
        card_data = model.get("cardData", {})
        extracted.append({
            "modelId": model.get("modelId"),
            "likes": model.get("likes"),
            "downloads": model.get("downloads"),
            "pipeline_tag": model.get("pipeline_tag"),
            "tags": model.get("tags", []),
            "library_name": model.get("library_name"),
            "last_modified": model.get("lastModified"),
            "sha": model.get("sha"),
            "parameters": card_data.get("model_parameters", {}),
            "benchmark_scores": card_data.get("eval_results", {})
        })
    return extracted

def save_to_json(data, filename):
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump({"fetched_at": datetime.utcnow().isoformat(), "models": data}, f, indent=2)
        print(f"Successfully saved data to {filename}")
        return True
    except Exception as e:
        print(f"Error saving to {filename}: {str(e)}")
        return False

def main():
    print(f"Fetching up to {QUERY_LIMIT} models from Hugging Face...")
    try:
        models_raw = fetch_models(limit=QUERY_LIMIT, filters=FILTERS)
        if not models_raw:
            print("No models found with the current filters.")
            return
        
        models_info = extract_model_info(models_raw)
        if save_to_json(models_info, OUTPUT_FILE):
            print(f"Saved {len(models_info)} models to {OUTPUT_FILE}")
        else:
            print("Failed to save model data.")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()
