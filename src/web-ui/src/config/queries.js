// This file contains the Neo4j query configurations
const queries = {
  queries: [
    {
      id: "papers_count",
      name: "Papers Count",
      description: "Show count of papers in the database",
      category: "Overview",
      cypher: "MATCH (p:Paper) RETURN count(p) AS paper_count"
    },
    {
      id: "author_network",
      name: "Author Collaboration Network",
      description: "Show authors who have collaborated on papers",
      category: "Authors",
      cypher: "MATCH (a1:Author)-[:AUTHORED]->(p:Paper)<-[:AUTHORED]-(a2:Author) WHERE a1 <> a2 RETURN a1, a2, p LIMIT 200"
    },
    {
      id: "category_distribution",
      name: "Category Distribution",
      description: "Show papers by category with category sizes proportional to paper count",
      category: "Categories",
      cypher: "MATCH (p:Paper)-[:BELONGS_TO]->(c:Category) RETURN p, c LIMIT 200"
    }
  ]
};

export default queries;