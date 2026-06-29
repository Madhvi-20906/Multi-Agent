import json
import logging
from typing import AsyncGenerator, List, Dict, Any, Optional
from openai import AsyncOpenAI

from app.config import settings
from app.agents.base import BaseAgent
from app.rag.pipeline import query_knowledge_base
from app.tools.chef_tools import scale_ingredients, convert_units, estimate_nutrition
from app.services.llm import get_openai_client

logger = logging.getLogger(__name__)

CHEF_SYSTEM_PROMPT = """You are "Chef Gasto", a professional five-star Michelin executive chef and master culinary guide. Your mission is to provide accurate, high-quality, practical cooking advice, create delicious recipes, handle dietary requirements, and help users scale or convert their culinary metrics.

RULES:
1. When asked for a recipe, ALWAYS present it in a beautifully formatted manner:
   - Title
   - Prep & Cook Time, Difficulty, and Dietary Style
   - Complete ingredients list with exact quantities
   - Clear, step-by-step numbered instructions
   - Helpful "Chef Tips" at the end.
2. ALWAYS use retrieved knowledge from the database when it is provided. Ground your recipes in the retrieved text to avoid hallucinations.
3. If the user asks about ingredient substitutions, present them clearly with alternatives.
4. Support dietary preferences (e.g., keto, gluten-free, vegan, vegetarian). Suggest adjustments matching their goals.
5. You have tools available (scale_ingredients, convert_units, estimate_nutrition). Use them when the user explicitly requests calculations, unit conversions, or macros.
6. Maintain an encouraging, warm, professional chef persona.
"""

