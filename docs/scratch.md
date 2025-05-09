
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
- python src/pipeline/sync_summary_vectors.py
- ollama api check http://localhost:11434/
- ### Activate venv first
cd c:\Users\mad_p\OneDrive\Desktop\arxiv_pipeline
python src/utils/track_downloaded_pdfs.py

cd src\web-ui
$env:PORT=3001
npm start


```bash
{
  "limit": 1000,
  "using": "default"
}

{
  "limit": 5000,
  "using": "default",
  "filter": {
    "must": [
      {
        "key": "category",
        "match": {
          "value": "cs.AI"
        }
      }
    ]
  }
}

{
  "limit": 5000,
  "using": "default",
  "filter": {
    "must": [
      {
        "key": "category",
        "match": {
          "value": "cs.AI"
        }
      },
      {
        "key": "summary",
        "match": {
          "value": "Neural network model for classification"
        }
      }
    ]
  }
}

'''


https://marketplace.visualstudio.com/items
## windsurf marketplace
https://marketplace.windsurf.com/vscode/gallery
https://marketplace.windsurf.com/vscode/item

      },
      "dbcode": {
        "command": "C:\\Users\\mad_p\\.vscode\\extensions\\dbcode.dbcode-1.12.5\\out\\extension.js",
        "args": []
      }


      {
    "mssql.connectionGroups": [
        {
            "name": "ROOT",
            "id": "5F7B90A1-3644-4236-9F97-0786B24AD6A4"
        }
    ],
    "mssql.connections": [],
    "mcp": {
        
        "inputs": [],
        "servers": {
            "mcp-server-time": {
                "command": "python",
                "args": [
                    "-m",
                    "mcp_server_time",
                    "--local-timezone=America/Los_Angeles"
                ],
                "env": {}
            }
        }
    },
    "git.confirmSync": false
}