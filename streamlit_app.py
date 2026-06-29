import sys
import os
import asyncio
from dotenv import load_dotenv

# 1. Setup paths so backend modules can be imported
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

# Load environment variables from backend/.env if available
load_dotenv(os.path.join(os.path.dirname(__file__), "backend", ".env"))

import streamlit as st
from app.orchestration.orchestrator import MultiAgentOrchestrator
from app.services.qdrant import get_qdrant_client
from app.rag.pipeline import CHEF_COLLECTION_NAME
from app.rag.ingest import ingest_recipes

# 2. Initialize Page Config
st.set_page_config(
    page_title="Allora - Multi-Agent AI Platform",
    page_icon="🍳",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 3. Custom CSS styling to recreate the premium leather/parchment/brass design
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400..900;1,400..900&family=Outfit:wght@100..900&display=swap');
    
    /* Overall app container */
    .stApp {
        background-color: #1a2a1a !important; /* Leather Green */
        color: #EAE0D3 !important;
        font-family: 'Outfit', sans-serif;
    }
    
    /* Main Header Brass Plate */
    .brass-plate {
        background: linear-gradient(135deg, #d4af37 0%, #aa8c2c 50%, #80661c 100%);
        border: 2px solid #5a4010;
        border-radius: 8px;
        padding: 15px 30px;
        text-align: center;
        color: #1a2a1a !important;
        font-family: 'Playfair Display', serif;
        font-weight: 800;
        font-size: 24px;
        margin-bottom: 25px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.4);
        position: relative;
        text-shadow: 1px 1px 0px rgba(255, 255, 255, 0.4);
    }
    
    .brass-plate::before, .brass-plate::after {
        content: '•';
        position: absolute;
        top: 50%;
        transform: translateY(-50%);
        color: #1a2a1a;
        font-size: 20px;
    }
    .brass-plate::before { left: 15px; }
    .brass-plate::after { right: 15px; }

    /* Sidebar styled like Parchment */
    [data-testid="stSidebar"] {
        background-color: #f4edd8 !important; /* Parchment */
        border-right: 8px solid #3A2A1A !important;
        color: #3A2A1A !important;
    }
    
    [data-testid="stSidebar"] .stMarkdown, [data-testid="stSidebar"] p, [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3, [data-testid="stSidebar"] label {
        color: #3A2A1A !important;
    }
    
    /* Sidebar Branding Header */
    .sidebar-branding {
        padding: 15px 0;
        border-bottom: 2px solid rgba(58, 42, 26, 0.2);
        margin-bottom: 20px;
        text-align: center;
    }
    
    .sidebar-logo {
        width: 60px;
        height: 60px;
        border-radius: 50%;
        background-color: #2b3e2d;
        border: 2px dashed #d4af37;
        display: flex;
        align-items: center;
        justify-content: center;
        margin: 0 auto 10px auto;
        color: #d4af37;
        font-size: 28px;
    }
    
    .sidebar-title {
        font-family: 'Playfair Display', serif;
        font-size: 28px;
        font-weight: 900;
        color: #3A2A1A;
        margin: 0;
    }
    
    .sidebar-subtitle {
        font-size: 10px;
        text-transform: uppercase;
        letter-spacing: 2px;
        color: #5A4027;
        font-weight: bold;
        margin-top: 2px;
    }

    /* Buttons styled like Leather */
    .stButton>button {
        background-color: #5C4033 !important; /* Leather Brown */
        color: #EAE0D3 !important;
        border: 2px solid #3A2A1A !important;
        border-radius: 8px !important;
        font-family: 'Playfair Display', serif !important;
        font-weight: bold !important;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.3) !important;
        transition: all 0.2s ease !important;
        width: 100% !important;
    }
    
    .stButton>button:hover {
        transform: scale(1.02) !important;
        background-color: #704F3F !important;
        border-color: #d4af37 !important;
        color: #FFFFFF !important;
    }
    
    .stButton>button:active {
        transform: scale(0.98) !important;
    }
    
    /* Quick Action suggestions */
    .quick-suggestion-btn button {
        background-color: rgba(234, 224, 211, 0.1) !important;
        color: #EAE0D3 !important;
        border: 1px solid rgba(234, 224, 211, 0.3) !important;
        border-radius: 12px !important;
        padding: 8px 12px !important;
        font-size: 13px !important;
        font-family: 'Playfair Display', serif !important;
        text-align: left !important;
        margin-bottom: 8px !important;
        width: auto !important;
    }
    .quick-suggestion-btn button:hover {
        border-color: #d4af37 !important;
        background-color: rgba(234, 224, 211, 0.2) !important;
    }

    /* Custom chat style overrides */
    .stChatMessage[data-testid="stChatMessage"] {
        border-radius: 16px !important;
        padding: 15px !important;
        margin-bottom: 12px !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.15) !important;
    }
    
    /* User chat bubble: Leather Brown */
    .stChatMessage[data-testid="stChatMessage"]:nth-child(even) {
        background-color: #5C4033 !important;
        color: #EAE0D3 !important;
        border: 1px solid #7A5537 !important;
    }
    
    /* Assistant chat bubble: Parchment */
    .stChatMessage[data-testid="stChatMessage"]:nth-child(odd) {
        background-color: #f4edd8 !important;
        color: #3A2A1A !important;
        border: 1px solid #D5C6B3 !important;
    }
    
    /* Input box formatting */
    .stChatInput {
        border-radius: 30px !important;
        border: 2px solid #2a1810 !important;
        background-color: #3a2a1a !important;
        color: #EAE0D3 !important;
    }
    
