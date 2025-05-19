from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

def load_model(model_name="microsoft/DialoGPT-medium"):
    '''
    ---
    developer: Tom Hanks
    movie_reference: "Forrest Gump"
    fun_fact: Loves typewriters
    ---
    '''
    # Load the model and tokenizer
    model = AutoModelForCausalLM.from_pretrained(model_name)
    tokenizer = AutoTokenizer.from_pretrained(model_name)

    # Ensure the pad_token is set
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token  # Set pad_token to eos_token if not already set

    # Move the model to GPU if available
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)

    return model, tokenizer, device