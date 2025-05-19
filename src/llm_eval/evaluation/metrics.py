from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
from nltk.translate.meteor_score import meteor_score
from rouge_score import rouge_scorer
from collections import Counter
import warnings

# Suppress the BLEU score warning
warnings.filterwarnings("ignore", message="The hypothesis contains 0 counts of 4-gram overlaps.")

def calculate_bleu(reference, generated, n_gram=2):  # Use 2-grams instead of 4-grams
    smoothing_function = SmoothingFunction().method1  # Apply smoothing
    return sentence_bleu(
        [reference.split()],
        generated.split(),
        weights=(1.0 / n_gram,) * n_gram,  # Equal weights for n-grams
        smoothing_function=smoothing_function
    )

# BLEU Score
def calculate_bleu(reference, generated, n_gram=4):
    smoothing_function = SmoothingFunction().method1
    return sentence_bleu([reference.split()], generated.split(), weights=(1.0 / n_gram,) * n_gram, smoothing_function=smoothing_function)

# METEOR Score
def calculate_meteor(reference, generated):
    return meteor_score([reference.split()], generated.split())

# ROUGE Score
def calculate_rouge(reference, generated):
    scorer = rouge_scorer.RougeScorer(['rouge1', 'rougeL'], use_stemmer=True)
    return scorer.score(reference, generated)

# Distinct-n (Diversity Metric)
def calculate_distinct_n(generated_texts, n=2):
    ngrams = []
    for text in generated_texts:
        words = text.split()
        ngrams.extend(zip(*[words[i:] for i in range(n)]))
    return len(set(ngrams)) / len(ngrams)

# Self-BLEU (Diversity Metric)
def calculate_self_bleu(generated_texts, n=4):
    scores = []
    for i in range(len(generated_texts)):
        reference = generated_texts[i].split()
        hypotheses = [text.split() for j, text in enumerate(generated_texts) if j != i]
        scores.append(sentence_bleu(hypotheses, reference))
    return sum(scores) / len(scores)

if __name__ == "__main__":
    reference = "The cat is on the mat."
    generated = "The cat is on the mat."
    print(f"BLEU Score (2-grams): {calculate_bleu(reference, generated, n_gram=2)}")

    generated = "A cat is sitting on the mat."
    print(f"BLEU Score (2-grams): {calculate_bleu(reference, generated, n_gram=2)}")

    generated = "The dog is in the house."
    print(f"BLEU Score (2-grams): {calculate_bleu(reference, generated, n_gram=2)}")