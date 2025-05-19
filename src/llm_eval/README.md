# LLM Evaluation Project

This project demonstrates how to evaluate a Large Language Model (LLM) using common metrics like **BLEU**, **ROUGE**, and **BERTScore**. It also includes scripts for loading a pre-trained model, generating responses, and evaluating the quality of generated text.

---

## Table of Contents
1. [Project Overview](#project-overview)
2. [Folder Structure](#folder-structure)
3. [Installation](#installation)
4. [Usage](#usage)
5. [Evaluation Metrics](#evaluation-metrics)
6. [Example Output](#example-output)
7. [Limitations](#limitations)
8. [Useful Resources](#useful-resources)

## Project Overview
The goal of this project is to:
- Load a pre-trained LLM (e.g., Hugging Face's `DialoGPT`).
- Generate responses to input prompts.
- Evaluate the quality of generated responses using metrics like BLEU, ROUGE, and BERTScore.
- Understand the strengths and limitations of these metrics.

## Folder Structure
llm-evaluation/
│
├── test_data/
│ └── test_data.json # Test dataset (input prompts and reference responses)
│
├── models/
│ └── load_model.py # Script to load the model and tokenizer
│
├── evaluation/
│ ├── evaluate.py # Script to evaluate the model
│ └── metrics.py # Script to compute evaluation metrics
│
├── results/
│ └── evaluation_results.json # Output file for evaluation results
│
├── utils/
│ └── helpers.py # Helper functions (e.g., preprocessing)
│
├── evaluate_llm_models.py # Main script to run the entire pipeline
│
└── requirements.txt # List of dependencies

## Installation
1. Clone this repository:
   ```bash
   git clone https://github.com/your-username/llm-evaluation.git
   cd llm-evaluation

python3 -m venv myenv
source myenv/bin/activate

# windows
python -m venv myenv
.\myenv\Scripts\Activate.ps1

pip install -r requirements.txt

python -c "import nltk; nltk.download('wordnet'); nltk.download('omw-1.4')"

## Usage

### Changing Models to Evaluate
To change which models are evaluated, edit the `MODELS_TO_COMPARE` list in `models/models_to_compare.py`. You can add or remove model identifiers as needed. For example:

```python
MODELS_TO_COMPARE = [
    "microsoft/DialoGPT-large",  # Default large model
    "microsoft/DialoGPT-medium", # Default medium model
    "gpt2",                    # Example: Adding GPT-2
    "facebook/opt-350m"         # Example: Adding OPT-350M
]
```

Supported models are those available in the Hugging Face model hub or local paths to pre-downloaded models.

### Preparing Test Data
Add your input prompts and reference responses to `test_data/test_data.json`.

### Running the Evaluation Pipeline
```bash
python evaluate_llm_models.py
```

### Checking Results
The evaluation results will be saved in the `results/` directory:
- Individual model results: `model1_results.json`, `model2_results.json`, etc.
- Comparison results: `comparison_results.txt` (when comparing 2+ models)

## System Metadata

The project includes a metadata generator that creates documentation about the system's structure and dependencies. This is useful for understanding the codebase architecture and module relationships.

### Generating Metadata

To generate system metadata for the entire project:

```bash
# From the project root directory
python metadata_generator.py . -o system_metadata.yaml

# Or for just the llm_eval module:
python metadata_generator.py src/llm_eval -o llm_eval_metadata.yaml
```

### Metadata Contents

The generated `system_metadata.yaml` file includes:
- List of all Python modules
- Entry points and their dependencies
- External library dependencies
- Module relationships and component structure

### Usage

The metadata is primarily used for:
- Documentation generation
- System architecture analysis
- Dependency visualization
- Codebase understanding and onboarding

## Evaluation Metrics
This project uses the following metrics to evaluate the model:

Metric	Description	Score Range
BLEU	Measures n-gram overlap between generated and reference texts.	0 to 1 (higher is better)
ROUGE	Measures word sequence overlap between generated and reference texts.	0 to 1 (higher is better)
BERTScore	Measures semantic similarity using embeddings from models like BERT.	0 to 1 (higher is better)
Perplexity	Measures how well the model predicts the next word in a sequence.	0 to ∞ (lower is better)
Limitations

Reference Quality:
Metrics assume the reference text is perfect. If the reference is flawed, the scores may be misleading.

Semantic Understanding:
Metrics like BLEU and ROUGE focus on word overlap, not semantic meaning. Use BERTScore for semantic evaluation.

Creativity:
Metrics may penalize creative or diverse responses that don’t match the reference text.
Useful Resources
Hugging Face Transformers Documentation:
https://huggingface.co/docs/transformers/index

NLTK Documentation:
https://www.nltk.org/

BERTScore Paper:
https://arxiv.org/abs/1904.09675

BLEU Score Explanation:
https://en.wikipedia.org/wiki/BLEU

ROUGE Score Explanation:
https://en.wikipedia.org/wiki/ROUGE_(metric)

Contributing
Feel free to contribute to this project by:
Adding new evaluation metrics.
Improving the test dataset.
Fixing bugs or adding new features.
