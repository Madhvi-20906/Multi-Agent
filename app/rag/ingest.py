import os
import json
import uuid
import asyncio
import logging
from typing import List
from qdrant_client import models as qmodels
from dotenv import load_dotenv

# Setup Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Absolute/Relative Imports fallback
from app.services.qdrant import get_qdrant_client, ensure_collection
from app.services.llm import get_embedding
from app.rag.pipeline import CHEF_COLLECTION_NAME

def load_recipes_from_json(file_path: str) -> List[dict]:
    """
    Loads raw recipe database from JSON file.
    """
    if not os.path.exists(file_path):
        logger.error(f"Knowledge source file not found at {file_path}")
        return []
    
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

async def ingest_recipes_async(json_path: str, collection_name: str = CHEF_COLLECTION_NAME):
    """
    Asynchronously parses recipe models, computes vector embeddings,
    and inserts points into Qdrant vector database.
    """
    recipes = load_recipes_from_json(json_path)
    if not recipes:
        logger.warning("No recipes loaded. Ingestion cancelled.")
        return
        
    logger.info(f"Loaded {len(recipes)} recipes from {json_path}. Processing embeddings...")
    
    ensure_collection(collection_name)
    client = get_qdrant_client()
    points = []
    
    for recipe in recipes:
        title = recipe.get("title", "Unnamed Recipe")
        cuisine = recipe.get("cuisine", "Any")
        diet = recipe.get("diet", "none")
        prep_time = recipe.get("prep_time", 0)
        difficulty = recipe.get("difficulty", "medium")
        
        ingredients = recipe.get("ingredients", [])
        steps = recipe.get("steps", [])
        substitutions = recipe.get("substitutions", {})
        tips = recipe.get("tips", [])
        
        ingredients_txt = "\n".join([f"- {ing}" for ing in ingredients])
        steps_txt = "\n".join([f"{i+1}. {step}" for i, step in enumerate(steps)])
        subs_txt = "\n".join([f"- {k}: substitute with {v}" for k, v in substitutions.items()])
        tips_txt = "\n".join([f"- {tip}" for tip in tips])
        
        full_recipe_text = (
            f"Recipe: {title}\n"
            f"Cuisine: {cuisine}\n"
            f"Dietary Suitability: {diet}\n"
            f"Preparation Time: {prep_time} minutes\n"
            f"Difficulty Level: {difficulty}\n\n"
            f"=== Ingredients ===\n{ingredients_txt}\n\n"
            f"=== Cooking Steps ===\n{steps_txt}\n\n"
            f"=== Ingredient Substitutions ===\n{subs_txt or 'None listed.'}\n\n"
            f"=== Professional Chef Tips ===\n{tips_txt or 'None listed.'}"
        )
        
        # 1. Compute embedding vector
        vector = await get_embedding(full_recipe_text)
        
        # 2. Package payload dict
        payload = {
            "text": full_recipe_text,
            "title": title,
            "cuisine": cuisine.lower(),
            "diet": diet.lower(),
            "prep_time": int(prep_time),
            "difficulty": difficulty.lower()
        }
        
        point_id = str(uuid.uuid4())
        points.append(
            qmodels.PointStruct(
                id=point_id,
                vector=vector,
                payload=payload
            )
        )
        logger.info(f"Prepared vector point for: {title} | Diet: {diet}")

    # 3. Batch upsert into Qdrant
    try:
        if points:
            client.upsert(
                collection_name=collection_name,
                points=points
            )
            logger.info(f"Ingested {len(points)} recipe points successfully into Qdrant collection '{collection_name}'!")
    except Exception as e:
        logger.error(f"Error during Qdrant upsert: {e}")

def ingest_recipes(json_path: str, collection_name: str = CHEF_COLLECTION_NAME):
    """
    Synchronous thread-safe manager to trigger ingestion safely in FastAPI background.
    """
    logger.info("Triggering database ingestion runner...")
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    if loop.is_running():
        import threading
        t = threading.Thread(
            target=lambda: asyncio.run(ingest_recipes_async(json_path, collection_name))
        )
        t.start()
        t.join()
    else:
        asyncio.run(ingest_recipes_async(json_path, collection_name))

if __name__ == "__main__":
    load_dotenv()
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    data_path = os.path.join(base_dir, "data", "culinary_kb.json")
    ingest_recipes(data_path)
