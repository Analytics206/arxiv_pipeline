import requests
from bs4 import BeautifulSoup
import json
from pathlib import Path
from datetime import datetime

# Configuration
OUTPUT_DIR = Path(__file__).parent.parent / "model_metadata_viewer"
OUTPUT_FILE = OUTPUT_DIR / "ollama_available_models.json"
OLLAMA_LIBRARY_URL = "https://ollama.com/library"

# Ensure output directory exists
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def fetch_ollama_available_models():
    try:
        print(f"Fetching available models from {OLLAMA_LIBRARY_URL}...")
        response = requests.get(OLLAMA_LIBRARY_URL, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        model_cards = soup.select('a[href^="/library/"]')
        
        if not model_cards:
            print("Warning: No model cards found on the page.")
            return {"models": []}
        
        models = []
        seen_models = set()  # To avoid duplicates
        
        for card in model_cards:
            try:
                href = card.get('href', '')
                if not href or '/library/' not in href:
                    continue
                    
                name = href.split('/library/')[-1].strip()
                if not name or name in seen_models:
                    continue
                    
                seen_models.add(name)
                link = f"https://ollama.com/library/{name}"
                title = card.text.strip()
                
                models.append({
                    "modelId": name,
                    "displayName": title if title else name,
                    "link": link,
                    "fetched_at": datetime.utcnow().isoformat()
                })
            except Exception as e:
                print(f"Error processing model card: {str(e)}")
                continue
        
        return {"models": models}
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching Ollama library: {str(e)}")
        return {"models": []}
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")
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
    data = fetch_ollama_available_models()
    
    if data["models"]:
        if save_to_json(data, OUTPUT_FILE):
            print(f"Saved {len(data['models'])} available Ollama models to {OUTPUT_FILE}")
        else:
            print("Failed to save Ollama available models data.")
    else:
        print("No Ollama models found or error occurred while fetching.")
