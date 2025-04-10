from app.configs.configs import APP_NAME
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import api_router

application = FastAPI(title=APP_NAME, redoc_url=None, docs_url=None)

# Add CORSMiddleware to the application
application.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# including the endpoints from all routes
application.include_router(api_router)
