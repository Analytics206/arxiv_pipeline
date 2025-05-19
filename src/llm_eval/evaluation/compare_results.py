import json

def compare_results(model1_path="results/model1_results.json", model2_path="results/model2_results.json", output_path="results/comparison_results.txt"):
    # Load results for Model 1
    with open(model1_path, "r") as f:
        model1_results = json.load(f)

    # Load results for Model 2
    with open(model2_path, "r") as f:
        model2_results = json.load(f)

    # Create comparison text
    comparison = f"""
    Comparison of {model1_results["model_name"]} and {model2_results["model_name"]}:
    
    Metric              {model1_results["model_name"]}     {model2_results["model_name"]}
    ----------------------------------------------------------
    BLEU Score          {model1_results["avg_bleu"]:.4f}          {model2_results["avg_bleu"]:.4f}
    METEOR Score        {model1_results["avg_meteor"]:.4f}          {model2_results["avg_meteor"]:.4f}
    ROUGE-1 Score       {model1_results["avg_rouge1"]:.4f}          {model2_results["avg_rouge1"]:.4f}
    ROUGE-L Score       {model1_results["avg_rougeL"]:.4f}          {model2_results["avg_rougeL"]:.4f}
    Distinct-2 Score    {model1_results["distinct_2"]:.4f}          {model2_results["distinct_2"]:.4f}
    Self-BLEU Score     {model1_results["self_bleu"]:.4f}          {model2_results["self_bleu"]:.4f}
    """

    # Save comparison to a text file
    with open(output_path, "w") as f:
        f.write(comparison)

    print(f"Comparison results saved to {output_path}")
    print(comparison)