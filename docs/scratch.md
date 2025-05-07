
# Notes

- pip install seaborn wordcloud
- test scripts and setup for qdrant remote
- fix dashboards
- fix jupyter notebooks
- Admin user interface for configuration and running pipelines
- pipelines can be used with different pdf sources
- verify readme.md is updated with complete stop start of all docker containers
- cd src\web-ui; npm install react-router-dom
- remove neo4j-sync from docker-compose.yml
- Works *neo4j-sync docker container 
- python execution, docker to docker sync might need names instead of localhost or vise-versa
- python -m src.pipeline.sync_qdrant - Adjusted MongoDB connection for local execution: mongodb://localhost:27017/
- cd src\web-ui; npm install react-router-dom
-  jupyter/scipy docker container
- docker-compose --profile manual up jupyter-scipy
- http://localhost:8000/docs# api documentation
- http://localhost:3000/docs# web ui documentation (blank)
- Jupyter notebook docker runs last to more easily rind key, restart Jupyter docker might needed to find key again
- docker-compose --profile manual up zookeeper kafka
- docker-compose --profile manual up zookeeper kafka kafka-ui *http://localhost:8080*
- check readme.md for possible deletion database connections information

cd src\web-ui
$env:PORT=3001
npm start