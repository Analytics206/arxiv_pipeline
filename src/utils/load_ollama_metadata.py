import requests
import json

def fetch_ollama_models():
    response = requests.get("http://localhost:11434/api/tags")
    if response.status_code != 200:
        raise Exception("Failed to fetch models from Ollama.")

    models_data = response.json().get("models", [])
    
    models = []
    for model in models_data:
        models.append({
            "modelId": model.get("name"),
            "digest": model.get("digest"),
            "size": model.get("size", "N/A"),
            "modified_at": model.get("modified_at", "N/A"),
            "tags": model.get("tags", []),
            "parameters": {},  # Ollama doesn't expose detailed parameters via /tags
            "benchmark_scores": {}  # You could define these manually or leave empty
        })

    return {"models": models}

if __name__ == "__main__":
    data = fetch_ollama_models()
    with open("ollama_models_data.json", "w") as f:
        json.dump(data, f, indent=2)

    print("Saved Ollama model metadata to 'ollama_models_data.json'")
