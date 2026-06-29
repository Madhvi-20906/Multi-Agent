import logging
import asyncio
from typing import Optional, List
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.orchestration.orchestrator import orchestrator
from app.rag.pipeline import query_knowledge_base
from app.rag.ingest import ingest_recipes
from app.services.llm import get_openai_client
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

# --- Pydantic Schema Models ---

class ChatRequest(BaseModel):
    message: str = Field(..., description="The user's query or instruction.")
    session_id: Optional[str] = Field(None, description="Optional conversation session ID.")
    agent_id: Optional[str] = Field("chef", description="Target agent to query (e.g., 'chef').")
    diet_preference: Optional[str] = Field(None, description="Dietary filters to enforce.")

class SessionUpdateAgent(BaseModel):
    agent_id: str

class SessionUpdateDiet(BaseModel):
    diet_preference: str

class RecipeGenerateRequest(BaseModel):
    prompt: str = Field(..., description="Description or core ingredients of the desired recipe.")
    diet: Optional[str] = Field("none", description="Dietary style (e.g. 'vegan', 'keto').")

class SeedInjectionRequest(BaseModel):
    seed_context: str = Field(..., description="The shared coordination context to inject.")

# --- Endpoints ---

@router.get("/health")
def health_check():
    """
    Standard service health check endpoint.
    """
    return {"status": "healthy", "service": "AI Agent Platform API"}


@router.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """
    Core Server-Sent Events (SSE) chat response streaming endpoint.
    Retrieves agent from orchestrator, logs memory, triggers tool analysis,
    and returns token-by-token text streams.
    """
    logger.info(f"Received chat request: session_id={request.session_id}, agent={request.agent_id}")
    
    # Retrieve or create session
    session = orchestrator.get_or_create_session(request.session_id)
    session_id = session["session_id"]
    
    # Update active agent and diet preference if supplied
    if request.agent_id:
        orchestrator.update_session_agent(session_id, request.agent_id)
    if request.diet_preference:
        orchestrator.update_session_diet(session_id, request.diet_preference)
        
    active_agent_id = session["active_agent"]
    diet = session["diet_preference"]
    history = session["history"]
    
    # Fetch agent instance
    agent = orchestrator.get_agent(active_agent_id)
    
    # Add user message to session history
    orchestrator.add_message(session_id, "user", request.message)

    async def event_generator():
        # Stream response
        try:
            full_response = ""
            async for token in agent.chat_stream(
                message=request.message,
                history=history,
                diet_preference=diet
            ):
                full_response += token
                # Escape newlines to prevent breaking the SSE line-by-line protocol
                safe_token = token.replace("\n", "\\n").replace("\r", "")
                yield f"data: {safe_token}\n\n"
                
            # Log completed agent response back to memory
            orchestrator.add_message(session_id, "assistant", full_response)
            
            # Send session metadata updates (like ID and Title) at the end
            yield f"event: metadata\ndata: {{\"session_id\": \"{session_id}\", \"title\": \"{session['title']}\"}}\n\n"
            
        except Exception as e:
            logger.error(f"Error in event stream: {e}")
            yield f"data: Error during streaming generation: {str(e)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/recipes/generate")
async def generate_recipe_endpoint(request: RecipeGenerateRequest):
    """
    Non-streaming, structured recipe generation endpoint.
    Forces Chef Agent to generate and return a completed recipe.
    """
    chef = orchestrator.get_agent("chef")
    try:
        query = f"Provide a recipe for: {request.prompt}."
        recipe_content = await chef.chat(
            message=query,
            history=[],
            diet_preference=request.diet
        )
        return {"recipe": recipe_content}
    except Exception as e:
        logger.error(f"Error generating recipe: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/seed")
