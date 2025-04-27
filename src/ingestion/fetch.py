import requests
import xml.etree.ElementTree as ET
import datetime
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class ArxivClient:
    """Client for fetching papers from arXiv API using Atom XML format."""
    
    BASE_URL = "http://export.arxiv.org/api/query"
    
    def __init__(self, 
                 max_results: int = 10000, 
                 sort_by: str = "submittedDate", 
                 sort_order: str = "descending"):
        self.max_results = max_results
        self.sort_by = sort_by
        self.sort_order = sort_order
    
    def fetch_papers(self, 
                    category: str = "cs.AI", 
                    search_query: Optional[str] = None, 
                    start: int = 0) -> List[Dict]:
        """
        Fetch papers from arXiv API.
        
        Args:
            category: arXiv category (default: cs.AI)
            search_query: Optional search terms
            start: Starting index for pagination
            
        Returns:
            List of paper metadata dictionaries
        """
        # Build query
        query_parts = []
        if category:
            query_parts.append(f"cat:{category}")
        if search_query:
            query_parts.append(search_query)
        
        search_query_str = " AND ".join(query_parts)
        
        # Build request params
        params = {
            "search_query": search_query_str,
            "start": start,
            "max_results": self.max_results,
            "sortBy": self.sort_by,
            "sortOrder": self.sort_order
        }
        
        logger.info(f"Fetching papers with params: {params}")
        
        # Make request
        response = requests.get(self.BASE_URL, params=params)
        
        if response.status_code != 200:
            logger.error(f"Error fetching papers: {response.status_code} - {response.text}")
            return []
        
        # Parse XML response
        return self._parse_response(response.text)
    
    def _parse_response(self, xml_data: str) -> List[Dict]:
        """Parse arXiv API XML response into list of dictionaries."""
        root = ET.fromstring(xml_data)
        
        # Define XML namespaces
        namespaces = {
            'atom': 'http://www.w3.org/2005/Atom',
            'arxiv': 'http://arxiv.org/schemas/atom'
        }
        
        results = []
        
        # Extract entries
        for entry in root.findall('atom:entry', namespaces):
            paper = {}
            
            # Basic metadata
            paper['id'] = self._get_text(entry, 'atom:id', namespaces)
            paper['title'] = self._get_text(entry, 'atom:title', namespaces)
            paper['summary'] = self._get_text(entry, 'atom:summary', namespaces)
            paper['published'] = self._get_text(entry, 'atom:published', namespaces)
            paper['updated'] = self._get_text(entry, 'atom:updated', namespaces)
            
            # Authors
            paper['authors'] = []
            for author in entry.findall('atom:author', namespaces):
                name = self._get_text(author, 'atom:name', namespaces)
                if name:
                    paper['authors'].append(name)
            
            # arXiv specific fields
            paper['arxiv_url'] = paper['id']
            paper['pdf_url'] = paper['id'].replace('abs', 'pdf')
            
            # Categories
            paper['categories'] = []
            for category in entry.findall('arxiv:primary_category', namespaces):
                if 'term' in category.attrib:
                    paper['categories'].append(category.attrib['term'])
            
            # Add to results
            results.append(paper)
        
        logger.info(f"Parsed {len(results)} papers from arXiv response")
        return results
    
    @staticmethod
    def _get_text(element, xpath, namespaces, default=''):
        """Helper to extract text from XML element with proper error handling."""
        try:
            return element.find(xpath, namespaces).text.strip()
        except (AttributeError, TypeError):
            return default