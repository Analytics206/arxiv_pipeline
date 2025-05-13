# 📊 1. Descriptive Statistics Dashboard
## ✅ Use: Provide summary metrics across all data sources
## 📈 Techniques:

- Count of papers by category (MongoDB)
- Mean/median/min/max of:
    - summary_length
    - total_pages
    - PageRank score
- Number of clusters from Qdrant
- Most common authors or tools in metadata
### 📌 User benefit: Immediate sense of dataset size, spread, and structure

# 📊 2. Distribution Plots
## ✅ Use: Let users visually understand data range and shape
### 📈 Techniques:
- Histograms: of summary_length, total_pages, PageRank
- Box plots: per category or cluster to show variance
- Violin plots: show distribution + density (optional)
### 📌 User benefit: Quickly see skewed data, outliers, dense regions

# 📦 3. Z-Scores for Outlier Detection
## ✅ Use: Flag unusually long/short summaries or high influence papers
## 📈 Technique:
```python
from scipy.stats import zscore
mongo_df['z_summary'] = zscore(mongo_df['summary_length'])
Highlight papers where |z| > 2
```
### 📌 User benefit: Understand which documents are statistical anomalies

# 📚 4. Top-N Lists
## ✅ Use: Show most influential or detailed documents
### 📈 Examples:
- Top 10 papers by PageRank
- Top 10 longest summaries
- Top authors with most papers
### 📌 User benefit: Surface standout documents and contributors

# 📆 5. Time Series Aggregation (Basic Trend)
## ✅ Use: Let users see data evolution over time
### 📈 Technique:

- Group by processed_date (monthly/weekly)
- Plot counts or average summary_length per period
### 📌 User benefit: Understand trends in submissions or processing

# 📘 6. Category & Cluster Cross Tab
## ✅ Use: Explore how semantic clusters relate to labeled categories
### 📈 Technique:
```python
pd.crosstab(merged_df['category'], merged_df['cluster'])
```
### 📌 User benefit: Identify if certain categories dominate specific clusters

# 📊 7. Simple Correlations
## ✅ Use: Highlight basic relationships
### 📈 Technique:
```python
merged_df[['summary_length', 'total_pages', 'score']].corr()
```
### 📌 User benefit: Do longer papers tend to be more influential?

# 🧠 8. Embedding Norm Histogram (Qdrant)
## ✅ Use: Show spread of semantic vector magnitudes
### 📈 Technique:
```python
qdrant_df['norm'] = qdrant_df['vector'].apply(lambda x: np.linalg.norm(x))
qdrant_df['norm'].hist()
```
### 📌 User benefit: Understand spread of semantic representation size

# 🧩 9. Cluster Size Table
## ✅ Use: Show distribution of papers across semantic clusters
### 📈 Technique:
```python
cluster_counts = merged_df['cluster'].value_counts()
print(cluster_counts)
```
### 📌 User benefit: Know how many groups exist and their size

# 🧾 10. "Did You Know?" Facts (Automated Insights)
## ✅ Use: Generate user-friendly insight summaries
### 📈 Examples:

- “📌 The largest cluster contains 45 papers.”
- “📌 The average PageRank of CV papers is 0.134.”
- “📌 Only 8 papers have a summary longer than 1000 words.”
### 📌 User benefit: Surface interesting facts without effort