import logging
import argparse
import yaml
import os
from datetime import datetime, timezone
UTC = timezone.utc
from typing import Dict, Any, List
from tqdm import tqdm

from pymongo import MongoClient, UpdateOne
from src.storage.mongo import MongoStorage
from src.pipeline.top2vec import EnhancedTopicModeler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

import pandas as pd
from top2vec import Top2Vec
import nltk
from nltk.corpus import stopwords
import re
from typing import List, Dict, Any
import numpy as np
import matplotlib.pyplot as plt
from sklearn.metrics import silhouette_score
from collections import Counter

# Download stopwords if needed
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

def preprocess_text(text: str) -> str:
    """
    Preprocess text for better topic modeling
    """
    # Convert to lowercase
    text = text.lower()
    
    # Remove URLs
    text = re.sub(r'http\S+', '', text)
    
    # Remove special characters but keep useful punctuation
    text = re.sub(r'[^\w\s\.\,\-\:]', ' ', text)
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Remove scientific/math/technical stop phrases
    stop_phrases = [
        'et al', 'proposed method', 'proposed approach', 'experimental results',
        'fig', 'figure', 'table', 'eq', 'equation', 'section', 'chapter',
        'we propose', 'we present', 'we introduce', 'in this paper',
        'experimental results show', 'paper proposes', 'proposed algorithm'
    ]
    
    for phrase in stop_phrases:
        text = text.replace(phrase, '')
    
    return text

def classify_papers(summaries: List[str], doc_ids: List[Any] = None) -> Dict:
    """
    Classify research papers into topics using Top2Vec
    
    Args:
        summaries: List of paper summaries
        doc_ids: Optional document IDs
        
    Returns:
        Dictionary with model and results
    """
    print(f"Processing {len(summaries)} paper summaries...")
    
    # Preprocess summaries
    processed_summaries = [preprocess_text(summary) for summary in summaries]
    
    # Filter out very short summaries
    valid_indices = [i for i, summary in enumerate(processed_summaries) if len(summary.split()) > 20]
    filtered_summaries = [processed_summaries[i] for i in valid_indices]
    
    # Handle document IDs if provided
    if doc_ids:
        filtered_ids = [doc_ids[i] for i in valid_indices]
    else:
        filtered_ids = list(range(len(filtered_summaries)))
    
    print(f"Training with {len(filtered_summaries)} valid summaries...")
    
    # Create Top2Vec model with appropriate settings for research papers
    model = Top2Vec(
        documents=filtered_summaries,
        speed="deep-learn",          # Better accuracy for scientific text
        workers=8,                   # Adjust based on your CPU cores
        min_count=5,                 # Minimum word count
        document_ids=filtered_ids,   # Use provided IDs if available
        embedding_model="universal-sentence-encoder"  # Good for scientific texts
    )
    
    # Get topic information
    topic_sizes, topic_nums = model.get_topic_sizes()
    
    # Get number of topics (excluding -1 which is noise)
    num_topics = len([t for t in topic_nums if t != -1])
    print(f"Found {num_topics} distinct topics")
    
    # Get topic words (more words for better topic characterization)
    topic_words = {}
    topic_word_scores = {}
    
    for topic_num in topic_nums:
        if topic_num != -1:  # Skip noise topic
            words, word_scores, _ = model.get_topic(topic_num, 30)
            topic_words[topic_num] = words
            topic_word_scores[topic_num] = word_scores
    
    # Get document-topic assignments
    doc_topics, doc_probs = model.get_documents_topics(
        doc_ids=model.document_ids,
        num_topics=1,  # Get most relevant topic
        reduced=False  # Use full topic space
    )
    
    # Extract primary topic for each document
    primary_topics = [t[0] for t in doc_topics]
    primary_probs = [p[0] for p in doc_probs]
    
    # Create report data
    report_data = []
    
    # Add topic counts and probabilities
    topic_counter = Counter(primary_topics)
    for topic in sorted(topic_counter.keys()):
        # Calculate average probability for this topic
        topic_indices = [i for i, t in enumerate(primary_topics) if t == topic]
        avg_prob = np.mean([primary_probs[i] for i in topic_indices])
        
        # Create descriptive topic name using most relevant words
        if topic in topic_words:
            key_words = topic_words[topic][:4]
            topic_name = f"{topic}_{key_words[0]}_{key_words[1]}_{key_words[2]}_{key_words[3]}"
        else:
            topic_name = f"{topic}_misc"
        
        report_data.append({
            "Topic ID": topic,
            "Count": topic_counter[topic],
            "Avg Prob": round(avg_prob, 4),
            "Topic Name": topic_name
        })
    
    # Sort by count descending
    report_data = sorted(report_data, key=lambda x: x["Count"], reverse=True)
    
    # Print report
    print("\nTopic Classification Results:")
    print("Topic ID   Count    Avg Prob   Topic Name")
    print("-" * 80)
    for row in report_data:
        print(f"{row['Topic ID']:<10} {row['Count']:<8} {row['Avg Prob']:<10} {row['Topic Name']}")
    
    # Return results
    results = {
        "model": model,
        "report_data": report_data,
        "topic_words": topic_words,
        "topic_word_scores": topic_word_scores,
        "doc_topics": primary_topics,
        "doc_probs": primary_probs,
        "filtered_ids": filtered_ids
    }
    
    return results

