# Notes
- pip install seaborn wordcloud
- test scripts and setup for qdrant remote
- fix jupyter notebooks
- Admin user interface for configuration and running pipelines
- pipelines can be used with different pdf sources
- verify readme.md is updated with complete stop start of all docker containers
- cd src\web-ui; npm install react-router-dom
- python execution, docker to docker sync might need names instead of localhost or vise-versa
- python -m src.pipeline.sync_qdrant - Adjusted MongoDB connection for local execution: mongodb://localhost:27017/
- cd src\web-ui; npm install react-router-dom
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

docker-compose --profile manual build --no-cache sync-top2vec
docker-compose --profile manual up sync-top2vec

Remove-Item -Recurse -Force .venv  # or venv, depending on your folder name
python3.11 -m venv .venv
.\.venv\Scripts\Activate
pip install -e .

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


📅 Monthly Summary 📅
----------------------------------------
Month      |    Count |   Percentage
----------------------------------------
2025-05    |    1,738 |        1.35%
2025-04    |    8,843 |        6.87%
2025-03    |   10,653 |        8.27%
2025-02    |    9,895 |        7.68%
2025-01    |    7,233 |        5.62%
2024-12    |    6,923 |        5.37%
2024-11    |    5,496 |        4.27%
2024-10    |    7,878 |        6.12%
2024-09    |    5,861 |        4.55%
2024-08    |    4,698 |        3.65%
2024-07    |    5,337 |        4.14%
2024-06    |    6,744 |        5.24%
----------------------------------------
Total Papers: 128,806


📊 ArXiv Papers by Year 📊
--------------------------------------------------
Year   |    Count |  Percentage | Distribution
--------------------------------------------------
2022   |    3,725 |       2.86% | █
2023   |   18,764 |      14.40% | █████
2024   |   69,444 |      53.30% | ████████████████████
2025   |   38,362 |      29.44% | ███████████
--------------------------------------------------

📅 ArXiv Papers by Month 📅
------------------------------------------------------------
Year-Month |    Count |  Percentage | Distribution
------------------------------------------------------------
2022-01    |       91 |       0.07% |
2022-02    |      262 |       0.20% |
2022-03    |      155 |       0.12% |
2022-04    |      366 |       0.28% |
2022-05    |      472 |       0.36% | █
2022-06    |      262 |       0.20% |
2022-07    |      337 |       0.26% |
2022-08    |      497 |       0.38% | █
2022-09    |      332 |       0.25% |
2022-10    |      335 |       0.26% |
2022-11    |      391 |       0.30% |
2022-12    |      225 |       0.17% |
2023-01    |    1,159 |       0.89% | ██
2023-02    |      973 |       0.75% | ██
2023-03    |    1,070 |       0.82% | ██
2023-04    |    1,131 |       0.87% | ██
2023-05    |    1,719 |       1.32% | ████
2023-06    |    1,336 |       1.03% | ███
2023-07    |    1,317 |       1.01% | ███
2023-08    |    1,334 |       1.02% | ███
2023-09    |    1,082 |       0.83% | ██
2023-10    |    2,167 |       1.66% | █████
2023-11    |    2,614 |       2.01% | ██████
2023-12    |    2,862 |       2.20% | ██████
2024-01    |    3,761 |       2.89% | ████████
2024-02    |    5,580 |       4.28% | █████████████
2024-03    |    5,229 |       4.01% | ████████████
2024-04    |    4,849 |       3.72% | ███████████
2024-05    |    5,599 |       4.30% | █████████████
2024-06    |    6,744 |       5.18% | ███████████████
2024-07    |    5,337 |       4.10% | ████████████
2024-08    |    4,698 |       3.61% | ███████████
2024-09    |    6,186 |       4.75% | ██████████████
2024-10    |    8,580 |       6.59% | ████████████████████
2024-11    |    5,958 |       4.57% | █████████████
2024-12    |    6,923 |       5.31% | ████████████████
2025-01    |    7,233 |       5.55% | ████████████████
2025-02    |    9,895 |       7.59% | ███████████████████████
2025-03    |   10,653 |       8.18% | █████████████████████████
2025-04    |    8,843 |       6.79% | ████████████████████
2025-05    |    1,738 |       1.33% | ████
------------------------------------------------------------

📆 ArXiv Papers by Day (Last {max_days} Days) 📆
------------------------------------------------------------
Date       |  Count | Percentage | Day of Week | Distribution
------------------------------------------------------------
2025-04-07 |    395 |    0.30% |   Monday   | ██████████████
2025-04-08 |    354 |    0.27% |  Tuesday   | ████████████
2025-04-09 |    317 |    0.24% | Wednesday  | ███████████
2025-04-10 |    339 |    0.26% |  Thursday  | ████████████
2025-04-11 |    318 |    0.24% |   Friday   | ███████████
2025-04-12 |    162 |    0.12% |  Saturday  | █████
2025-04-13 |    185 |    0.14% |   Sunday   | ██████
2025-04-14 |    410 |    0.31% |   Monday   | ██████████████
2025-04-15 |    370 |    0.28% |  Tuesday   | █████████████
2025-04-16 |    331 |    0.25% | Wednesday  | ████████████
2025-04-17 |    359 |    0.28% |  Thursday  | █████████████
2025-04-18 |    281 |    0.22% |   Friday   | ██████████
2025-04-19 |    155 |    0.12% |  Saturday  | █████
2025-04-20 |    157 |    0.12% |   Sunday   | █████
2025-04-21 |    302 |    0.23% |   Monday   | ███████████
2025-04-22 |    326 |    0.25% |  Tuesday   | ███████████
2025-04-23 |    326 |    0.25% | Wednesday  | ███████████
2025-04-24 |    352 |    0.27% |  Thursday  | ████████████
2025-04-25 |    303 |    0.23% |   Friday   | ███████████
2025-04-26 |    138 |    0.11% |  Saturday  | █████
2025-04-27 |    156 |    0.12% |   Sunday   | █████
2025-04-28 |    334 |    0.26% |   Monday   | ████████████
2025-04-29 |    360 |    0.28% |  Tuesday   | █████████████
2025-04-30 |    341 |    0.26% | Wednesday  | ████████████
2025-05-01 |    309 |    0.24% |  Thursday  | ███████████
2025-05-02 |    294 |    0.23% |   Friday   | ██████████
2025-05-03 |    138 |    0.11% |  Saturday  | █████
2025-05-04 |    175 |    0.13% |   Sunday   | ██████
2025-05-05 |    279 |    0.21% |   Monday   | ██████████
2025-05-06 |    321 |    0.25% |  Tuesday   | ███████████
2025-05-07 |    222 |    0.17% | Wednesday  | ████████
------------------------------------------------------------

📊 ArXiv Papers by Day of Week 📊
------------------------------------------------------------
   Day     |    Count |  Percentage | Distribution
------------------------------------------------------------
  Monday   |   23,640 |      18.14% | █████████████████████████
 Tuesday   |   22,971 |      17.63% | ████████████████████████
Wednesday  |   21,482 |      16.49% | ██████████████████████
 Thursday  |   22,384 |      17.18% | ███████████████████████
  Friday   |   19,600 |      15.04% | ████████████████████
 Saturday  |    9,835 |       7.55% | ██████████
  Sunday   |   10,383 |       7.97% | ██████████
------------------------------------------------------------

Total Papers: 130,295
Distinct Years: 4
Distinct Months: 41
Distinct Days: 1216