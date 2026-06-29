import json
import logging
from typing import AsyncGenerator, List, Dict, Any, Optional
from openai import AsyncOpenAI

from app.config import settings
from app.agents.base import BaseAgent
from app.rag.pipeline import query_knowledge_base
from app.tools.gardener_tools import diagnose_plant, generate_watering_schedule
from app.services.llm import get_openai_client

logger = logging.getLogger(__name__)

GARDENER_SYSTEM_PROMPT = """You are "Flora Root", a master gardening expert, botanist, and plant health consultant. Your mission is to provide accurate, comprehensive, and organic advice on cultivating houseplants, flowers, vegetables, shrubs, lawns, and container gardening.

RULES:
1. When asked for advice on growing a specific plant, ALWAYS present it in a beautifully formatted gardener's profile:
   - Common & Scientific Name
   - Difficulty Level, Sunlight & Water Needs
   - Aeration and Soil Mix Recommendations
   - Step-by-step planting and propagation steps
   - Helpful "Flora's Secret Tips" at the end.
2. Ground your advice in organic, sustainable, and eco-friendly gardening techniques. Avoid recommending harsh chemical pesticides unless absolutely necessary.
3. You have tools available (diagnose_plant, generate_watering_schedule). Use them when the user explicitly requests watering calendars or diagnoses for sick plants.
4. Maintain a warm, earthy, wise, and enthusiastic botanical expert persona. Use rich descriptions of soil, roots, foliage, and seasons.
"""

class GardenerAgent(BaseAgent):
    """
    Flora Root Gardener Agent.
    Specializes in organic gardening, botany science, soil physics, and plant health care.
    """
    def __init__(self):
        super().__init__(
            name="Flora Root",
            description="Botanist and organic gardening expert. Specializes in houseplants, organic pest control, and watering optimization.",
            system_prompt=GARDENER_SYSTEM_PROMPT
        )
        self.client = get_openai_client()

    def get_tools(self) -> List[Dict[str, Any]]:
        """
        Returns JSON tool definitions for OpenAI Function Calling.
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": "diagnose_plant",
                    "description": "Diagnoses common plant symptoms (yellow leaves, spots, wilting) and generates natural organic remedies.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "plant_type": {
                                "type": "string",
                                "description": "The common name of the plant (e.g., 'Tomato', 'Fiddle Leaf Fig')."
                            },
                            "symptoms": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "A list of visual symptoms (e.g., ['yellow leaves', 'brown dry tips', 'wilting stems'])."
                            },
                            "sun_exposure": {
                                "type": "string",
                                "description": "Approximate sun exposure (e.g. 'direct bright sunlight', 'shaded indoor', 'partial shadow')."
                            }
                        },
                        "required": ["plant_type", "symptoms", "sun_exposure"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "generate_watering_schedule",
                    "description": "Computes a personalized watering frequency schedule based on plant type, container, climate, and soil aeration.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "plant_type": {
                                "type": "string",
                                "description": "Type of plant (e.g., 'Jade succulent', 'Maidenhair fern')."
                            },
                            "container_type": {
                                "type": "string",
                                "description": "Type of pot/container (e.g., 'terracotta clay', 'plastic container', 'raised bed ground')."
                            },
                            "climate": {
                                "type": "string",
                                "description": "Local weather/room climate (e.g., 'hot dry room', 'cool humid patio')."
                            },
                            "soil_type": {
                                "type": "string",
                                "description": "Aeration/makeup of soil (e.g., 'fast-draining sandy mix', 'dense clay garden soil')."
                            }
                        },
                        "required": ["plant_type", "container_type", "climate", "soil_type"]
                    }
                }
            }
        ]

    async def _execute_tool(self, tool_name: str, args: Dict[str, Any]) -> str:
        """
        Routing and execution of gardener tools.
        """
        try:
            if tool_name == "diagnose_plant":
                return diagnose_plant(
                    args["plant_type"],
                    args["symptoms"],
                    args["sun_exposure"]
                )
            elif tool_name == "generate_watering_schedule":
                return generate_watering_schedule(
                    args["plant_type"],
                    args["container_type"],
                    args["climate"],
                    args["soil_type"]
                )
            else:
                return f"Error: Tool '{tool_name}' is not supported by Flora Root."
        except Exception as e:
            logger.error(f"Error executing gardener tool {tool_name}: {e}")
            return f"Error: Failed to execute tool '{tool_name}' due to error: {str(e)}"

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
        if diet_preference and diet_preference.lower() != "none":
            system_message += f"\n\nCRITICAL INSTRUCTION: The user has an active dietary/lifestyle preference set to: {diet_preference.upper()}. You MUST strictly adhere to this preference in ALL your advice, recipes, and ingredient suggestions. Do not suggest anything that violates this preference."

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
        if diet_preference and diet_preference.lower() != "none":
            system_message += f"\n\nCRITICAL INSTRUCTION: The user has an active dietary/lifestyle preference set to: {diet_preference.upper()}. You MUST strictly adhere to this preference in ALL your advice, recipes, and ingredient suggestions. Do not suggest anything that violates this preference."

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
                        tool_calls_to_assemble.append({
                            "id": tc.id or "",
                            "name": tc.function.name or "",
                            "arguments": ""
                        })
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
                yield f"\n\n*Error: Failed to parse gardener tool '{name}' arguments.*"
                return

            yield f"\n\n*Executing botanical tool: **{name}**...*\n\n"
            tool_output = await self._execute_tool(name, args)
            yield tool_output + "\n\n"
            
            messages.append({
                "role": "assistant",
                "content": None,
                "tool_calls": [{
                    "id": tc["id"],
                    "type": "function",
                    "function": {
                        "name": tc["name"],
                        "arguments": tc["arguments"]
                    }
                }]
            })
            messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "name": tc["name"],
                "content": tool_output
            })
            
            final_stream = await self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=messages,
                stream=True
            )
            async for chunk in final_stream:
                delta = chunk.choices[0].delta
                if delta.content:
                    yield delta.content
