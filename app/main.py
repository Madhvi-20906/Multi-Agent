import os
import uvicorn
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load Env
load_dotenv()

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

from app.config import settings
from app.api.endpoints import router as api_router
from app.services.llm import init_llm_services
from app.services.qdrant import get_qdrant_client, ensure_collection
from app.rag.pipeline import CHEF_COLLECTION_NAME
from app.rag.ingest import ingest_recipes


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Modern lifespan handler replacing deprecated on_event('startup')."""
    logger.info("Starting up AI Agent Platform server...")
    
    # 1. Initialize LLM configurations (OpenAI)
    init_llm_services()
    
    # 2. Check Qdrant Connection
    try:
        logger.info("Initializing vector store collections...")
        client = get_qdrant_client()
        
        # Dynamically detect embedding size to adapt to different models (e.g. Gemini 768 vs OpenAI 1536)
        try:
            from app.services.llm import get_embedding
            test_vector = await get_embedding("test")
            vector_dim = len(test_vector)
            logger.info(f"Dynamically detected embedding dimension: {vector_dim}")
        except Exception as dim_err:
            logger.warning(f"Could not dynamically detect embedding size: {dim_err}. Defaulting to 1536.")
            vector_dim = 1536
            
        ensure_collection(CHEF_COLLECTION_NAME, vector_size=vector_dim)
        
        # Check if collection is empty, and auto-ingest seed data if so
        collections_info = client.get_collection(CHEF_COLLECTION_NAME)
        if collections_info.points_count == 0:
            logger.info("Qdrant collection is currently empty. Auto-ingesting seed culinary database...")
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            data_path = os.path.join(base_dir, "data", "culinary_kb.json")
            if os.path.exists(data_path):
                from app.rag.ingest import ingest_recipes_async
                await ingest_recipes_async(data_path)
            else:
                logger.warning(f"Seed data not found at {data_path}. Skipping auto-ingest.")
        else:
            logger.info(f"Qdrant collection '{CHEF_COLLECTION_NAME}' already has {collections_info.points_count} active records.")
    except Exception as e:
        logger.warning(f"Could not complete database initialization checks: {e}. Starting server with default fallbacks.")
        
    logger.info("Application startup processes completed successfully!")
    
    yield  # Application runs here
    
    # Shutdown cleanup (if needed in the future)
    logger.info("Shutting down AI Agent Platform server gracefully.")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        description="Production-Ready Allora Multi-Agent AI Platform Backend using RAG",
        version="1.0.0",
        lifespan=lifespan
    )

    # Configure CORS - allow localhost connections for developers
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register Router
    app.include_router(api_router)

    @app.get("/")
    def read_root():
        return {
            "status": "online",
            "message": "Allora Multi-Agent AI Platform Backend is running.",
            "frontend_url": "http://localhost:3000",
            "api_docs": "/docs"
        }

    return app

app = create_app()

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True
    )
