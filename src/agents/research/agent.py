# agents/research/agent.py
import asyncio
from typing import Dict, Any, List, Optional
import os
import json

from agent_core.models.base import ModelInterface
from agent_core.data.mongodb import MongoDBClient
from agent_core.data.neo4j import Neo4jClient
from agent_core.data.qdrant import QdrantClient
from agents.base_agent import BaseAgent
from agents.research.paper_processor import PaperProcessor
from agents.research.concept_mapper import ConceptMapper

class ResearchAnalysisAgent(BaseAgent):
    """Agent for analyzing research papers and generating insights."""
    
    def __init__(self, config: Dict[str, Any], model_interface: ModelInterface):
        super().__init__("research_analysis", config, model_interface)
        self.data_sources = config.get("data_sources", [])
        self.tasks = config.get("tasks", [])
        self.vector_store_config = config.get("vector_store", {})
        
        # Initialize components
        self.paper_processor = PaperProcessor()
        self.concept_mapper = ConceptMapper()
        
        # Initialize clients
        self.mongodb_clients = {}
        self.neo4j_clients = {}
        self.vector_store = None
        
    async def initialize(self) -> None:
        """Initialize the research analysis agent."""
        self.logger.info("Initializing research analysis agent")
        
        # Initialize data source clients
        for source in self.data_sources:
            source_type = source.get("type")
            
            if source_type == "mongodb":
                client = MongoDBClient(
                    connection_string=source.get("connection"),
                    database=source.get("database")
                )
                self.mongodb_clients[source.get("database")] = client
                self.logger.info(f"Connected to MongoDB database: {source.get('database')}")
                
            elif source_type == "neo4j":
                client = Neo4jClient(
                    url=source.get("url"),
                    user=source.get("user"),
                    password=os.environ.get(source.get("password").replace("${", "").replace("}", ""))
                    if source.get("password", "").startswith("${") else source.get("password")
                )
                self.neo4j_clients["default"] = client
                self.logger.info("Connected to Neo4j database")
        
        # Initialize vector store
        if self.vector_store_config:
            vector_type = self.vector_store_config.get("type")
            if vector_type == "qdrant":
                self.vector_store = QdrantClient(
                    url=self.vector_store_config.get("url"),
                    collection=self.vector_store_config.get("collection")
                )
                self.logger.info(f"Connected to Qdrant collection: {self.vector_store_config.get('collection')}")
    
    async def run_cycle(self) -> Dict[str, Any]:
        """Run a research analysis cycle."""
        self.logger.info("Running research analysis cycle")
        
        # Get papers to analyze
        papers = await self._fetch_papers()
        
        if not papers:
            self.logger.info("No papers to analyze")
            return {"status": "no_papers"}
        
        # Process tasks
        results = {}
        for task in self.tasks:
            task_name = task.get("name")
            self.logger.info(f"Processing task: {task_name}")
            
            task_results = await self._process_task(task, papers)
            results[task_name] = task_results
        
        return {
            "status": "completed",
            "papers_analyzed": len(papers),
            "results": results
        }
    
    async def _fetch_papers(self) -> List[Dict[str, Any]]:
        """Fetch papers from configured data sources."""
        all_papers = []
        
        # Fetch from MongoDB
        for db_name, client in self.mongodb_clients.items():
            for source in self.data_sources:
                if source.get("type") == "mongodb" and source.get("database") == db_name:
                    collection = client.get_collection(source.get("collection"))
                    papers = list(collection.find({}))
                    self.logger.info(f"Fetched {len(papers)} papers from MongoDB collection {source.get('collection')}")
                    all_papers.extend(papers)
        
        # Fetch from Neo4j
        for _, client in self.neo4j_clients.items():
            for source in self.data_sources:
                if source.get("type") == "neo4j":
                    query = source.get("query")
                    papers = client.run_query(query)
                    self.logger.info(f"Fetched {len(papers)} papers from Neo4j")
                    all_papers.extend(papers)
        
        return all_papers
    
    async def _process_task(self, task: Dict[str, Any], papers: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Process a specific task on the papers."""
        task_name = task.get("name")
        prompt_template_path = task.get("prompt_template")
        
        # Load prompt template
        prompt_template = ""
        if prompt_template_path and os.path.exists(prompt_template_path):
            with open(prompt_template_path, 'r') as f:
                prompt_template = f.read()
        else:
            prompt_template = self._get_default_prompt(task_name)
        
        results = {}
        
        # Process each paper
        for paper in papers:
            paper_id = str(paper.get("_id", paper.get("id", "unknown")))
            paper_title = paper.get("title", "Untitled")
            
            # Create prompt for this paper
            prompt = prompt_template.format(
                title=paper_title,
                abstract=paper.get("abstract", ""),
                authors=", ".join(paper.get("authors", [])),
                categories=", ".join(paper.get("categories", [])),
                content=paper.get("content", "")[:2000]  # Limit content to prevent token overflow
            )
            
            # Generate analysis
            analysis = await self.model.generate(
                prompt=prompt,
                system_prompt=f"You are an expert research analyst specializing in scientific papers. Your task is to {task.get('description')}",
                parameters={"temperature": 0.3}
            )
            
            results[paper_id] = {
                "title": paper_title,
                "analysis": analysis
            }
            
        return results
    
    def _get_default_prompt(self, task_name: str) -> str:
        """Get a default prompt template for a task."""
        if task_name == "summarize":
            return """
            Please provide a comprehensive summary of the following research paper:
            
            Title: {title}
            Authors: {authors}
            Categories: {categories}
            
            Abstract:
            {abstract}
            
            Paper excerpt:
            {content}
            
            Your summary should include:
            1. The main research question or problem
            2. Key methodologies used
            3. Major findings and results
            4. Limitations and future work
            5. Potential applications and impact
            """
        elif task_name == "concept_mapping":
            return """
            Please extract and map the key concepts from the following research paper:
            
            Title: {title}
            Authors: {authors}
            Categories: {categories}
            
            Abstract:
            {abstract}
            
            Paper excerpt:
            {content}
            
            Your response should include:
            1. A list of key concepts/terms and their definitions
            2. Relationships between these concepts
            3. How these concepts connect to the broader field
            4. Novel combinations or applications of these concepts
            """
        else:
            return """
            Please analyze the following research paper:
            
            Title: {title}
            Authors: {authors}
            Categories: {categories}
            
            Abstract:
            {abstract}
            
            Paper excerpt:
            {content}
            
            Provide a detailed analysis including key points, methodology, results, and significance.
            """