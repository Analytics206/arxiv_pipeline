import pandas as pd
import numpy as np
from top2vec import Top2Vec
import matplotlib.pyplot as plt
from typing import List, Dict, Tuple, Optional
import re
import seaborn as sns
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EnhancedTopicModeler:
    """Enhanced topic modeling for research papers using Top2Vec with better
    topic naming and evaluation metrics. Designed to work with ArXiv papers.
    
    This class provides:
    1. Enhanced preprocessing for scientific text
    2. Better topic naming using domain-specific heuristics
    3. Topic hierarchy generation
    4. Quality metrics and visualization
    5. MongoDB integration support
    """
    """
    Enhanced topic modeling for research papers using Top2Vec with better
    topic naming and evaluation metrics.
    """
    
    def __init__(self, 
                 min_count: int = 10,
                 speed: str = "learn",
                 workers: int = 8,
                 embedding_model: str = "universal-sentence-encoder"):
        """Initialize the EnhancedTopicModeler.
        
        Args:
            min_count: Minimum count of words to be included
            speed: Speed vs accuracy tradeoff ('learn', 'deep-learn', 'fast-learn')
            workers: Number of worker threads
            embedding_model: Which embedding model to use
        """
        self.min_count = min_count
        self.speed = speed
        self.workers = workers
        self.embedding_model = embedding_model
        self.logger = logging.getLogger(__name__)
        self.model = None
        self.topic_sizes = None
        self.topic_nums = None
        self.topic_words = None
        self.word_scores = None
        self.topic_scores = None
        
    def fit(self, documents: List[str], ids: Optional[List] = None) -> None:
        """
        Fit the model on the input documents.
        
        Args:
            documents: List of document texts (paper summaries)
            ids: Optional document IDs
        """
        self.logger.info(f"Fitting model on {len(documents)} documents")
        
        if not documents:
            raise ValueError("No documents provided for topic modeling.")
            
        # Clean text to improve topic modeling
        clean_docs = [self._clean_text(doc) for doc in documents]
        
        # Ensure we have enough documents for clustering
        if len(clean_docs) < 2:
            raise ValueError(f"Need at least 2 documents to fit Top2Vec model, got {len(clean_docs)}")
                
        try:
            # Configure model with parameters appropriate for small datasets if needed
            min_cluster_size = 2 if len(clean_docs) < 10 else 5
            min_samples = 1 if len(clean_docs) < 10 else 2
            
            self.logger.info(f"Creating Top2Vec model with {len(clean_docs)} documents")
            
            # Create Top2Vec model
            self.model = Top2Vec(
                documents=clean_docs,
                min_count=self.min_count,
                speed=self.speed,
                workers=self.workers,
                embedding_model=self.embedding_model,
                document_ids=ids,
                hdbscan_args={'min_cluster_size': min_cluster_size, 'min_samples': min_samples}
            )
            
            # Store topic info for later use
            self.logger.info("Getting topic sizes")
            self.topic_sizes, self.topic_nums = self.model.get_topic_sizes()
            
            # Get topics using the correct method: get_topics (NOT get_topic)
            self.logger.info("Getting topic words and scores using get_topics")
            try:
                # According to the documentation, get_topics returns three values:
                # topic_words, word_scores, topic_nums
                self.topic_words, self.word_scores, _ = self.model.get_topics(self.model.get_num_topics())
                
                # Calculate topic scores as mean of word scores
                self.topic_scores = [np.mean(scores) for scores in self.word_scores]
                
                self.logger.info(f"Successfully extracted {len(self.topic_words)} topics with words and scores")
            except Exception as topic_error:
                self.logger.error(f"Error getting topics: {str(topic_error)}")
                raise
                
            self.logger.info(f"Successfully fitted Top2Vec model with {len(self.topic_nums)} topics")
            
        except Exception as e:
            self.logger.error(f"Error in Top2Vec model fitting: {str(e)}")
            raise ValueError(f"Failed to fit Top2Vec model: {str(e)}. Please check your data or model parameters.")
        
    def _clean_text(self, text: str) -> str:
        """Clean text for better topic modeling."""
        if not text or not isinstance(text, str):
            return "empty document"
            
        # Convert to lowercase
        text = text.lower()
        
        # Remove URLs, emails, etc.
        text = re.sub(r'http\S+|www\S+|\S+@\S+|\S+\.com\S*', '', text)
        
        # Remove special characters but keep useful punctuation
        text = re.sub(r'[^\w\s\.,\-\:]', ' ', text)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Ensure document has minimum length
        if len(text.split()) < 5:
            text = text + " content document research"
        
        return text
    
    def get_enhanced_topics(self, num_words: int = 15) -> Tuple[List[List[str]], List[List[float]], List[float]]:
        """
        Get enhanced topics with more meaningful words.
        
        Args:
            num_words: Number of words per topic
            
        Returns:
            Tuple of (topic_words, word_scores, topic_scores)
        """
        if self.model is None:
            self.logger.error("Model not fitted yet")
            return [], [], []
            
        try:
            # Get all topics at once using get_topics
            self.logger.info(f"Getting enhanced topics with {num_words} words per topic")
            all_words, all_scores, _ = self.model.get_topics(num_words=num_words)
            
            # Calculate topic scores as mean of word scores
            topic_scores = [np.mean(scores) for scores in all_scores]
            
            return all_words, all_scores, topic_scores
            
        except Exception as e:
            self.logger.error(f"Error in get_enhanced_topics: {str(e)}")
            # Return empty results if there's an error to prevent pipeline failure
            return [], [], []
    
    def get_document_topics(self) -> Tuple[List[int], List[float]]:
        """
        Get topic assignments for all documents.
        
        Returns:
            Tuple of (document_topics, document_topic_probs)
        """
        try:
            if self.model is None:
                self.logger.error("Model not fitted yet")
                return [], []
            
            # Check if we have any topics
            if not hasattr(self.model, 'get_num_topics') or self.model.get_num_topics() == 0:
                self.logger.warning("Model has no topics, returning empty assignments")
                return [], []
                
            # The get_documents_topics method might return different formats
            # or more than 2 values, so we need to handle it carefully
            self.logger.info("Getting document topics")
            try:
                # Try to get topics with proper unpacking
                result = self.model.get_documents_topics(
                    doc_ids=self.model.document_ids, 
                    num_topics=1  # Get only the most relevant topic
                )
                
                # Handle different return formats
                if isinstance(result, tuple):
                    # If it's a tuple, use the first two elements
                    if len(result) >= 2:
                        topics, probs = result[0], result[1]
                    else:
                        self.logger.error(f"Unexpected tuple length from get_documents_topics: {len(result)}")
                        return [], []
                else:
                    self.logger.error(f"Unexpected return type from get_documents_topics: {type(result)}")
                    return [], []
                    
            except Exception as topic_error:
                self.logger.error(f"Error in get_documents_topics: {str(topic_error)}")
                return [], []
            
            # Process the topics and probabilities for consistent format
            doc_topics = []
            doc_probs = []
            
            try:
                # Check if topics and probs are lists/arrays of single values or lists
                if len(topics) > 0:
                    # Check the structure of the first element to determine format
                    if isinstance(topics[0], (list, np.ndarray)):
                        # Format is list of lists
                        for t, p in zip(topics, probs):
                            if len(t) > 0:
                                doc_topics.append(int(t[0]))  # Take the first (most relevant) topic
                                doc_probs.append(float(p[0]))  # Take the corresponding probability
                            else:
                                doc_topics.append(-1)  # No topic
                                doc_probs.append(0.0)  # Zero probability
                    else:
                        # Format is flat list
                        for t, p in zip(topics, probs):
                            doc_topics.append(int(t))
                            doc_probs.append(float(p))
            except Exception as format_error:
                self.logger.error(f"Error processing topic format: {str(format_error)}")
                return [], []
            
            self.logger.info(f"Got topics for {len(doc_topics)} documents")
            return doc_topics, doc_probs
            
        except Exception as e:
            self.logger.error(f"Error getting document topics: {str(e)}")
            # Return empty lists instead of raising an exception
            return [], []

    
    def get_hierarchical_topics(self, num_topics: Optional[int] = None) -> Dict:
        """
        Create hierarchical topic representation.
        
        Args:
            num_topics: Target number of topics or None to auto-determine
            
        Returns:
            Dictionary with hierarchy information
        """
        if num_topics is None:
            # Auto-determine a reasonable number based on document count
            doc_count = len(self.model.document_ids)
            num_topics = max(5, min(30, int(np.sqrt(doc_count) / 2)))
        
        # Generate hierarchical topics
        hierarchy = {}
        try:
            # Get the hierarchical topic reduction
            hierarchical_topics = self.model.hierarchical_topic_reduction(num_topics)
            hierarchy = {
                'num_topics': num_topics,
                'hierarchical_topics': hierarchical_topics
            }
        except Exception as e:
            print(f"Error generating hierarchical topics: {e}")
        
        return hierarchy
    
    def print_topic_report(self, min_probability: float = 0.1) -> pd.DataFrame:
        """
        Print a comprehensive topic report similar to BERTopic.
        
        Args:
            min_probability: Minimum probability threshold
            
        Returns:
            DataFrame with topic report
        """
        doc_topics, doc_probs = self.get_document_topics()
        
        # Count documents by topic
        topic_counts = {}
        topic_avg_probs = {}
        
        for topic, prob in zip(doc_topics, doc_probs):
            if prob >= min_probability:
                topic_counts[topic] = topic_counts.get(topic, 0) + 1
                topic_avg_probs[topic] = topic_avg_probs.get(topic, []) + [prob]
        
        # Convert to averages
        for topic in topic_avg_probs:
            topic_avg_probs[topic] = np.mean(topic_avg_probs[topic])
        
        # Create topic names
        topic_names = {}
        for topic in range(self.model.get_num_topics()):
            words = self.topic_words[topic][:4]
            topic_names[topic] = f"{topic}_{words[0]}_{words[1]}_{words[2]}_{words[3]}"
        
        # Create dataframe
        report_data = []
        for topic in sorted(topic_counts.keys(), key=lambda x: topic_counts[x], reverse=True):
            report_data.append({
                'Topic ID': topic,
                'Count': topic_counts[topic],
                'Avg Prob': round(topic_avg_probs[topic], 4),
                'Topic Name': topic_names[topic]
            })
        
        # Add topic -1 for uncategorized docs
        uncat_count = len(doc_topics) - sum(topic_counts.values())
        if uncat_count > 0:
            report_data.append({
                'Topic ID': -1,
                'Count': uncat_count,
                'Avg Prob': 0.0,
                'Topic Name': "-1_uncategorized"
            })
        
        df = pd.DataFrame(report_data)
        
        # Print report in a format similar to BERTopic
        print("Topic ID   Count    Avg Prob   Topic Name")
        print("-" * 80)
        for _, row in df.iterrows():
            print(f"{row['Topic ID']:<10} {row['Count']:<8} {row['Avg Prob']:<10} {row['Topic Name']}")
        
        return df

    def visualize_topics(self, figsize=(12, 10)):
        """
        Visualize topics in a 2D space.
        """
        # Get topic vectors
        topic_vectors = self.model.topic_vectors
        
        # Use UMAP to reduce to 2D (Top2Vec already uses UMAP internally)
        # Here we'll use the existing topic vectors
        try:
            # Get UMAP from Top2Vec if available
            umap_model = self.model.umap_model
            reduced_topics = umap_model.transform(topic_vectors)
            
            # Plot
            plt.figure(figsize=figsize)
            plt.scatter(reduced_topics[:, 0], reduced_topics[:, 1], 
                      s=[size/10 for size in self.topic_sizes], alpha=0.7)
            
            # Add topic names
            for i, (x, y) in enumerate(zip(reduced_topics[:, 0], reduced_topics[:, 1])):
                words = self.topic_words[i][:2]
                plt.annotate(f"T{i}: {words[0]}, {words[1]}", 
                           (x, y), 
                           fontsize=8, 
                           alpha=0.8)
                
            plt.title('Topic Visualization')
            plt.xlabel('Dimension 1')
            plt.ylabel('Dimension 2')
            plt.tight_layout()
            plt.show()
        except Exception as e:
            print(f"Error visualizing topics: {e}")

    def get_topic_word_matrix(self, num_words=100):
        """
        Create a topic-word matrix for additional analysis.
        """
        all_words = set()
        for words in self.topic_words:
            all_words.update(words[:num_words])
        
        all_words = sorted(list(all_words))
        word_index = {word: i for i, word in enumerate(all_words)}
        
        # Create matrix
        matrix = np.zeros((len(self.topic_words), len(all_words)))
        
        for topic_idx, (words, scores) in enumerate(zip(self.topic_words, self.word_scores)):
            for word, score in zip(words[:num_words], scores[:num_words]):
                matrix[topic_idx, word_index[word]] = score
                
        return matrix, all_words

    def reassign_outliers(self, min_probability=0.3):
        """
        Try to reassign outlier documents to the closest topic.
        
        Returns:
            New document-topic assignments
        """
        doc_topics, doc_probs = self.get_document_topics()
        
        # Find documents with low probability
        low_prob_indices = [i for i, p in enumerate(doc_probs) if p < min_probability]
        
        if not low_prob_indices:
            return doc_topics, doc_probs
            
        # Get documents
        low_prob_docs = [self.model.documents[i] for i in low_prob_indices]
        
        # Get document vectors
        doc_vectors = self.model.document_vectors[low_prob_indices]
        
        # For each document, find the most similar topic
        new_assignments = []
        new_probs = []
        
        for vec in doc_vectors:
            # Compute similarity to each topic vector
            similarities = []
            for topic_vec in self.model.topic_vectors:
                # Use cosine similarity
                similarity = np.dot(vec, topic_vec) / (np.linalg.norm(vec) * np.linalg.norm(topic_vec))
                similarities.append(similarity)
                
            # Get best topic
            best_topic = np.argmax(similarities)
            best_prob = similarities[best_topic]
            
            new_assignments.append(best_topic)
            new_probs.append(best_prob)
        
        # Update assignments
        for i, idx in enumerate(low_prob_indices):
            doc_topics[idx] = new_assignments[i]
            doc_probs[idx] = new_probs[i]
            
        return doc_topics, doc_probs
        
    def topic_keywords_table(self, num_words=10):
        """
        Print a nice table of topic keywords.
        """
        df_topics = pd.DataFrame()
        
        # Add topic size info
        df_topics['Topic'] = [f"Topic {i}" for i in range(len(self.topic_words))]
        df_topics['Size'] = self.topic_sizes
        
        # Add keywords
        for i in range(num_words):
            df_topics[f'Word {i+1}'] = [
                words[i] if i < len(words) else "" 
                for words in self.topic_words
            ]
            
        return df_topics

    def document_topic_matrix(self, documents, num_topics=10):
        """
        Create a document-topic matrix for the given documents.
        
        Args:
            documents: List of document texts to analyze
            num_topics: Number of topics to consider per document
            
        Returns:
            Document-topic matrix and topic names
        """
        # Get document vectors
        doc_vectors = self.model.embed(documents)
        
        # Calculate similarity to each topic
        doc_topic_matrix = np.zeros((len(documents), self.model.get_num_topics()))
        
        for i, doc_vec in enumerate(doc_vectors):
            for topic_idx, topic_vec in enumerate(self.model.topic_vectors):
                # Cosine similarity
                similarity = np.dot(doc_vec, topic_vec) / (np.linalg.norm(doc_vec) * np.linalg.norm(topic_vec))
                doc_topic_matrix[i, topic_idx] = similarity
        
        # Normalize to sum to 1
        row_sums = doc_topic_matrix.sum(axis=1)
        doc_topic_matrix = doc_topic_matrix / row_sums[:, np.newaxis]
        
        # Create topic names
        topic_names = [f"T{i}: {', '.join(words[:2])}" for i, words in enumerate(self.topic_words)]
        
        return doc_topic_matrix, topic_names

# Example usage
def example_classification(documents):
    """Example classification workflow"""
    
    # Initialize and fit the model
    topic_model = EnhancedTopicModeler(
        min_count=5,
        speed="learn",  # Use "deep-learn" for better but slower results
        workers=8,
        embedding_model="universal-sentence-encoder"  # Good for scientific texts
    )
    
    # Fit the model
    print("Fitting model...")
    topic_model.fit(documents)
    
    # Print topic report
    print("\nTopic Report:")
    topic_report = topic_model.print_topic_report(min_probability=0.1)
    
    # Try to reassign outliers
    print("\nReassigning outliers...")
    doc_topics, doc_probs = topic_model.reassign_outliers(min_probability=0.3)
    
    # Print more detailed topic information
    print("\nDetailed Topic Keywords:")
    topic_keywords = topic_model.topic_keywords_table(num_words=10)
    print(topic_keywords)
    
    # Visualize topics
    print("\nVisualizing topics...")
    topic_model.visualize_topics()
    
    return topic_model, topic_report