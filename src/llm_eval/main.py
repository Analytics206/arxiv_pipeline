from models.models_to_compare import MODELS_TO_COMPARE
from evaluation.evaluate import evaluate_model
from evaluation.compare_results import compare_results

def main():
    # Evaluate each model
    for i, model_name in enumerate(MODELS_TO_COMPARE):
        output_path = f"results/model{i+1}_results.json"
        evaluate_model(model_name, output_path=output_path)

    # Compare the results of the two models
    compare_results(
        model1_path="results/model1_results.json",
        model2_path="results/model2_results.json",
        output_path="results/comparison_results.txt"
    )

if __name__ == "__main__":
    main()