def get_topic_hierarchy(model, num_topics=None):
    """
    Get hierarchical topic representation to improve interpretability
    
    Args:
        model: Trained Top2Vec model
        num_topics: Number of topics to reduce to (None for auto-determination)
    """
    if num_topics is None:
        # Determine a reasonable number based on document count
        doc_count = len(model.document_ids)
        # Square root heuristic works well for topic count
        num_topics = max(5, min(30, int(np.sqrt(doc_count) / 2)))
    
    print(f"Generating hierarchical topic representation with {num_topics} topics...")
    
    try:
        # Get hierarchical topics
        hierarchy = model.hierarchical_topic_reduction(num_topics)
        
        # Print hierarchical topic information
        print("\nHierarchical Topic Structure:")
        for i, (topic_num, reduced_num) in enumerate(hierarchy):
            # Get words for original topic
            words, _, _ = model.get_topic(topic_num)
            # Get words for reduced topic
            reduced_words, _, _ = model.get_topic_reduction(reduced_num)
            
            print(f"Original Topic {topic_num} ({words[0]}, {words[1]}) → " +
                  f"Reduced Topic {reduced_num} ({reduced_words[0]}, {reduced_words[1]})")
        
        return hierarchy
    except Exception as e:
        print(f"Error generating hierarchical topics: {e}")
        return None

def plot_topic_distribution(report_data):
    """
    Plot topic distribution as a bar chart
    """
    topics = [row["Topic Name"].split('_')[0] + ": " + '_'.join(row["Topic Name"].split('_')[1:3]) 
              for row in report_data[:15]]  # Limit to top 15 topics
    counts = [row["Count"] for row in report_data[:15]]
    
    plt.figure(figsize=(12, 8))
    bars = plt.bar(range(len(topics)), counts)
    plt.xticks(range(len(topics)), topics, rotation=45, ha='right')
    plt.title('Distribution of Papers Across Topics')
    plt.xlabel('Topic')
    plt.ylabel('Number of Papers')
    plt.tight_layout()
    
    # Add count labels on top of bars
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                 f'{height}', ha='center', va='bottom')
    
    plt.show()

def evaluate_topic_quality(model, doc_topics, doc_probs):
    """
    Evaluate topic quality using various metrics
    """
    # Calculate average document-topic probability (higher is better)
    avg_prob = np.mean(doc_probs)
    
    # Calculate topic coherence (approximation)
    coherence_scores = []
    
    for topic in range(model.get_num_topics()):
        words, word_scores, _ = model.get_topic(topic, 12)
        # Use word scores as approximation of coherence
        coherence_scores.append(np.mean(word_scores))
    
    avg_coherence = np.mean(coherence_scores)
    
    # Count documents with high confidence (prob > 0.5)
    high_conf_docs = sum(1 for p in doc_probs if p > 0.5)
    high_conf_percentage = high_conf_docs / len(doc_probs) * 100
    
    print("\nTopic Quality Metrics:")
    print(f"Average document-topic probability: {avg_prob:.4f}")
    print(f"Average topic coherence score: {avg_coherence:.4f}")
    print(f"Percentage of documents with high confidence: {high_conf_percentage:.2f}%")
    
    return {
        "avg_probability": avg_prob,
        "avg_coherence": avg_coherence,
        "high_confidence_percentage": high_conf_percentage
    }

def load_config(config_path: str) -> Dict[str, Any]:
    """Load configuration settings from a YAML file.
    
    Args:
        config_path (str): Path to the YAML configuration file.
        
    Returns:
        Dict[str, Any]: Dictionary containing configuration settings.
        
    Raises:
        FileNotFoundError: If the config file doesn't exist.
        yaml.YAMLError: If the YAML file is malformed.
    """
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def is_docker() -> bool:
    """Detect if running inside a Docker container."""
    try:
        with open('/proc/1/cgroup', 'r') as f:
            return 'docker' in f.read()
    except:
        return False

