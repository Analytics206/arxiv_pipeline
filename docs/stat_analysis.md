# 🧠 Descriptive & Inferential Statistics
## 1. Z-Score
- Use: Identify outliers in summary_length, PageRank scores, or embedding-based metrics.
- Example: Detect unusually influential papers (e.g., PageRank Z-score > 3).

## 2. T-Statistic / T-Test
- Use: Compare means between two groups.
- Example:
    - Are papers in Cluster A longer than in Cluster B (summary_length)?
    - Do papers authored by authors with high PageRank have more pages?

## 3. ANOVA (Analysis of Variance)
- Use: Compare multiple group means.
- Example:
    - Compare average PageRank or summary_length across categories (e.g., NLP vs CV vs AI).

## 4. Chi-Square Test
- Use: Check for independence between categorical variables.
- Example:
    - Are cluster assignments independent of category?
    - Are high PageRank scores more frequent in certain regions?

# 📈 Correlation & Association
## 5. Pearson/Spearman Correlation
- Use: Measure linear (Pearson) or rank-based (Spearman) relationships.
- Example:
    - Correlation between summary length and PageRank.
    - Correlation between total_pages and embedding cluster ID.

## 6. Point-Biserial Correlation
- Use: Between binary variable and continuous value.
- Example:
Correlate whether a paper was cited (yes/no) with its summary_length or vector norm.

# 🧩 Dimensionality & Embedding Analysis
## 7. Cosine Similarity & Distance Metrics
- Use: Measure semantic proximity in Qdrant.
- Example:
    - How different are clusters semantically?
    - Compare average distance to cluster centroid.

## 8. PCA / UMAP / t-SNE
- Use: Dimensionality reduction to visualize or cluster high-dimensional embedding data.
- Complement: You already used UMAP; PCA can help explain variance structure.

# 📊 Graph-Based Stats (Neo4j)
## 9. Graph Centrality Measures
- Use: Quantify influence or connectivity in the citation/author network.
- Examples:
     - PageRank: Authority
    - Betweenness: Gatekeepers
    - Closeness: Information spread

## 10. Community Detection
- Use: Find clusters of co-citing papers or collaborative authors.
- Methods: Louvain, Label Propagation (GDS in Neo4j)

# 🧪 Advanced Modeling Techniques
## 11. Regression Models
- Use: Predict paper influence or clustering based on metadata.
- Examples:
    - Linear regression: summary_length → PageRank
    - Logistic regression: Predict high influence (PageRank > threshold)

## 12. Survival Analysis
- Use: Estimate time until a paper gets cited.
- Might require timestamped citation graph and lifelines package.

