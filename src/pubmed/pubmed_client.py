# pubmed_client.py
from Bio import Entrez
from config import EMAIL
import xml.etree.ElementTree as ET

Entrez.email = EMAIL

def search_pubmed(query, max_results=20):
    handle = Entrez.esearch(db="pubmed", term=query, retmax=max_results)
    record = Entrez.read(handle)
    handle.close()
    return record["IdList"]

def fetch_details(pmid_list):
    handle = Entrez.efetch(db="pubmed", id=",".join(pmid_list), rettype="xml", retmode="text")
    records = handle.read()
    handle.close()
    return parse_pubmed_xml(records)

def parse_pubmed_xml(xml_data):
    root = ET.fromstring(xml_data)
    articles = []
    for article in root.findall(".//PubmedArticle"):
        try:
            pmid = article.findtext(".//PMID")
            title = article.findtext(".//ArticleTitle")
            abstract = article.findtext(".//AbstractText")
            authors = [
                f"{a.findtext('ForeName', '')} {a.findtext('LastName', '')}".strip()
                for a in article.findall(".//Author") if a.find("LastName") is not None
            ]
            journal = article.findtext(".//Journal/Title")
            articles.append({
                "pmid": pmid,
                "title": title,
                "abstract": abstract,
                "authors": authors,
                "journal": journal
            })
        except Exception as e:
            print("Parse error:", e)
    return articles
