import logging
from typing import List, Dict, Any, Optional
from qdrant_client import models as qmodels

from app.services.qdrant import get_qdrant_client, ensure_collection
from app.services.llm import get_embedding

logger = logging.getLogger(__name__)

# Collection Name Constants
CHEF_COLLECTION_NAME = "chef_kb"

async def query_knowledge_base(
    query_str: str,
    collection_name: str = CHEF_COLLECTION_NAME,
    diet_filter: Optional[str] = None,
    cuisine_filter: Optional[str] = None,
    limit: int = 3
) -> List[Dict[str, Any]]:
    """
    Direct Qdrant similarity search with precise metadata filtering and semantic vector matching.
    """
    try:
        # Verify database collection presence
        ensure_collection(collection_name)
        
        # 1. Generate text embedding asynchronously
        query_vector = await get_embedding(query_str)
        
        # 2. Build Qdrant strict match filters
        must_conditions = []
        
        if diet_filter and diet_filter.lower() != "none":
            must_conditions.append(
                qmodels.FieldCondition(
                    key="diet",
                    match=qmodels.MatchValue(value=diet_filter.lower())
                )
            )
            
        if cuisine_filter:
            must_conditions.append(
                qmodels.FieldCondition(
                    key="cuisine",
                    match=qmodels.MatchValue(value=cuisine_filter.lower())
                )
            )
            
        search_filter = qmodels.Filter(must=must_conditions) if must_conditions else None
        
        # 3. Retrieve from Qdrant Client
        client = get_qdrant_client()
        response = client.query_points(
            collection_name=collection_name,
            query=query_vector,
            query_filter=search_filter,
            limit=limit
        )
        hits = response.points
        
        # 4. Parse results into structured response schema
        results = []
        for hit in hits:
            payload = hit.payload or {}
            results.append({
                "text": payload.get("text", ""),
                "metadata": {
                    "title": payload.get("title", "Unnamed Recipe"),
                    "cuisine": payload.get("cuisine", "any"),
                    "diet": payload.get("diet", "none"),
                    "prep_time": payload.get("prep_time", 0),
                    "difficulty": payload.get("difficulty", "easy"),
                },
                "score": hit.score
            })
            
        logger.info(f"RAG search retrieved {len(results)} matches for: '{query_str}'")
        return results
        
    except Exception as e:
        logger.error(f"Error querying knowledge base: {e}")
        return []