async def seed_injection_endpoint(request: SeedInjectionRequest):
    """
    RAG-driven Seed Injection:
    1. Fetches RAG context for the seed.
    2. Queries all active agents for their perspective (sequentially with backoff retries to handle rate limits).
    3. Uses an overarching Orchestrator prompt to synthesize a Master Plan.
    """
    logger.info(f"Received Seed Injection Request: {request.seed_context}")
    
    # 1. Fetch RAG Context
    rag_results = await query_knowledge_base(query_str=request.seed_context, diet_filter="none", limit=3)
    rag_text = "\n\n".join([f"Source: {res['metadata'].get('title', 'Knowledge Base')}\nContent: {res['text']}" for res in rag_results])
    
    # Construct combined prompt for agents
    agent_prompt = f"Seed Context: {request.seed_context}\n\nRelevant Knowledge Base Context:\n{rag_text if rag_results else 'None found.'}\n\nPlease provide your unique perspective and contribution to this plan based on your expertise. Be concise."
    
    # 2. Gather perspectives sequentially with retry mechanism
    agent_ids = ["chef", "baker", "gardener", "stylist", "event"]
    results = []
    
    async def fetch_perspective_with_retry(agent_id):
        agent = orchestrator.get_agent(agent_id)
        max_retries = 3
        delay = 2.0
        for attempt in range(max_retries):
            try:
                # Spacer delay before each call to avoid concurrency rate spikes
                await asyncio.sleep(0.8)
                resp = await agent.chat(message=agent_prompt, history=[])
                return agent_id, resp
            except Exception as e:
                err_msg = str(e).lower()
                is_rate_limit = "429" in err_msg or "quota" in err_msg or "limit" in err_msg or "exhausted" in err_msg
                if is_rate_limit and attempt < max_retries - 1:
                    logger.warning(f"Rate limit hit for agent '{agent_id}' (attempt {attempt + 1}/{max_retries}). Retrying in {delay}s...")
                    await asyncio.sleep(delay)
                    delay *= 2
                else:
                    logger.error(f"Failed to generate perspective for agent '{agent_id}': {e}")
                    return agent_id, f"Error generating perspective: {str(e)}"
        return agent_id, f"Failed to retrieve perspective after {max_retries} attempts due to API rate limits."

    for aid in agent_ids:
        aid_res, resp_res = await fetch_perspective_with_retry(aid)
        results.append((aid_res, resp_res))

    perspectives = {aid: resp for aid, resp in results}
    
    # 3. Master Synthesis
    synthesis_prompt = f"""
    You are the Master Orchestrator AI. A user has injected the following Seed Scenario:
    "{request.seed_context}"
    
    Here are the perspectives from your 5 specialized agents:
    Chef: {perspectives['chef']}
    Baker: {perspectives['baker']}
    Gardener: {perspectives['gardener']}
    Stylist: {perspectives['stylist']}
    Event Planner: {perspectives['event']}
    
    Synthesize these inputs into a single, cohesive Master Plan. Resolve any conflicts, ensure a unified vision, and present it elegantly.
    """
    
    master_plan = ""
    max_retries = 3
    delay = 2.0
    for attempt in range(max_retries):
        try:
            await asyncio.sleep(0.8)
            client = get_openai_client()
            synthesis_resp = await client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[{"role": "system", "content": "You are the Master Orchestrator AI."}, {"role": "user", "content": synthesis_prompt}],
                max_tokens=1500
            )
            master_plan = synthesis_resp.choices[0].message.content
            break
        except Exception as e:
            err_msg = str(e).lower()
            is_rate_limit = "429" in err_msg or "quota" in err_msg or "limit" in err_msg or "exhausted" in err_msg
            if is_rate_limit and attempt < max_retries - 1:
                logger.warning(f"Rate limit hit during Master Synthesis (attempt {attempt + 1}/{max_retries}). Retrying in {delay}s...")
                await asyncio.sleep(delay)
                delay *= 2
            else:
                logger.error(f"Error during synthesis: {e}")
                master_plan = f"Synthesis failed due to API constraints: {str(e)}"
                break
        
    return {
        "rag_context": rag_results,
        "perspectives": perspectives,
        "master_plan": master_plan
    }


