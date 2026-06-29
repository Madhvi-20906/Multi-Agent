import json
import logging
from typing import AsyncGenerator, List, Dict, Any, Optional

from app.config import settings
from app.agents.base import BaseAgent
from app.rag.pipeline import query_knowledge_base
from app.tools.event_tools import build_event_budget, generate_event_timeline
from app.services.llm import get_openai_client

logger = logging.getLogger(__name__)

EVENT_SYSTEM_PROMPT = """You are "Vivid Bloom", a luxury event planner and social gathering curator with 15+ years of experience orchestrating unforgettable weddings, corporate galas, intimate dinners, birthday celebrations, and social events worldwide.

RULES:
1. When asked to plan an event, ALWAYS present a comprehensive "Event Blueprint" that includes:
   - Event Theme & Vision
   - Guest Experience Journey (arrival → programme → farewell)
   - Venue & Décor Direction
   - Catering & Beverage Strategy
   - Entertainment & Activity Recommendations
   - Timeline & Logistics Overview
   - "Vivid Bloom's Touch" — signature wow-factor ideas at the end.
2. You have tools available: `build_event_budget` and `generate_event_timeline`. Use them when users need budget breakdowns or detailed day-of schedules.
3. Always consider the full guest experience — from the first invitation received to the last memory made.
4. Provide vendor negotiation tips, contingency plans, and insider industry knowledge that clients wouldn't find in a basic search.
5. Maintain an elegant, enthusiastic, and detail-obsessed persona. You live for the magic in the details.
"""

