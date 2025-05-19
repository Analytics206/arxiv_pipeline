import requests
import json

# Fetch list of models from Hugging Face Model Hub
response = requests.get("https://huggingface.co/api/models")
models = response.json()

# Parse the models data
parsed_models = []
for model in models:
    model_info = {
        "Model ID": model["modelId"],
        "Name": model.get("id", "Not available"),
        "Likes": model.get("likes", 0),
        "Downloads": model.get("downloads", 0),
        "Tags": model.get("tags", []),
        "Pipeline Tag": model.get("pipeline_tag", "Not available"),
        "Created At": model.get("createdAt", "Not available"),
    }
    parsed_models.append(model_info)

# Print the parsed models data
for i, model in enumerate(parsed_models):
    print(f"**Model {i+1}:**")
    for key, value in model.items():
        print(f"{key}: {value}")
    print("\n")

# Filter models by task (e.g. "text-to-image")
text_to_image_models = [model for model in parsed_models if "text-to-image" in model["Tags"]]

print("\n**Text to Image Models:**")
for i, model in enumerate(text_to_image_models):
    print(f"{i+1}. {model['Model ID']}")