class ChefAgent(BaseAgent):
    """
    Chef Gasto Agent implementation.
    Integrates LlamaIndex RAG retrieval, OpenAI dynamic tool execution, and SSE streaming.
    """
    def __init__(self):
        super().__init__(
            name="Chef Gasto",
            description="5-Star Michelin chef agent providing custom recipes, ingredient scaling, unit conversions, and nutrition diagnostics.",
            system_prompt=CHEF_SYSTEM_PROMPT
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
                    "name": "scale_ingredients",
                    "description": "Scales a list of ingredients by a given multiplier (e.g., 2.0 to double, 0.5 to halve).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "ingredients": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "The exact list of ingredient strings to scale."
                            },
                            "scale_factor": {
                                "type": "number",
                                "description": "Multiplier factor. E.g., 1.5, 2.0, or 0.5."
                            }
                        },
                        "required": ["ingredients", "scale_factor"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "convert_units",
                    "description": "Converts measurements between popular metric and imperial culinary units (e.g., g <-> oz, cups <-> ml, tbsp <-> tsp).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "amount": {
                                "type": "number",
                                "description": "The numeric quantity to convert."
                            },
                            "from_unit": {
                                "type": "string",
                                "description": "The current source unit (e.g., 'g', 'oz', 'cups', 'ml', 'tbsp', 'tsp')."
                            },
                            "to_unit": {
                                "type": "string",
                                "description": "The targeted unit to convert into."
                            }
                        },
                        "required": ["amount", "from_unit", "to_unit"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "estimate_nutrition",
                    "description": "Approximates calories, protein, carbs, and fats based on the list of ingredients.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "ingredients": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of ingredients in the recipe."
                            }
                        },
                        "required": ["ingredients"]
                    }
                }
            }
        ]

    async def _execute_tool(self, tool_name: str, args: Dict[str, Any]) -> str:
        """
        Routing and execution of chef tools.
        """
        try:
            if tool_name == "scale_ingredients":
                return scale_ingredients(args["ingredients"], float(args["scale_factor"]))
            elif tool_name == "convert_units":
                return convert_units(float(args["amount"]), args["from_unit"], args["to_unit"])
            elif tool_name == "estimate_nutrition":
                return estimate_nutrition(args["ingredients"])
            else:
                return f"Error: Tool '{tool_name}' is not supported."
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            return f"Error: Failed to execute tool '{tool_name}' due to error: {str(e)}"

    async def chat(
        self,
        message: str,
        history: List[Dict[str, str]],
        diet_preference: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Blocking chat mode (non-streaming). Used for testing or structured responses.
        """
        # Retrieve relevant context from RAG
        rag_results = await query_knowledge_base(message, diet_filter=diet_preference)
        context_str = ""
        if rag_results:
            context_str = "\nRetrieved Culinary Knowledge Base Context:\n"
            for res in rag_results:
                context_str += f"\n---\n{res['text']}\n---\n"

        # Construct messages
        system_message = self.system_prompt
        if diet_preference and diet_preference.lower() != "none":
            system_message += f"\n\nCRITICAL INSTRUCTION: The user has an active dietary/lifestyle preference set to: {diet_preference.upper()}. You MUST strictly adhere to this preference in ALL your advice, recipes, and ingredient suggestions. Do not suggest anything that violates this preference."

        if context_str:
            system_message += context_str
            
        messages = [{"role": "system", "content": system_message}]
        for h in history:
            messages.append({"role": h["role"], "content": h["content"]})
        messages.append({"role": "user", "content": message})

        # OpenAI Call
        response = await self.client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=messages,
            tools=self.get_tools(),
            tool_choice="auto"
        )

        response_message = response.choices[0].message
        
        # Check if function call requested
        if response_message.tool_calls:
            tool_call = response_message.tool_calls[0]
            name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)
            
            # Execute tool
            tool_output = await self._execute_tool(name, args)
            
            # Add to dialogue history and complete the conversation
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
        """
        Asynchronous streaming endpoint. Handles token-by-token streaming,
        intercepts tool calls, executes them, and streams tool results to the client.
        """
        # Retrieve relevant context from RAG
        rag_results = await query_knowledge_base(message, diet_filter=diet_preference)
        context_str = ""
        if rag_results:
            context_str = "\nRetrieved Culinary Knowledge Base Context:\n"
            for res in rag_results:
                context_str += f"\n---\n{res['text']}\n---\n"

        # System Prompt
        system_message = self.system_prompt
        if diet_preference and diet_preference.lower() != "none":
            system_message += f"\n\nCRITICAL INSTRUCTION: The user has an active dietary/lifestyle preference set to: {diet_preference.upper()}. You MUST strictly adhere to this preference in ALL your advice, recipes, and ingredient suggestions. Do not suggest anything that violates this preference."

        if context_str:
            system_message += context_str
            
        messages = [{"role": "system", "content": system_message}]
        for h in history:
            messages.append({"role": h["role"], "content": h["content"]})
        messages.append({"role": "user", "content": message})

        logger.info(f"Initiating streaming chat completions with model={settings.OPENAI_MODEL}")
        
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
            
            # Text stream
            if delta.content:
                yield delta.content
                
            # Function calls (tool calls) stream — guard against None index (Gemini quirk)
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

        # If a tool call was detected, execute it
        if tool_calls_to_assemble:
            # Let's process the first tool call
            tc = tool_calls_to_assemble[0]
            name = tc["name"]
            
            try:
                args = json.loads(tc["arguments"])
            except Exception as e:
                logger.error(f"Failed to parse tool arguments: {tc['arguments']} Error: {e}")
                yield f"\n\n*Error trying to execute tool '{name}': invalid arguments parsed.*"
                return

            yield f"\n\n*Executing kitchen tool: **{name}**...*\n\n"
            tool_output = await self._execute_tool(name, args)
            
            # Stream the tool output back directly as nice markdown cards!
            yield tool_output + "\n\n"
            
            # Let LLM complete response incorporating tool context
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
            
            # Get final completion stream
            final_stream = await self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=messages,
                stream=True
            )
            
            async for chunk in final_stream:
                delta = chunk.choices[0].delta
                if delta.content:
                    yield delta.content
