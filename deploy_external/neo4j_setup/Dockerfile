FROM neo4j:5.13

# Set configuration options
ENV NEO4J_AUTH=neo4j/password
ENV NEO4J_dbms_memory_pagecache_size=1G
ENV NEO4J_dbms_memory_heap_initial__size=1G
ENV NEO4J_dbms_memory_heap_max__size=2G
ENV NEO4J_dbms_connector_bolt_advertised__address=:7687
ENV NEO4J_dbms_connector_http_advertised__address=:7474

# Expose Neo4j ports
EXPOSE 7474 7473 7687

# Default entrypoint/command from base image will start Neo4j