@router.post("/seed/stream")
async def seed_injection_stream_endpoint(request: SeedInjectionRequest):
    """
    RAG-driven Seed Injection with Event Streaming (SSE):
    Streams status updates and progressive outputs for each agent,
    followed by the final master plan synthesis.
    """
    logger.info(f"Received Streaming Seed Injection Request: {request.seed_context}")

    async def event_generator():
        import json
        # 1. Fetch RAG Context
        yield "event: phase\ndata: " + json.dumps({"phase": "rag", "status": "started"}) + "\n\n"
        
        try:
            rag_results = await query_knowledge_base(query_str=request.seed_context, diet_filter="none", limit=3)
            yield "event: rag_result\ndata: " + json.dumps({"results": rag_results}) + "\n\n"
            rag_text = "\n\n".join([f"Source: {res['metadata'].get('title', 'Knowledge Base')}\nContent: {res['text']}" for res in rag_results])
        except Exception as e:
            logger.error(f"RAG search failed in seed: {e}")
            rag_results = []
            rag_text = ""
            yield "event: rag_result\ndata: " + json.dumps({"results": [], "error": str(e)}) + "\n\n"
            
        # Construct combined prompt for agents
        agent_prompt = f"Seed Context: {request.seed_context}\n\nRelevant Knowledge Base Context:\n{rag_text if rag_results else 'None found.'}\n\nPlease provide your unique perspective and contribution to this plan based on your expertise. Be concise."
        
        # 2. Gather perspectives sequentially with retry mechanism
        agent_ids = ["chef", "baker", "gardener", "stylist", "event"]
        perspectives = {}
        
        yield "event: phase\ndata: " + json.dumps({"phase": "agents", "status": "started"}) + "\n\n"
        
        async def fetch_perspective_with_retry(agent_id):
            agent = orchestrator.get_agent(agent_id)
            max_retries = 3
            delay = 3.5 # Increased base delay for better rate limit avoidance
            for attempt in range(max_retries):
                try:
                    # Spacer delay before each call to avoid concurrency rate spikes
                    await asyncio.sleep(2.0) # More spacing
                    resp = await agent.chat(message=agent_prompt, history=[])
                    return "success", resp
                except Exception as e:
                    err_msg = str(e).lower()
                    is_rate_limit = "429" in err_msg or "quota" in err_msg or "limit" in err_msg or "exhausted" in err_msg
                    if is_rate_limit and attempt < max_retries - 1:
                        logger.warning(f"Rate limit hit for agent '{agent_id}' (attempt {attempt + 1}/{max_retries}). Retrying in {delay}s...")
                        await asyncio.sleep(delay)
                        delay *= 2
                    else:
                        logger.error(f"Failed to generate perspective for agent '{agent_id}': {e}")
                        return "error", str(e)
            return "error", f"Failed to retrieve perspective after {max_retries} attempts due to API rate limits."

        for aid in agent_ids:
            status, content = await fetch_perspective_with_retry(aid)
            perspectives[aid] = content
            yield "event: agent_result\ndata: " + json.dumps({"agent_id": aid, "status": status, "content": content}) + "\n\n"

        # 3. Master Synthesis
        yield "event: phase\ndata: " + json.dumps({"phase": "synthesis", "status": "started"}) + "\n\n"
        
        synthesis_prompt = f"""
        You are the Master Orchestrator AI. A user has injected the following Seed Scenario:
        "{request.seed_context}"
        
        Here are the perspectives from your 5 specialized agents:
        Chef: {perspectives.get('chef', 'No content')}
        Baker: {perspectives.get('baker', 'No content')}
        Gardener: {perspectives.get('gardener', 'No content')}
        Stylist: {perspectives.get('stylist', 'No content')}
        Event Planner: {perspectives.get('event', 'No content')}
        
        Synthesize these inputs into a single, cohesive Master Plan. Resolve any conflicts, ensure a unified vision, and present it elegantly.
        """
        
        master_plan = ""
        max_retries = 3
        delay = 4.0
        for attempt in range(max_retries):
            try:
                await asyncio.sleep(2.0)
                client = get_openai_client()
                synthesis_resp = await client.chat.completions.create(
                    model=settings.OPENAI_MODEL,
                    messages=[{"role": "system", "content": "You are the Master Orchestrator AI."}, {"role": "user", "content": synthesis_prompt}],
                    max_tokens=1500
                )
                master_plan = synthesis_resp.choices[0].message.content
                yield "event: synthesis_result\ndata: " + json.dumps({"master_plan": master_plan}) + "\n\n"
                break
            except Exception as e:
                err_msg = str(e).lower()
                is_rate_limit = "429" in err_msg or "quota" in err_msg or "limit" in err_msg or "exhausted" in err_msg
                if is_rate_limit and attempt < max_retries - 1:
                    logger.warning(f"Rate limit hit during Master Synthesis (attempt {attempt + 1}/{max_retries}). Retrying in {delay}s...")
                    await asyncio.sleep(delay)
                    delay *= 2
                else:
                    logger.error(f"Error during synthesis: {e}")
                    master_plan = f"Synthesis failed due to API constraints: {str(e)}"
                    yield "event: synthesis_result\ndata: " + json.dumps({"master_plan": master_plan, "error": str(e)}) + "\n\n"
                    break
                    
        yield "event: done\ndata: {}\n\n"