</style>
""", unsafe_allow_html=True)

# 4. Initialize Orchestrator Singleton
@st.cache_resource
def get_orchestrator():
    return MultiAgentOrchestrator()

orchestrator = get_orchestrator()

# 5. Session State Setup
if "history" not in st.session_state:
    st.session_state.history = []
if "session_id" not in st.session_state:
    import uuid
    st.session_state.session_id = str(uuid.uuid4())
if "active_agent" not in st.session_state:
    st.session_state.active_agent = "chef"
if "diet_preference" not in st.session_state:
    st.session_state.diet_preference = "none"

# Helper to run async generator in Streamlit's sync environment
def iterate_async_generator(async_gen):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    iterator = async_gen.__aiter__()
    while True:
        try:
            chunk = loop.run_until_complete(iterator.__anext__())
            yield chunk
        except StopAsyncIteration:
            break
        except Exception as e:
            yield f"\n\n*Error during streaming: {str(e)}*"
            break

# 6. SIDEBAR: Parchment background with controls
with st.sidebar:
    st.markdown("""
    <div class="sidebar-branding">
        <div class="sidebar-logo">🍳</div>
        <div class="sidebar-title">Allora</div>
        <div class="sidebar-subtitle">5 Agents • Endless Possibilities</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Active Agent Configuration
    st.markdown("### 🤖 Active Workspace")
    agent_options = {
        "chef": "Chef Gasto (Culinary RAG & Advice)",
        "gardener": "Flora Root (Botany & Soil Diagnostics)",
        "baker": "Artisan Loaf (Baking & Hydration math)",
        "stylist": "Sartorial Thread (Fashion Curation)",
        "event": "Vivid Bloom (Timeline & Event Planner)"
    }
    selected_agent = st.selectbox(
        "Choose Agent",
        options=list(agent_options.keys()),
        format_func=lambda x: agent_options[x],
        index=list(agent_options.keys()).index(st.session_state.active_agent)
    )
    if selected_agent != st.session_state.active_agent:
        st.session_state.active_agent = selected_agent
        # Clear or keep history? Let's just update active agent in session
        orchestrator.update_session_agent(st.session_state.session_id, selected_agent)
        st.rerun()
        
    # Dietary Preferences
    st.markdown("### 🥗 Dietary Preference")
    diet_options = {
        "none": "Standard Diet (No Filters)",
        "gluten-free": "Gluten-Free",
        "vegan": "Vegan",
        "keto": "Keto / Low-Carb",
        "vegetarian": "Vegetarian"
    }
    selected_diet = st.selectbox(
        "Choose Preference",
        options=list(diet_options.keys()),
        format_func=lambda x: diet_options[x],
        index=list(diet_options.keys()).index(st.session_state.diet_preference)
    )
    if selected_diet != st.session_state.diet_preference:
        st.session_state.diet_preference = selected_diet
        orchestrator.update_session_diet(st.session_state.session_id, selected_diet)
        st.rerun()

    # Session Control Buttons
    st.markdown("### ⚙️ Workspace Actions")
    if st.button("New Session / Reset"):
        import uuid
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.history = []
        st.rerun()
        
    if st.button("Clear Conversation"):
        st.session_state.history = []
        st.rerun()

    # Diagnostics
    st.markdown("### 📊 Platform Diagnostics")
    with st.expander("Show Details"):
        # Connection check
        try:
            client = get_qdrant_client()
            cols = client.get_collections().collections
            has_chef_kb = any(c.name == CHEF_COLLECTION_NAME for c in cols)
            if has_chef_kb:
                count = client.get_collection(CHEF_COLLECTION_NAME).points_count
                st.success(f"Qdrant Connected ({count} records)")
            else:
                st.warning("Collection 'chef_kb' missing")
                count = 0
        except Exception as e:
            st.error(f"Vector Database Refused: {str(e)}")
            count = 0
            
        # Ingestion Button
        if count == 0:
            st.warning("Vector database is empty. Auto-ingest seed data now.")
            if st.button("Ingest Seed Recipes"):
                with st.spinner("Ingesting culinary database..."):
                    base_dir = os.path.dirname(os.path.abspath(__file__))
                    data_path = os.path.join(base_dir, "data", "culinary_kb.json")
                    if os.path.exists(data_path):
                        ingest_recipes(data_path)
                        st.success("Successfully ingested seed data!")
                        st.rerun()
                    else:
                        st.error(f"Seed file not found at {data_path}")
        else:
            if st.button("Re-Ingest Data"):
                with st.spinner("Re-ingesting culinary database..."):
                    base_dir = os.path.dirname(os.path.abspath(__file__))
                    data_path = os.path.join(base_dir, "data", "culinary_kb.json")
                    if os.path.exists(data_path):
                        ingest_recipes(data_path)
                        st.success("Successfully ingested seed data!")
                        st.rerun()
                    else:
                        st.error(f"Seed file not found at {data_path}")

