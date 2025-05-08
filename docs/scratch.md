
# Notes

- pip install seaborn wordcloud
- test scripts and setup for qdrant remote
- fix dashboards 
- fix jupyter notebooks
- Admin user interface for configuration and running pipelines
- pipelines can be used with different pdf sources
- verify readme.md is updated with complete stop start of all docker containers
- cd src\web-ui; npm install react-router-dom
x remove neo4j-sync from docker-compose.yml
- python execution, docker to docker sync might need names instead of localhost or vise-versa
- python -m src.pipeline.sync_qdrant - Adjusted MongoDB connection for local execution: mongodb://localhost:27017/
- cd src\web-ui; npm install react-router-dom
- docker-compose --profile manual up jupyter-scipy
- http://localhost:8000/docs# api documentation
- http://localhost:3000/docs# web ui documentation (blank)
- Jupyter notebook docker runs last to more easily rind key, restart Jupyter docker might needed to find key again
- docker-compose --profile manual up zookeeper kafka kafka-ui *http://localhost:8080*
- check readme.md for possible deletion database connections information
- setup ollama docker for use on external machine and local machine
- setup qdrant docker for use on external machine and local machine
- setup mongodb docker for use on external machine and local machine
- setup neo4j docker for use on external machine and local machine
- setup zookeeper docker for use on external machine and local machine
- setup kafka docker for use on external machine and local machine
- setup kafka-ui docker for use on external machine and local machine
- Fix local vs docker
- ollama api check http://localhost:11434/
- # Activate venv first
cd c:\Users\mad_p\OneDrive\Desktop\arxiv_pipeline
python src/utils/track_downloaded_pdfs.py

cd src\web-ui
$env:PORT=3001
npm start