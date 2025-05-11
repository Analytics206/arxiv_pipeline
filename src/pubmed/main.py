# main.py
from pubmed_client import search_pubmed, fetch_details
from db_client import article_exists, save_article, save_articles
import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("query", type=str, help="Search query for PubMed")
    parser.add_argument("--max", type=int, default=10, help="Max results")
    args = parser.parse_args()

    pmids = search_pubmed(args.query, max_results=args.max)
    new_pmids = [pmid for pmid in pmids if not article_exists(pmid)]

    if not new_pmids:
        print("All results already cached.")
        return

    articles = fetch_details(new_pmids)
    save_articles(articles)
    print(f"Saved {len(articles)} new articles to MongoDB.")

if __name__ == "__main__":
    main()