@router.get("/rag/test")
async def test_retrieval(query: str, diet: Optional[str] = "none", limit: int = 3):
    """
    Retrieval Testing endpoint. Directly runs vector search on Qdrant
    and returns raw retrieved nodes with their text and matching metrics.
    """
    results = await query_knowledge_base(query_str=query, diet_filter=diet, limit=limit)
    return {
        "query": query,
        "diet_filter": diet,
        "results_count": len(results),
        "matches": results
    }


@router.post("/rag/ingest")
def trigger_ingestion(background_tasks: BackgroundTasks):
    """
    Asynchronously triggers ingestion of the default recipe knowledge base JSON
    in the background to prevent API blockages.
    """
    import os
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    data_path = os.path.join(base_dir, "data", "culinary_kb.json")
    
    from app.rag.ingest import ingest_recipes_async
    background_tasks.add_task(ingest_recipes_async, data_path)
    return {"message": "Knowledge base ingestion started asynchronously in the background."}


@router.get("/sessions")
def get_sessions():
    """
    Lists all session memories and active profiles.
    """
    return {"sessions": orchestrator.list_all_sessions()}


@router.post("/sessions/{session_id}/clear")
def clear_session(session_id: str):
    """
    Flushes the memory queue of a given session.
    """
    orchestrator.clear_session(session_id)
    return {"message": f"Session {session_id} memory cleared successfully."}


@router.get("/system/stats")
async def get_system_stats():
    """
    Returns system statistics, registered agents, tool definitions, 
    and vector DB collection sizes.
    """
    from app.config import settings
    from app.services.qdrant import get_qdrant_client, is_fallback_memory
    
    # 1. Gather Agent specs
    agents_spec = []
    for agent_id, agent in orchestrator.agents.items():
        agents_spec.append({
            "id": agent_id,
            "name": agent.name,
            "description": agent.description,
            "tools": [t["function"]["name"] for t in agent.get_tools()]
        })
        
    # 2. Gather session count
    sessions_count = len(orchestrator.sessions)
    
    # 3. Gather Vector DB point count
    vector_db_points = 0
    collection_status = "uninitialized"
    try:
        client = get_qdrant_client()
        collections = client.get_collections().collections
        exists = any(c.name == "chef_kb" for c in collections)
        if exists:
            info = client.get_collection("chef_kb")
            vector_db_points = info.points_count
            collection_status = "active"
        else:
            collection_status = "missing"
    except Exception as e:
        logger.error(f"Error gathering Qdrant collection stats: {e}")
        collection_status = f"error: {str(e)}"
        
    return {
        "status": "healthy",
        "active_agents": agents_spec,
        "sessions_count": sessions_count,
        "vector_db": {
            "collection": "chef_kb",
            "status": collection_status,
            "vectors_count": vector_db_points,
            "fallback_memory": is_fallback_memory()
        }
    }
