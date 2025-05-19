import requests
import json
from datetime import datetime

# Configuration
API_URL = "https://huggingface.co/api/models"
QUERY_LIMIT = 100  # Max models per request
OUTPUT_FILE = "open_models_data.json"

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
    with open(filename, "w", encoding="utf-8") as f:
        json.dump({"fetched_at": datetime.utcnow().isoformat(), "models": data}, f, indent=2)

def main():
    print("Fetching model data from Hugging Face...")
    models_raw = fetch_models(limit=QUERY_LIMIT, filters=FILTERS)
    models_info = extract_model_info(models_raw)
    save_to_json(models_info, OUTPUT_FILE)
    print(f"Saved {len(models_info)} models to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
