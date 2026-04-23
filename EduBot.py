"""
EduBot.py
---------
Synchronous Bot class designed for use with Streamlit.
(Streamlit runs in its own event loop, so we use sync calls via asyncio.run()
 internally rather than exposing async methods to the UI layer.)
"""
 
import asyncio
from googleGenAIAPI import GoogleGenAIAPI
from prompts import (
    bot_sys_prompt, bot_prompt,
    translator_sys_prompt, translator_prompt,
    format_content_sys_prompt, format_content_prompt,
)
 
 
class Bot:
    def __init__(self):
        self.llm = GoogleGenAIAPI()
 
    # ------------------------------------------------------------------ #
    # Public sync API (called by Streamlit)                               #
    # ------------------------------------------------------------------ #
 
    def format_content_sync(self, content: str) -> str:
        return asyncio.run(self._format_content(content))
 
    def translate_sync(self, content: str, lang: str) -> str:
        return asyncio.run(self._translate(content, lang))
 
    def get_bot_response_sync(self, messages: list) -> str:
        """
        Send the current conversation history to the model and return
        the raw response string.
        """
        return asyncio.run(self._get_response(messages))
 
    # ------------------------------------------------------------------ #
    # Message builder helpers                                             #
    # ------------------------------------------------------------------ #
 
    def build_initial_messages(self, problem: str, solution: str) -> list:
        """Return the first message list for a new session."""
        return [
            {"role": "system", "content": bot_sys_prompt},
            {"role": "user",   "content": bot_prompt(problem=problem, solution=solution)},
        ]
 
    # ------------------------------------------------------------------ #
    # Internal async implementations                                      #
    # ------------------------------------------------------------------ #
 
    async def _get_response(self, messages: list) -> str:
    # Use vision-capable model if any message contains an image
        has_image = any(
            isinstance(msg.get("content"), list) and
            any(block.get("type") == "image" for block in msg["content"])
            for msg in messages
    )
    model = "gemini-2.5-flash" if has_image else "gemini-3.1-flash-lite-preview"

    completion = await self.llm.chat_completion(
        model=model,
        messages=messages,
        temperature=0,
        max_tokens=1024,
    )
    return completion.choices[0].message["content"]
 
    async def _translate(self, content: str, lang: str) -> str:
        messages = [
            {"role": "system", "content": translator_sys_prompt},
            {"role": "user",   "content": translator_prompt(content=content, lang=lang)},
        ]
        res = await self.llm.chat_completion(
            model="gemini-3.1-flash-lite-preview",
            messages=messages,
            temperature=0,
            max_tokens=512,
        )
        return res.choices[0].message["content"]
 
    async def _format_content(self, content: str) -> str:
        messages = [
            {"role": "system", "content": format_content_sys_prompt},
            {"role": "user",   "content": format_content_prompt(content=content)},
        ]
        res = await self.llm.chat_completion(
            model="gemini-3.1-flash-lite-preview",
            messages=messages,
            temperature=0,
            max_tokens=512,
        )
        return res.choices[0].message["content"]