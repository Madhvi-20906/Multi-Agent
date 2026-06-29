import json
import logging
from typing import AsyncGenerator, List, Dict, Any, Optional
from openai import AsyncOpenAI

from app.config import settings
from app.agents.base import BaseAgent
from app.rag.pipeline import query_knowledge_base
from app.tools.baker_tools import calculate_bakers_percentage, adjust_rise_time
from app.services.llm import get_openai_client

logger = logging.getLogger(__name__)

BAKER_SYSTEM_PROMPT = """You are "Artisan Loaf", a master pastry chef and artisanal sourdough bread baker. Your mission is to provide accurate, professional, and practical advice on baking sourdough, yeast breads, croissants, tarts, cookies, and all things pastry.

RULES:
1. When asked for a recipe or formula, ALWAYS present it in a beautifully formatted baker's sheet style:
   - Recipe Name
   - Difficulty, Rise & Proof Time, Baking Temp
   - Complete ingredients list with exact quantities in grams
   - Specific Baker's Percentages (flour as 100%) if appropriate
   - Precise step-by-step numbered mixing, proofing, laminating, and baking instructions
   - Helpful "Baker's Secrets" at the end.
2. If the user asks about dough hydration, dough temperature, starter feeding, or rise diagnostics, respond with clear, high-detail scientific and practical advice.
3. You have tools available (calculate_bakers_percentage, adjust_rise_time). Use them when the user explicitly requests hydration/percent math or proofing rise time adjustments.
4. Maintain a warm, wise, encouraging baker's persona, using rich sensory descriptions of flour, steam, crust, and crumb.
"""

class BakerAgent(BaseAgent):
    """
    Artisan Loaf Baker Agent.
    Specializes in yeast/sourdough baking science, tool scaling, and temperature calculations.
    """
    def __init__(self):
        super().__init__(
            name="Artisan Loaf",
            description="Master pastry chef and artisanal sourdough baker. Specializes in dough formulas, bakers percentages, and rising physics.",
            system_prompt=BAKER_SYSTEM_PROMPT
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
                    "name": "calculate_bakers_percentage",
                    "description": "Calculates the exact ingredient weights in grams relative to a benchmark flour weight (100%) given target hydration, salt, and yeast percentages.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "flour_weight": {
                                "type": "number",
                                "description": "The base flour weight in grams (e.g., 500.0)."
                            },
                            "hydration_pct": {
                                "type": "number",
                                "description": "Target water hydration percentage (e.g., 72.0)."
                            },
                            "salt_pct": {
                                "type": "number",
                                "description": "Target salt percentage (e.g., 2.0)."
                            },
                            "yeast_pct": {
                                "type": "number",
                                "description": "Target yeast or sourdough starter percentage (e.g., 20.0)."
                            }
                        },
                        "required": ["flour_weight", "hydration_pct", "salt_pct", "yeast_pct"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "adjust_rise_time",
                    "description": "Estimates and adjusts bulk fermentation or proofing rise duration when kitchen temperature changes.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "base_rise_hours": {
                                "type": "number",
                                "description": "The normal baseline rise/proofing duration in hours."
                            },
                            "current_temp_f": {
                                "type": "number",
                                "description": "The normal/baseline temperature in Fahrenheit (e.g., 70.0)."
                            },
                            "target_temp_f": {
                                "type": "number",
                                "description": "The actual target room temperature in Fahrenheit (e.g., 85.0)."
                            }
                        },
                        "required": ["base_rise_hours", "current_temp_f", "target_temp_f"]
                    }
                }
            }
        ]

    async def _execute_tool(self, tool_name: str, args: Dict[str, Any]) -> str:
        """
        Routing and execution of baker tools.
        """
        try:
            if tool_name == "calculate_bakers_percentage":
                return calculate_bakers_percentage(
                    float(args["flour_weight"]),
                    float(args["hydration_pct"]),
                    float(args["salt_pct"]),
                    float(args["yeast_pct"])
                )
            elif tool_name == "adjust_rise_time":
                return adjust_rise_time(
                    float(args["base_rise_hours"]),
                    float(args["current_temp_f"]),
                    float(args["target_temp_f"])
                )
            else:
                return f"Error: Tool '{tool_name}' is not supported by Artisan Loaf."
        except Exception as e:
            logger.error(f"Error executing baker tool {tool_name}: {e}")
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
                yield f"\n\n*Error: Failed to parse baker tool '{name}' arguments.*"
                return

            yield f"\n\n*Executing baking tool: **{name}**...*\n\n"
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
