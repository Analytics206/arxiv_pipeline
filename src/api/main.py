from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from routes.mongodb import router as mongodb_router

app = FastAPI(title="ArXiv Pipeline API")

# Enable CORS for all origins (development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(mongodb_router, prefix="/metrics/mongodb", tags=["mongodb"])
