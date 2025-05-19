import json
from pathlib import Path
from models.load_model import load_model
from evaluation.metrics import (
    calculate_bleu, calculate_meteor, calculate_rouge,
    calculate_distinct_n, calculate_self_bleu
)

def evaluate_model(model_name, test_data_path=None, output_path=None):
    # Convert paths to Path objects if they're not already
    if test_data_path is None:
        test_data_path = Path(__file__).parent.parent / "test_data" / "test_data.json"
    elif isinstance(test_data_path, str):
        test_data_path = Path(test_data_path)
        
    if output_path is None:
        output_path = Path(__file__).parent.parent / "results" / "model_results.json"
    elif isinstance(output_path, str):
        output_path = Path(output_path)
    
    # Create results directory if it doesn't exist
    output_path.parent.mkdir(parents=True, exist_ok=True)
    # Load the model, tokenizer, and device
    model, tokenizer, device = load_model(model_name)

    # Load the test data with UTF-8 encoding to handle special characters
    with open(test_data_path, "r", encoding='utf-8') as f:
        test_data = json.load(f)

    results = {
        "model_name": model_name,
        "avg_bleu": 0,
        "avg_meteor": 0,
        "avg_rouge1": 0,
        "avg_rougeL": 0,
        "distinct_2": 0,
        "self_bleu": 0,
        "samples": []
    }

    generated_texts = []

    # Evaluate each sample
    for sample in test_data:
        input_text = sample["input"]
        reference = sample["response"]

        # Generate a response
        inputs = tokenizer(input_text, return_tensors="pt").to(device)
        attention_mask = inputs["attention_mask"]  # Explicitly get the attention mask
        outputs = model.generate(
            inputs["input_ids"],
            attention_mask=attention_mask,  # Pass the attention mask
            max_length=50,
            pad_token_id=tokenizer.eos_token_id  # Use eos_token_id as pad_token_id
        )
        generated = tokenizer.decode(outputs[0], skip_special_tokens=True)
        generated_texts.append(generated)

        # Calculate metrics
        bleu_score = calculate_bleu(reference, generated)
        meteor_score = calculate_meteor(reference, generated)
        rouge_scores = calculate_rouge(reference, generated)

        # Store results
        results["samples"].append({
            "input": input_text,
            "reference": reference,
            "generated": generated,
            "bleu": bleu_score,
            "meteor": meteor_score,
            "rouge1": rouge_scores["rouge1"].fmeasure,
            "rougeL": rouge_scores["rougeL"].fmeasure
        })

        # Update averages
        results["avg_bleu"] += bleu_score
        results["avg_meteor"] += meteor_score
        results["avg_rouge1"] += rouge_scores["rouge1"].fmeasure
        results["avg_rougeL"] += rouge_scores["rougeL"].fmeasure

    # Compute averages
    num_samples = len(test_data)
    results["avg_bleu"] /= num_samples
    results["avg_meteor"] /= num_samples
    results["avg_rouge1"] /= num_samples
    results["avg_rougeL"] /= num_samples

    # Calculate diversity metrics
    results["distinct_2"] = calculate_distinct_n(generated_texts, n=2)
    results["self_bleu"] = calculate_self_bleu(generated_texts, n=4)

    # Save results
    with open(output_path, "w") as f:
        json.dump(results, f, indent=4)

    print(f"Evaluation results for {model_name} saved to {output_path}")