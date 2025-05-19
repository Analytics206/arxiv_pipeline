# Model Evaluation Tools

This table summarizes common model evaluation tools, how to interpret their scores, and common pitfalls.

| Evaluation Tool       | What It Measures                                                                 | Score Range       | Precision                                | How to Read the Score                                                                                     | How NOT to Read the Score                                                                                   |
|-----------------------|---------------------------------------------------------------------------------|------------------|------------------------------------------|-----------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------|
| **BLEU**             | Overlap of n-grams (word sequences) between generated and reference texts.      | 0 to 1           | Typically 2-4 decimal places (e.g., 0.75) | - Higher scores (closer to 1) indicate better overlap.<br>- Scores are typically between 0 and 1.         | - Don’t assume high scores mean the text is fluent or correct.<br>- Don’t ignore low scores for creative text. |
| **ROUGE**            | Overlap of n-grams or word pairs between generated and reference texts.         | 0 to 1           | Typically 2-4 decimal places (e.g., 0.85) | - Higher scores (closer to 1) indicate better overlap.<br>- Focuses on recall (coverage of reference text). | - Don’t assume high scores mean the text is informative.<br>- Don’t ignore low scores for paraphrased text.    |
| **METEOR**           | Semantic similarity and word overlap between generated and reference texts.      | 0 to 1           | Typically 2-4 decimal places (e.g., 0.92) | - Higher scores (closer to 1) indicate better semantic alignment.<br>- Accounts for synonyms and stemming.   | - Don’t assume high scores mean perfect fluency.<br>- Don’t ignore low scores for diverse phrasing.            |
| **BERTScore**        | Semantic similarity using embeddings from models like BERT.                     | 0 to 1           | Typically 2-4 decimal places (e.g., 0.88) | - Higher scores (closer to 1) indicate better semantic alignment.<br>- Captures paraphrasing and meaning.    | - Don’t assume high scores mean exact word overlap.<br>- Don’t ignore low scores for factual correctness.      |
| **Perplexity**       | How well the model predicts the next word in a sequence.                        | 0 to ∞ (lower is better) | Typically 1-3 decimal places (e.g., 25.3) | - Lower scores indicate better performance.<br>- Measures model confidence.                                | - Don’t assume low perplexity means high-quality text.<br>- Don’t ignore high perplexity for creative text.    |
| **Human Evaluation** | Subjective quality of generated text (fluency, coherence, relevance, correctness). | Depends on scale (e.g., 1 to 5) | Typically 1 decimal place (e.g., 4.2)    | - Higher scores (e.g., on a scale of 1 to 5) indicate better quality.<br>- Captures nuances automated metrics miss. | - Don’t assume human scores are always objective.<br>- Don’t ignore biases or inconsistencies in human judgment. |
| **Distinct-n**       | Diversity of n-grams in generated text.                                          | 0 to 1           | Typically 2-4 decimal places (e.g., 0.45) | - Higher scores indicate more diverse text.<br>- Encourages creativity and variety.                         | - Don’t assume high diversity means high quality.<br>- Don’t ignore low diversity for task-specific outputs.    |
| **Self-BLEU**        | Similarity of generated text to itself (used to measure diversity).              | 0 to 1           | Typically 2-4 decimal places (e.g., 0.35) | - Lower scores indicate more diverse text.<br>- Encourages less repetitive outputs.                          | - Don’t assume low Self-BLEU means high quality.<br>- Don’t ignore high Self-BLEU for coherent outputs.        |
| **Task-Specific Metrics** (e.g., F1 for QA) | Accuracy of task-specific outputs (e.g., exact match for QA). | 0 to 1           | Typically 2-4 decimal places (e.g., 0.78) | - Higher scores indicate better task performance.<br>- Tailored to specific tasks (e.g., QA, summarization). | - Don’t assume high scores mean general-purpose quality.<br>- Don’t ignore low scores for creative tasks.       |

---

## Key Notes on Score Ranges and Precision
1. **Score Ranges**:
   - Most metrics (e.g., BLEU, ROUGE, METEOR, BERTScore, Distinct-n, Self-BLEU, F1) range from **0 to 1**, where higher scores indicate better performance.
   - **Perplexity** ranges from **0 to ∞**, where lower scores indicate better performance.
   - **Human Evaluation** typically uses a custom scale (e.g., 1 to 5).

2. **Precision**:
   - Most scores are reported with **2-4 decimal places** for precision.
   - **Perplexity** is often reported with **1-3 decimal places**.
   - **Human Evaluation** scores are typically reported with **1 decimal place**.

---

## How NOT to Use These Scores
- **Don’t rely on a single metric**: Each metric has limitations, so use a combination of metrics for a more complete evaluation.
- **Don’t ignore context**: A high score doesn’t always mean the text is good (e.g., BLEU can’t measure factual correctness).
- **Don’t assume high scores mean perfection**: Even with high scores, the text might have issues like bias, incoherence, or factual errors.
- **Don’t ignore low scores for creative text**: Creative or paraphrased text might score low on BLEU/ROUGE but still be high quality.

---

## Example Workflow for Evaluating an LLM
1. **Start with automated metrics** (e.g., BLEU, ROUGE, BERTScore) to get a quick assessment.
2. **Check diversity** (e.g., Distinct-n, Self-BLEU) to ensure the model isn’t repeating itself.
3. **Validate with human evaluation** for subjective quality (e.g., fluency, coherence).
4. **Use task-specific metrics** if applicable (e.g., F1 for QA, ROUGE for summarization).