class EventAgent(BaseAgent):
    """
    Vivid Bloom Event Planner Agent.
    Specialises in event budgeting, timeline planning, vendor coordination, and guest experience design.
    """
    def __init__(self):
        super().__init__(
            name="Vivid Bloom",
            description="Luxury event planner and social gathering curator. Specialises in budgets, timelines, vendor strategy, and unforgettable guest experiences.",
            system_prompt=EVENT_SYSTEM_PROMPT
        )
        self.client = get_openai_client()

    def get_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "build_event_budget",
                    "description": "Generates a detailed event budget breakdown across all major spending categories based on event type, guest count, total budget, and priority areas.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "event_type": {
                                "type": "string",
                                "description": "Type of event (e.g., 'wedding', 'birthday party', 'corporate event', 'baby shower', 'anniversary dinner', 'graduation party')."
                            },
                            "guest_count": {
                                "type": "integer",
                                "description": "Total number of expected guests."
                            },
                            "total_budget_usd": {
                                "type": "number",
                                "description": "Total event budget in US dollars (e.g., 15000.0)."
                            },
                            "priority_categories": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of categories to prioritise and allocate more budget toward (e.g., ['photography', 'florals'])."
                            },
                            "include_vendor_tips": {
                                "type": "boolean",
                                "description": "Whether to include pro vendor negotiation and booking tips for each category. Defaults to true."
                            }
                        },
                        "required": ["event_type", "guest_count", "total_budget_usd", "priority_categories"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "generate_event_timeline",
                    "description": "Generates a complete event day-of timeline with setup, reception, programme, and wrap-up phases, customised to the event type and key activities.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "event_type": {
                                "type": "string",
                                "description": "Type of event (e.g., 'wedding', 'birthday party', 'corporate event')."
                            },
                            "event_date": {
                                "type": "string",
                                "description": "The event date as a human-readable string (e.g., 'Saturday, June 14, 2025')."
                            },
                            "venue_type": {
                                "type": "string",
                                "description": "Description of the venue (e.g., 'outdoor garden', 'hotel ballroom', 'rooftop terrace', 'private home')."
                            },
                            "key_activities": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of key programme items in order (e.g., ['cocktail hour', 'dinner service', 'speeches', 'first dance', 'cake cutting'])."
                            },
                            "start_time": {
                                "type": "string",
                                "description": "Event start time for guests (e.g., '6:00 PM', '7:30 PM'). Defaults to 6:00 PM."
                            },
                            "duration_hours": {
                                "type": "number",
                                "description": "Total duration of the event in hours (e.g., 4.0 for a 4-hour reception)."
                            }
                        },
                        "required": ["event_type", "event_date", "venue_type", "key_activities"]
                    }
                }
            }
        ]

    async def _execute_tool(self, tool_name: str, args: Dict[str, Any]) -> str:
        try:
            if tool_name == "build_event_budget":
                return build_event_budget(
                    args["event_type"],
                    int(args["guest_count"]),
                    float(args["total_budget_usd"]),
                    args.get("priority_categories", []),
                    args.get("include_vendor_tips", True)
                )
            elif tool_name == "generate_event_timeline":
                return generate_event_timeline(
                    args["event_type"],
                    args["event_date"],
                    args["venue_type"],
                    args.get("key_activities", []),
                    args.get("start_time", "6:00 PM"),
                    float(args.get("duration_hours", 4.0))
                )
            else:
                return f"Error: Tool '{tool_name}' is not supported by Vivid Bloom."
        except Exception as e:
            logger.error(f"Error executing event tool {tool_name}: {e}")
            return f"Error: Failed to execute tool '{tool_name}': {str(e)}"

    async def chat(
        self,
        message: str,
        history: List[Dict[str, str]],
        diet_preference: Optional[str] = None,
        **kwargs
    ) -> str:
        # Retrieve relevant context from RAG
        rag_results = await query_knowledge_base(message, diet_filter=diet_preference)
        context_str = ""
        if rag_results:
            context_str = "\nRetrieved Knowledge Base Context:\n"
            for res in rag_results:
                context_str += f"\n---\n{res['text']}\n---\n"

        system_message = self.system_prompt
        if context_str:
            system_message += context_str

        messages = [{"role": "system", "content": system_message}]
        for h in history:
            messages.append({"role": h["role"], "content": h["content"]})
        messages.append({"role": "user", "content": message})

        response = await self.client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=messages,
            tools=self.get_tools(),
            tool_choice="auto"
        )
        response_message = response.choices[0].message

        if response_message.tool_calls:
            tool_call = response_message.tool_calls[0]
            name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)
            tool_output = await self._execute_tool(name, args)
            messages.append(response_message)
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": name,
                "content": tool_output
            })
            final_response = await self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=messages
            )
            return final_response.choices[0].message.content

        return response_message.content

    async def chat_stream(
        self,
        message: str,
        history: List[Dict[str, str]],
        diet_preference: Optional[str] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        # Retrieve relevant context from RAG
        rag_results = await query_knowledge_base(message, diet_filter=diet_preference)
        context_str = ""
        if rag_results:
            context_str = "\nRetrieved Knowledge Base Context:\n"
            for res in rag_results:
                context_str += f"\n---\n{res['text']}\n---\n"

        system_message = self.system_prompt
        if context_str:
            system_message += context_str

        messages = [{"role": "system", "content": system_message}]
        for h in history:
            messages.append({"role": h["role"], "content": h["content"]})
        messages.append({"role": "user", "content": message})

        response_stream = await self.client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=messages,
            tools=self.get_tools(),
            tool_choice="auto",
            stream=True
        )

        tool_calls_to_assemble = []
        async for chunk in response_stream:
            delta = chunk.choices[0].delta
            if delta.content:
                yield delta.content
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index if tc.index is not None else 0
                    if len(tool_calls_to_assemble) <= idx:
                        tool_calls_to_assemble.append({"id": tc.id or "", "name": tc.function.name or "", "arguments": ""})
                    if tc.id:
                        tool_calls_to_assemble[idx]["id"] = tc.id
                    if tc.function and tc.function.name:
                        tool_calls_to_assemble[idx]["name"] = tc.function.name
                    if tc.function and tc.function.arguments:
                        tool_calls_to_assemble[idx]["arguments"] += tc.function.arguments

        if tool_calls_to_assemble:
            tc = tool_calls_to_assemble[0]
            name = tc["name"]
            try:
                args = json.loads(tc["arguments"])
            except Exception as e:
                yield f"\n\n*Error: Failed to parse event tool '{name}' arguments.*"
                return

            yield f"\n\n*Executing event planning tool: **{name}**...*\n\n"
            tool_output = await self._execute_tool(name, args)
            yield tool_output + "\n\n"

            messages.append({
                "role": "assistant",
                "content": None,
                "tool_calls": [{"id": tc["id"], "type": "function", "function": {"name": tc["name"], "arguments": tc["arguments"]}}]
            })
            messages.append({"role": "tool", "tool_call_id": tc["id"], "name": tc["name"], "content": tool_output})

            final_stream = await self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=messages,
                stream=True
            )
            async for chunk in final_stream:
                delta = chunk.choices[0].delta
                if delta.content:
                    yield delta.content