# 7. MAIN CHAT AREA
agent_title_mapping = {
    "chef": "Chef Gasto Workspace",
    "gardener": "Flora Root Workspace",
    "baker": "Artisan Loaf Workspace",
    "stylist": "Sartorial Thread Workspace",
    "event": "Vivid Bloom Workspace"
}
st.markdown(f'<div class="brass-plate">{agent_title_mapping[st.session_state.active_agent]}</div>', unsafe_allow_html=True)

# 8. Render message history
for msg in st.session_state.history:
    avatar_char = "👤" if msg["role"] == "user" else "🤖"
    with st.chat_message(msg["role"], avatar=avatar_char):
        st.markdown(msg["content"])

# 9. Handle Suggestions / Pre-prompts
agent_prompts = {
    "chef": [
        "Scale ingredients of pancake recipe for 6 guests",
        "What gluten-free recipes do we have in the knowledge base?",
        "Convert 2.5 cups of almond flour to grams",
        "Estimate macros for a serving of avocado toast with eggs"
    ],
    "gardener": [
        "Generate a watering schedule for a fiddle leaf fig and snake plant",
        "Diagnose yellow spots on my monstera leaves",
        "Which plants grow best together in a sunny raised bed?",
        "How do I lower the pH of my alkaline garden soil?"
    ],
    "baker": [
        "Calculate bakers percentages for a 70% hydration sourdough dough",
        "How do I adjust rising time if my kitchen is 80 degrees?",
        "Suggest gluten-free flour substitutes for cookies",
        "Create a proofing schedule for overnight baguettes"
    ],
    "stylist": [
        "Create a cohesive color palette based on forest green and copper",
        "Build a smart-casual capsule wardrobe for a spring trip",
        "What dress code is appropriate for a rustic garden wedding?",
        "Suggest fabric matches for a warm oak table setting theme"
    ],
    "event": [
        "Generate a detailed timeline for a 4-hour evening dinner party",
        "Build an event budget allocation for $5,000 for 40 guests",
        "Suggest a seating arrangement strategy for conflicting families",
        "What are the key planning steps for a micro-wedding?"
    ]
}

suggested_query = None
if len(st.session_state.history) == 0:
    st.markdown("#### Suggested Topics")
    cols = st.columns(2)
    prompts_list = agent_prompts.get(st.session_state.active_agent, [])
    for idx, prompt_text in enumerate(prompts_list):
        col = cols[idx % 2]
        with col:
            st.markdown(f'<div class="quick-suggestion-btn">', unsafe_allow_html=True)
            if st.button(prompt_text, key=f"sugg_{idx}"):
                suggested_query = prompt_text
            st.markdown('</div>', unsafe_allow_html=True)

# 10. Handle Input
user_query = st.chat_input("Send a message to the active agent...")

# If suggestion was clicked, override query
if suggested_query:
    user_query = suggested_query

if user_query:
    # Render user query
    with st.chat_message("user", avatar="👤"):
        st.markdown(user_query)
    st.session_state.history.append({"role": "user", "content": user_query})
    
    # Retrieve agent class from orchestrator
    agent = orchestrator.get_agent(st.session_state.active_agent)
    
    # Set up message history for agent input
    history_input = []
    # Take last 10 messages for context window
    for h in st.session_state.history[:-1]:
        history_input.append({"role": h["role"], "content": h["content"]})
        
    # Render agent bubble placeholder and stream contents
    with st.chat_message("assistant", avatar="🤖"):
        placeholder = st.empty()
        full_response = ""
        
        # Get stream generator
        async_gen = agent.chat_stream(
            message=user_query,
            history=history_input,
            diet_preference=st.session_state.diet_preference
        )
        
        # Stream response
        for chunk in iterate_async_generator(async_gen):
            full_response += chunk
            placeholder.markdown(full_response + "▌")
        
        placeholder.markdown(full_response)
        st.session_state.history.append({"role": "assistant", "content": full_response})
        st.rerun()
