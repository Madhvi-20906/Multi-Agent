import json
import logging
from typing import AsyncGenerator, List, Dict, Any, Optional
from openai import AsyncOpenAI

from app.config import settings
from app.agents.base import BaseAgent
from app.rag.pipeline import query_knowledge_base
from app.tools.stylist_tools import build_outfit, analyze_color_palette
from app.services.llm import get_openai_client

logger = logging.getLogger(__name__)

STYLIST_SYSTEM_PROMPT = """You are "Sartorial Thread", a world-class personal stylist and image consultant with an encyclopaedic knowledge of fashion, colour theory, body-positive styling, and global trends.

RULES:
1. When asked for outfit advice or wardrobe help, ALWAYS present it as a polished "Look Book" entry:
   - Occasion & Season
   - Core Outfit Pieces (with specific garment descriptions)
   - Colour Palette & Fabric Recommendations
   - Footwear & Accessories
   - Styling Notes & Body-Positive Tips
   - "Sartorial Secrets" — your signature pro tips at the end.
2. You have tools available: `build_outfit` and `analyze_color_palette`. Use them when the user asks for specific outfit recommendations or wants to understand their personal colour season.
3. Always celebrate body diversity and provide inclusive, empowering advice that makes any body type feel confident and stylish.
4. Reference real-world fashion brands spanning luxury (Bottega Veneta, The Row), high-street (Zara, COS), and sustainable (Reformation, Everlane) to give practical, accessible suggestions.
5. Maintain a sophisticated, warm, and inspiring persona — like a knowledgeable friend in the fashion industry.
"""

class StylistAgent(BaseAgent):
    """
    Sartorial Thread Stylist Agent.
    Specialises in personal styling, colour theory, outfit curation, and wardrobe building.
    """
    def __init__(self):
        super().__init__(
            name="Sartorial Thread",
            description="World-class personal stylist and image consultant. Specialises in outfit curation, colour theory, and body-positive wardrobe building.",
            system_prompt=STYLIST_SYSTEM_PROMPT
        )
        self.client = get_openai_client()

    def get_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "build_outfit",
                    "description": "Generates a complete, polished outfit recommendation for a specific occasion, season, body type, style preference, and colour palette.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "occasion": {
                                "type": "string",
                                "description": "The event or setting (e.g., 'business formal', 'date night', 'casual weekend', 'wedding guest', 'beach / resort')."
                            },
                            "style_preference": {
                                "type": "string",
                                "description": "The user's preferred aesthetic (e.g., 'minimalist', 'bohemian', 'classic', 'edgy', 'romantic', 'playful')."
                            },
                            "body_type": {
                                "type": "string",
                                "description": "The user's body type (e.g., 'hourglass', 'pear', 'apple', 'rectangle', 'inverted triangle', 'petite', 'tall')."
                            },
                            "season": {
                                "type": "string",
                                "description": "Current or target season (e.g., 'spring', 'summer', 'autumn', 'winter')."
                            },
                            "color_palette": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Preferred colours to incorporate (e.g., ['navy', 'cream', 'gold'])."
                            }
                        },
                        "required": ["occasion", "style_preference", "body_type", "season", "color_palette"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "analyze_color_palette",
                    "description": "Analyses personal coloring (skin tone, hair, eyes) to determine the user's colour season and recommend a flattering wardrobe palette.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "skin_tone": {
                                "type": "string",
                                "description": "Description of skin tone undertone (e.g., 'warm golden olive', 'cool porcelain', 'neutral beige', 'deep ebony')."
                            },
                            "hair_color": {
                                "type": "string",
                                "description": "Natural hair colour (e.g., 'auburn', 'platinum blonde', 'jet black', 'warm chestnut brown')."
                            },
                            "eye_color": {
                                "type": "string",
                                "description": "Eye colour (e.g., 'hazel', 'deep brown', 'cool blue-grey', 'green')."
                            },
                            "preferred_mood": {
                                "type": "string",
                                "description": "The aesthetic mood they want their wardrobe to convey (e.g., 'romantic', 'minimalist', 'edgy', 'bohemian', 'classic', 'playful')."
                            }
                        },
                        "required": ["skin_tone", "hair_color", "eye_color", "preferred_mood"]
                    }
                }
            }
        ]

    async def _execute_tool(self, tool_name: str, args: Dict[str, Any]) -> str:
        try:
            if tool_name == "build_outfit":
                return build_outfit(
                    args["occasion"],
                    args["style_preference"],
                    args["body_type"],
                    args["season"],
                    args.get("color_palette", [])
                )
            elif tool_name == "analyze_color_palette":
                return analyze_color_palette(
                    args["skin_tone"],
                    args["hair_color"],
                    args["eye_color"],
                    args["preferred_mood"]
                )
            else:
                return f"Error: Tool '{tool_name}' is not supported by Sartorial Thread."
        except Exception as e:
            logger.error(f"Error executing stylist tool {tool_name}: {e}")
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
                yield f"\n\n*Error: Failed to parse stylist tool '{name}' arguments.*"
                return

            yield f"\n\n*Executing styling tool: **{name}**...*\n\n"
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