def get_mongo_uri(config: Dict[str, Any]) -> str:
    """Get the appropriate MongoDB URI based on environment and configuration."""
    mongo_uri = os.environ.get('MONGO_URI')
    if mongo_uri:
        return mongo_uri
        
    if is_docker():
        return config['top2vec']['mongo']['connection_string']
    return config['top2vec']['mongo']['connection_string_local']

def build_mongo_query(config: Dict[str, Any]) -> Dict:
    """Build a MongoDB query based on configuration filters."""
    query = {}
    
    # Add category filter
    if config['top2vec']['categories']:
        query['categories'] = {'$in': config['top2vec']['categories']}
    
    # Add date filter if enabled
    if config['top2vec'].get('date_filter', {}).get('enabled', False):
        date_filter = config['top2vec']['date_filter']
        date_query = {}
        
        if date_filter.get('start_date'):
            date_query['$gte'] = date_filter['start_date']
        if date_filter.get('end_date'):
            date_query['$lte'] = date_filter['end_date']
            
        if date_query:
            query['published'] = date_query
    
    return query

def process_batch(papers: List[Dict], topic_model: EnhancedTopicModeler, mongo_collection) -> int:
    """Process a batch of papers and store topics in MongoDB.
    
    Args:
        papers: List of paper documents from MongoDB
        topic_model: Trained Top2Vec model
        mongo_collection: MongoDB collection to store results
    
    Returns:
        int: Number of papers successfully processed
    """
    if not papers:
        logger.warning("Received empty batch of papers to process")
        return 0
        
    try:    
        # Get summaries and IDs
        summaries = [doc.get('summary', '') for doc in papers]
        paper_ids = [str(doc['_id']) for doc in papers]
        
        if len(paper_ids) != len(summaries):
            logger.error(f"Mismatch in paper_ids ({len(paper_ids)}) and summaries ({len(summaries)})")
            return 0
        
        # Get topic assignments
        doc_topics, doc_probs = topic_model.get_document_topics()
        
        # Check if we have topics
        if len(topic_model.topic_nums) == 0:
            logger.warning("Model has not found any topics. Will assign all papers to topic -1 (outlier)")
            # Assign all papers to topic -1 (outlier)
            doc_topics = [-1] * len(paper_ids)
            doc_probs = [0.0] * len(paper_ids)
        elif len(doc_topics) < len(paper_ids):
            logger.warning(f"Not enough topic assignments ({len(doc_topics)}) for papers ({len(paper_ids)}). Padding with -1 topics.")
            # Pad with -1 topics
            doc_topics = doc_topics + [-1] * (len(paper_ids) - len(doc_topics))
            doc_probs = doc_probs + [0.0] * (len(paper_ids) - len(doc_probs))
            
        # Prepare updates
        updates = []
        for i, (paper_id, topic, prob) in enumerate(zip(paper_ids, doc_topics, doc_probs)):
            # Default values for outliers or when no topics detected
            topic_words = []
            word_scores = []
            
            # Only try to access topic information if we have topics and the topic is valid
            if hasattr(topic_model, 'topic_words') and topic_model.topic_words is not None and topic >= 0:
                # Check if we have topics and if the topic index is valid
                if (isinstance(topic_model.topic_words, list) or isinstance(topic_model.topic_words, np.ndarray)) and \
                   len(topic_model.topic_words) > 0 and topic < len(topic_model.topic_words):
                    # Get topic words safely
                    try:
                        # Access the topic words
                        topic_word_item = topic_model.topic_words[topic]
                        if isinstance(topic_word_item, (list, np.ndarray)) and len(topic_word_item) > 0:
                            # Take the first 10 words or less
                            words = topic_word_item[:min(10, len(topic_word_item))]
                            topic_words = words.tolist() if isinstance(words, np.ndarray) else list(words)
                    except Exception as word_error:
                        logger.warning(f"Error accessing topic words: {word_error}")
                    
                    # Get word scores safely
                    try:
                        if hasattr(topic_model, 'word_scores') and topic_model.word_scores is not None and \
                           topic < len(topic_model.word_scores):
                            # Access the word scores
                            score_item = topic_model.word_scores[topic]
                            if isinstance(score_item, (list, np.ndarray)) and len(score_item) > 0:
                                # Take the first 10 scores or less
                                scores = score_item[:min(10, len(score_item))]
                                word_scores = scores.tolist() if isinstance(scores, np.ndarray) else list(scores)
                    except Exception as score_error:
                        logger.warning(f"Error accessing word scores: {score_error}")
            
            # Create update document with basic validation
            update = {
                'paper_id': paper_id,
                'topic_id': int(topic),
                'probability': float(prob),
                'topic_words': topic_words,
                'word_scores': word_scores,
                'processed_at': datetime.now(UTC),
                'categories': papers[i].get('categories', [])
            }
            
            updates.append(UpdateOne(
                {'paper_id': paper_id},
                {'$set': update},
                upsert=True
            ))
        
        if updates:
            try:
                result = mongo_collection.bulk_write(updates)
                logger.info(f"Wrote {result.upserted_count} new and modified {result.modified_count} existing documents")
                return len(updates)
            except Exception as e:
                logger.error(f'Error writing to MongoDB: {str(e)}')
                return 0
        else:
            logger.warning("No updates to write to MongoDB")
    except Exception as e:
        logger.error(f"Error processing batch: {str(e)}")
    
    return 0

