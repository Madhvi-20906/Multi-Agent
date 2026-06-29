# AURA - Multi-Agent AI Platform & RAG Kitchen Assistant

Welcome to **Aura**, an enterprise-ready, modular AI platform featuring a sophisticated multi-agent orchestration layer, robust contextual memory, and state-of-the-art Retrieval-Augmented Generation (RAG).

This implementation provides a completely operational, high-performance integration of:
- **FastAPI** for asynchronous streaming REST and Server-Sent Events (SSE) interfaces.
- **LlamaIndex & Qdrant** for semantic retrieval pipelines with real-time metadata filtering.
- **Next.js & Tailwind CSS** for a gorgeous dark-themed client workspace with rich animated cards, quick suggestions, and custom metric scaling tool buttons.

---

## Technical Stack Architecture

```
                               ┌──────────────────────────┐
                               │       Next.js Web UI     │
                               └────────────┬─────────────┘
                                            │
                                 SSE Token Stream / REST
                                            │
                                            ▼
                               ┌──────────────────────────┐
                               │   FastAPI Orchestrator   │
                               └────────────┬─────────────┘
                                            │
                                            ├──────────────────────────┐
                                            ▼                          ▼
                               ┌──────────────────────────┐ ┌────────────────────┐
                               │        Chef Agent        │ │  (Future Agents)   │
                               │  (System prompt & memory)│ │ Gardener, Baker... │
                               └────────────┬─────────────┘ └────────────────────┘
                                            │
                                            ├──────────────────────────┐
                                            ▼                          ▼
                               ┌──────────────────────────┐ ┌────────────────────┐
                               │    LlamaIndex RAG        │ │     Chef Tools     │
                               │   (Metadata filters)     │ │ Scaler, Converter│
                               └────────────┬─────────────┘ └────────────────────┘
                                            │
                                            ▼
                               ┌──────────────────────────┐
                               │     Qdrant Vector DB     │
                               └──────────────────────────┘
```

---

## Project Folder Structure

- `/backend` - Contains FastAPI REST and streaming webserver controllers.
  - `/app/agents` - Inherits from `BaseAgent` class to enable multi-agent scaling.
  - `/app/orchestration` - Thread-safe user session state registers and dynamic memory managers.
  - `/app/rag` - LlamaIndex connection adapters, custom metadata filters, and data upload pipelines.
  - `/app/tools` - Specialized Python execution engines (ingredient scaling, unit metric conversions, nutrition calculators).
  - `/app/services` - Central OpenAI and Qdrant network providers.
- `/frontend` - Contains a rich, dark-themed responsive Next.js application dashboard.
- `/data` - Pre-packaged seed data (`culinary_kb.json`) with culinary recipes, prep times, and dietary information for immediate RAG indexing.
- `docker-compose.yml` - Launches backend, frontend, and database services in harmony.

---

## Local Setup & Quickstart (No Docker Required)

Aura features an **automatic local fallback mode**! If you don't have Qdrant running as a Docker service, the backend will dynamically launch a high-performance in-memory client (`:memory:`) and index data locally, so you are operational in seconds.

### Step 1: Run the Backend Server

1. Open your terminal and navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create a virtual environment and activate it:
   ```bash
   python -m venv venv
   # On Windows:
   .\venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy environment settings and specify your OpenAI API key:
   ```bash
   copy .env.example .env
   ```
   Open the `.env` file and set:
   ```env
   OPENAI_API_KEY=sk-proj-yourActualOpenAiKey...
   # Set QDRANT_URL to :memory: to run locally without Qdrant installed
   QDRANT_URL=:memory:
   ```
5. Run the FastAPI application:
   ```bash
   python app/main.py
   ```
   The backend will start on **`http://localhost:8000`** and automatically parse and index the seed recipes in `data/culinary_kb.json`.

---

### Step 2: Run the Next.js Frontend

1. In a new terminal window, navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install npm dependencies:
   ```bash
   npm install
   ```
3. Set your environment variables (optional - defaults to localhost:8000):
   ```bash
   # On Windows:
   set NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
   ```
4. Run the Next.js client:
   ```bash
   npm run dev
   ```
   Open **`http://localhost:3000`** to view your beautiful new RAG AI workspace!

---

## Docker Compose Quickstart (Full Containerized Environment)

To run the complete ecosystem (including a permanent persistent Qdrant database) in one command:

1. Place your `OPENAI_API_KEY` inside a `.env` file in the **root** folder:
   ```env
   OPENAI_API_KEY=sk-proj-yourActualOpenAiKey...
   ```
2. Launch Docker Compose:
   ```bash
   docker-compose up --build
   ```
3. Services will run on:
   - **Frontend UI:** `http://localhost:3000`
   - **FastAPI API:** `http://localhost:8000`
   - **Qdrant DB Console:** `http://localhost:6333/dashboard`

---

## Engineering Customizations & Expansion

### Adding a New Agent Pod (e.g., Gardener or Baker)
Aura is built specifically for future agent expansion:
1. Create a new file in `backend/app/agents/gardener.py` inheriting from `BaseAgent`.
2. Implement your gardener system prompt and specific tools:
   ```python
   from app.agents.base import BaseAgent

   class GardenerAgent(BaseAgent):
       def __init__(self):
           super().__init__(
               name="Flora Root",
               description="Botany & soil diagnostics expert.",
               system_prompt="Your gardening prompts..."
           )
       # Implement chat, chat_stream, and get_tools...
   ```
3. Register the agent inside the `MultiAgentOrchestrator` constructor in `backend/app/orchestration/orchestrator.py`:
   ```python
   from app.agents.gardener import GardenerAgent
   self.register_agent("gardener", GardenerAgent())
   ```
4. Remove the lock badge in the frontend `page.tsx` sidebar to enable routing conversations to it dynamically!

### Scaling the Vector Database (Qdrant)
When transitioning to production with millions of recipes or files:
- **Indexing Options**: Adjust `vectors_config` distance criteria (Cosine vs Euclidean) in `qdrant.py`.
- **Quantization**: Enable Scalar Quantization (SQ) or Product Quantization (PQ) in Qdrant's collection parameters to reduce vector storage RAM usage by up to 60%.
- **Hybrid Search**: Combine dense semantic search with sparse BM25 token matching using Qdrant's sparse indexes to optimize exact ingredient matching.

---

## Production Security Measures
- **Rate-Limiting**: Ready for integration using `slowapi` or FastAPI dependency injection.
- **Input Validation**: Guaranteed safe payloads using strictly typed Pydantic structures.
- **CORS Guards**: Configured allowing specific, authorized client origins in production `main.py`.
- **Data Isolation**: User chats are isolated using secure `session_id` mapping.
