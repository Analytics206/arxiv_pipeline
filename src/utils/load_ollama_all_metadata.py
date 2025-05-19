import requests
from bs4 import BeautifulSoup
import json

def fetch_ollama_available_models():
    url = "https://ollama.com/library"
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception("Failed to fetch Ollama library page")

    soup = BeautifulSoup(response.text, 'html.parser')
    model_cards = soup.select('a[href^="/library/"]')

    models = []
    for card in model_cards:
        name = card['href'].split('/library/')[-1].strip()
        link = f"https://ollama.com/library/{name}"
        title = card.text.strip()
        models.append({
            "modelId": name,
            "displayName": title if title else name,
            "link": link
        })

    return {"models": models}

if __name__ == "__main__":
    data = fetch_ollama_available_models()
    with open("ollama_available_models.json", "w") as f:
        json.dump(data, f, indent=2)
    print("Saved available Ollama models to 'ollama_available_models.json'")
