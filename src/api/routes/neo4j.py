from fastapi import APIRouter, Query, Body
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable
import os
import logging
from typing import Dict, Any, Optional, List

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# Neo4j connection settings
# Use Docker service name for Neo4j inside Docker network
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

# Log connection parameters (without password)
logging.info(f"Neo4j connection configured with URI: {NEO4J_URI}")
logging.info(f"Neo4j user: {NEO4J_USER}")

def get_driver():
    """Get a Neo4j driver instance with proper error handling"""
    try:
        driver = GraphDatabase.driver(
            NEO4J_URI, 
            auth=(NEO4J_USER, NEO4J_PASSWORD),
            encrypted=False
        )
        return driver
    except Exception as e:
        logger.error(f"Failed to create Neo4j driver: {str(e)}")
        return None

@router.get("/test-connection")
def test_neo4j_connection():
    """Test connection to Neo4j database"""
    try:
        driver = get_driver()
        if not driver:
            return {"status": "error", "message": "Failed to create Neo4j driver"}
        
        # Test connection with a simple query
        with driver.session() as session:
            result = session.run("CALL db.info()")
            record = result.single()
            if record:
                databases = ["neo4j"]  # Default database
                
                # Try to get list of databases (Neo4j 4.0+)
                try:
                    db_result = session.run("SHOW DATABASES")
                    databases = [record["name"] for record in db_result]
                except:
                    # Older Neo4j or no permission, use default
                    pass
                    
                return {"status": "success", "message": "Connected to Neo4j", "databases": databases}
            else:
                return {"status": "warning", "message": "Connected to Neo4j but couldn't retrieve database info"}
    except ServiceUnavailable as e:
        return {"status": "error", "message": f"Neo4j is unavailable: {str(e)}"}
    except Exception as e:
        return {"status": "error", "message": f"Failed to connect to Neo4j: {str(e)}"}
    finally:
        if driver:
            driver.close()

@router.get("/db-stats")
def neo4j_db_stats():
    """Get Neo4j database statistics (papers, authors, categories)"""
    try:
        driver = get_driver()
        if not driver:
            return {"papers": 0, "authors": 0, "categories": 0, "error": "Failed to create Neo4j driver"}
        
        with driver.session() as session:
            # Count papers
            paper_result = session.run("MATCH (p:Paper) RETURN count(p) as count")
            paper_count = paper_result.single()["count"] if paper_result.peek() else 0
            
            # Count authors
            author_result = session.run("MATCH (a:Author) RETURN count(a) as count")
            author_count = author_result.single()["count"] if author_result.peek() else 0
            
            # Count categories
            category_result = session.run("MATCH (c:Category) RETURN count(c) as count")
            category_count = category_result.single()["count"] if category_result.peek() else 0
            
            return {"papers": paper_count, "authors": author_count, "categories": category_count}
    except Exception as e:
        logger.error(f"Neo4j stats error: {str(e)}")
        # Return fallback values for UI compatibility
        return {"papers": 0, "authors": 0, "categories": 0, "error": str(e)}
    finally:
        if driver:
            driver.close()

@router.post("/run-query")
def run_neo4j_query(cypher_query: str = Body(..., embed=True)):
    """Run a Cypher query and return the results in a format suitable for visualization"""
    try:
        driver = get_driver()
        if not driver:
            return {"nodes": [], "edges": [], "error": "Failed to create Neo4j driver"}
        
        with driver.session() as session:
            result = session.run(cypher_query)
            
            # Process the records into a format for Cytoscape
            node_map = {}
            edges = []
            
            for record in result:
                for key in record.keys():
                    value = record[key]
                    
                    # Handle nodes
                    if hasattr(value, 'id') and hasattr(value, 'labels'):
                        # This is a node
                        if value.id not in node_map:
                            label = value.get('name') or value.get('title') or value.get('id') or key
                            
                            node_map[value.id] = {
                                "data": {
                                    "id": str(value.id),
                                    "label": label[:20] + '...' if isinstance(label, str) and len(label) > 20 else label,
                                    "type": list(value.labels)[0] if value.labels else "Unknown",
                                    "properties": dict(value)
                                }
                            }
                    
                    # Handle relationships
                    if hasattr(record, '_values'):
                        for field in record._values:
                            if hasattr(field, 'start_node') and hasattr(field, 'end_node'):
                                # This is a relationship
                                edges.append({
                                    "data": {
                                        "id": f"{field.start_node.id}-{field.end_node.id}",
                                        "source": str(field.start_node.id),
                                        "target": str(field.end_node.id),
                                        "label": field.type,
                                        "properties": dict(field)
                                    }
                                })
            
            return {
                "nodes": list(node_map.values()),
                "edges": edges
            }
    except Exception as e:
        logger.error(f"Error executing Neo4j query: {str(e)}")
        return {"nodes": [], "edges": [], "error": str(e)}
    finally:
        if driver:
            driver.close()
