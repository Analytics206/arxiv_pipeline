from pathlib import Path
from models.models_to_compare import MODELS_TO_COMPARE
from evaluation.evaluate import evaluate_model
from evaluation.compare_results import compare_results

def main():
    # Set up paths
    base_dir = Path(__file__).parent
    results_dir = base_dir / "results"
    results_dir.mkdir(exist_ok=True)
    
    # Evaluate each model
    model_paths = []
    for i, model_name in enumerate(MODELS_TO_COMPARE):
        output_path = results_dir / f"model{i+1}_results.json"
        print(f"Evaluating {model_name}...")
        evaluate_model(model_name, output_path=str(output_path))
        model_paths.append(output_path)
        print(f"Evaluation complete. Results saved to: {output_path}")

    # Compare the results if we have at least two models
    if len(model_paths) >= 2:
        comparison_path = results_dir / "comparison_results.txt"
        print(f"\nComparing models...")
        compare_results(
            model1_path=str(model_paths[0]),
            model2_path=str(model_paths[1]),
            output_path=str(comparison_path)
        )
        print(f"Comparison complete. Results saved to: {comparison_path}")
    else:
        print("\nAt least two models are required for comparison.")

if __name__ == "__main__":
    main()