def process_data(config: Dict[str, Any]) -> None:
    """Main processing function for extracting topics from paper summaries."""
    try:
        # Get MongoDB connection
        mongo_uri = get_mongo_uri(config)
        client = MongoClient(mongo_uri)
        db = client[config['top2vec']['mongo']['database']]
        
        # Get collections
        papers_collection = db[config['top2vec']['mongo']['papers_collection']]
        topics_collection = db[config['top2vec']['mongo']['topics_collection']]
        
        # Build query
        query = build_mongo_query(config)
        
        # Initialize Top2Vec model
        topic_model = EnhancedTopicModeler(
            min_count=config['top2vec']['min_count'],
            speed=config['top2vec']['speed'],
            workers=config['top2vec']['workers'],
            embedding_model=config['top2vec']['embedding_model']
        )
        
        # Get total number of papers
        total_papers = papers_collection.count_documents(query)
        logger.info(f'Found {total_papers} papers matching filters')
        
        # Process in batches
        batch_size = config['top2vec']['batch_size']
        max_papers = config['top2vec']['max_papers']
        processed_papers = 0
        
        # Adjust total papers if max_papers is set
        if max_papers > 0:
            total_papers = min(total_papers, max_papers)
            logger.info(f'Will process up to {total_papers} papers due to max_papers setting')
        
        for skip in tqdm(range(0, total_papers, batch_size)):
            # Fetch batch with consistent sorting
            papers = list(papers_collection.find(query, {
                'summary': 1,
                '_id': 1,
                'categories': 1
            }).sort('_id', 1).skip(skip).limit(batch_size))
            
            if not papers:
                logger.warning(f'No papers found in batch starting at {skip}')
                continue
                
            logger.info(f'Processing batch of {len(papers)} papers')
            
            # Process batch
            summaries = [doc.get('summary', '') for doc in papers]
            
            if skip == 0:  # First batch - fit and transform
                if len(summaries) < 2:
                    logger.error(f'Need at least 2 documents to fit Top2Vec model, got {len(summaries)}')
                    return
                    
                logger.info('Fitting Top2Vec model on first batch...')
                topic_model.fit(summaries)
            
            # Process the batch
            processed = process_batch(papers, topic_model, topics_collection)
            processed_papers += processed
            
            logger.info(f'Processed {processed} papers in current batch. Total processed: {processed_papers}')
            
            # Check if we've hit max_papers
            if max_papers > 0 and processed_papers >= max_papers:
                logger.info(f'Reached max papers limit of {max_papers}')
                break
            
        logger.info(f'Topic extraction completed. Total papers processed: {processed_papers}')
    except Exception as e:
        logger.error(f'Error in process_data: {str(e)}', exc_info=True)
        raise

def main() -> None:
    """Main entry point for the Top2Vec extraction pipeline."""
    parser = argparse.ArgumentParser(description='Run Top2Vec extraction pipeline')
    parser.add_argument('--config', default='config/default.yaml', help='Path to config file')
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config)
    
    logger.info('Starting Top2Vec extraction pipeline')
    start_time = datetime.now(UTC)
    
    try:
        process_data(config)
    except Exception as e:
        logger.error(f'Pipeline failed: {str(e)}', exc_info=True)
    finally:
        execution_time = datetime.now(UTC) - start_time
        logger.info(f'Pipeline execution completed in {execution_time}')

if __name__ == "__main__":
    main()