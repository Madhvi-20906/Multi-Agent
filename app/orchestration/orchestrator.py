import uuid
import logging
from typing import Dict, Any, List, Optional
from app.agents.base import BaseAgent
from app.agents.chef import ChefAgent
from app.agents.baker import BakerAgent
from app.agents.gardener import GardenerAgent
from app.agents.stylist import StylistAgent
from app.agents.event import EventAgent

logger = logging.getLogger(__name__)

class MultiAgentOrchestrator:
    """
    Central Orchestration Layer that registers AI Agents,
    manages user sessions in-memory, tracks conversation history,
    and dynamically routes requests to the appropriate agent.
    """
    def __init__(self):
        self.agents: Dict[str, BaseAgent] = {}
        self.sessions: Dict[str, Dict[str, Any]] = {}
        
        # Self-register Agents immediately
        self.register_agent("chef", ChefAgent())
        self.register_agent("baker", BakerAgent())
        self.register_agent("gardener", GardenerAgent())
        self.register_agent("stylist", StylistAgent())
        self.register_agent("event", EventAgent())
        logger.info("Initialized Orchestrator and registered Chef, Baker, Gardener, Stylist, and Event Agents.")

    def register_agent(self, agent_id: str, agent: BaseAgent):
        """
        Registers an agent in the active multi-agent pool.
        """
        self.agents[agent_id.lower()] = agent
        logger.info(f"Successfully registered agent: '{agent_id}'")

    def get_agent(self, agent_id: str) -> BaseAgent:
        """
        Retrieves agent instance by ID. Defaults to Chef Agent if ID not found.
        """
        normalized_id = agent_id.lower()
        if normalized_id in self.agents:
            return self.agents[normalized_id]
        
        logger.warning(f"Agent '{agent_id}' not found. Defaulting to Chef Agent ('chef').")
        return self.agents["chef"]

    def get_or_create_session(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Retrieves an existing session's history and configurations, or spawns a new one.
        """
        if not session_id or session_id not in self.sessions:
            new_id = session_id or str(uuid.uuid4())
            self.sessions[new_id] = {
                "session_id": new_id,
                "history": [],
                "active_agent": "chef",
                "diet_preference": "none",
                "title": "New Culinary Session"
            }
            logger.info(f"Created new session with ID: {new_id}")
            return self.sessions[new_id]
            
        return self.sessions[session_id]

    def add_message(self, session_id: str, role: str, content: str):
        """
        Appends a message to a session's history.
        """
        session = self.get_or_create_session(session_id)
        session["history"].append({"role": role, "content": content})
        
        # Auto-update session title based on the first user query
        if len(session["history"]) == 1 and role == "user":
            title = content[:30] + "..." if len(content) > 30 else content
            session["title"] = title

    def update_session_diet(self, session_id: str, diet: str) -> Dict[str, Any]:
        """
        Sets dietary restriction filter for RAG queries in a session.
        """
        session = self.get_or_create_session(session_id)
        session["diet_preference"] = diet.strip().lower()
        logger.info(f"Session {session_id} diet preference updated to: {diet}")
        return session

    def update_session_agent(self, session_id: str, agent_id: str) -> Dict[str, Any]:
        """
        Routes the active session conversation to a new agent.
        """
        session = self.get_or_create_session(session_id)
        session["active_agent"] = agent_id.strip().lower()
        logger.info(f"Session {session_id} active agent set to: {agent_id}")
        return session

    def clear_session(self, session_id: str):
        """
        Clears chat memory of a session.
        """
        if session_id in self.sessions:
            self.sessions[session_id]["history"] = []
            logger.info(f"Cleared history for session {session_id}")

    def list_all_sessions(self) -> List[Dict[str, Any]]:
        """
        Lists all active sessions with details.
        """
        return list(self.sessions.values())

# Global Orchestrator Instance
orchestrator = MultiAgentOrchestrator()
