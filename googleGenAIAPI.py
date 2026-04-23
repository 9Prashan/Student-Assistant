import asyncio
import re
import streamlit as st
from google import genai
from google.genai import types


# Works locally (config.py) AND on Streamlit Cloud (st.secrets)
try:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
except Exception:
    from config import GOOGLE_API_KEY


class GoogleGenAIAPI:
    def __init__(self, retries=5):
        self.retries = retries
        self.client = genai.Client(api_key=GOOGLE_API_KEY)

    async def chat_completion(self, model, messages, temperature, max_tokens):
        # ------------------------------------------------------------------ #
        # 1. Separate system prompt, history, and the last user message       #
        # ------------------------------------------------------------------ #
        system_instruction = None
        history = []
        last_user_message = None   # str OR list (multimodal)

        for msg in messages:
            role    = msg["role"]
            content = msg["content"]

            if role == "system":
                system_instruction = content

            elif role == "user":
                last_user_message = content
                # Build parts — content can be a plain string or a list of blocks
                parts = self._build_parts(content)
                history.append(types.Content(role="user", parts=parts))

            elif role == "assistant":
                # Assistant messages are always plain text
                history.append(types.Content(
                    role="model",
                    parts=[types.Part(text=content if isinstance(content, str) else str(content))]
                ))

        # Remove the last user turn from history — it is sent via send_message
        if history and history[-1].role == "user":
            history.pop()

        # ------------------------------------------------------------------ #
        # 2. Build generation config                                          #
        # ------------------------------------------------------------------ #
        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
            system_instruction=system_instruction,
        )

        # ------------------------------------------------------------------ #
        # 3. Call with retry + respect the API's requested back-off delay     #
        # ------------------------------------------------------------------ #
        for attempt in range(self.retries):
            try:
                loop = asyncio.get_event_loop()
                last_parts = self._build_parts(last_user_message)

                def _call():
                    chat = self.client.chats.create(
                        model=model, history=history, config=config
                    )
                    # send_message accepts a string OR a list of Part objects
                    if len(last_parts) == 1 and last_parts[0].text is not None:
                        return chat.send_message(last_parts[0].text)
                    else:
                        return chat.send_message(last_parts)

                response = await loop.run_in_executor(None, _call)
                return _GeminiResponseWrapper(response.text)

            except Exception as e:
                error_str = str(e)
                wait_seconds = self._parse_retry_delay(error_str)

                if wait_seconds:
                    print(f"\n⏳ Rate limit — waiting {wait_seconds}s (attempt {attempt + 1}/{self.retries})...")
                    await asyncio.sleep(wait_seconds)
                elif attempt < self.retries - 1:
                    fallback = 2 ** attempt
                    print(f"Error (attempt {attempt + 1}): {e} — retrying in {fallback}s...")
                    await asyncio.sleep(fallback)
                else:
                    print(f"Error (attempt {attempt + 1}): {e}")
                    raise e

        raise RuntimeError("Max retries exceeded.")

    # ------------------------------------------------------------------ #
    # Helpers                                                              #
    # ------------------------------------------------------------------ #

    def _build_parts(self, content) -> list:
        """
        Convert an OpenAI-style content value into a list of Gemini Part objects.

        Plain string  → [Part(text=...)]
        List of dicts → each dict is {"type":"text","text":...}
                        or {"type":"image","source":{"type":"base64","media_type":...,"data":...}}
        """
        if isinstance(content, str):
            return [types.Part(text=content)]

        if isinstance(content, list):
            parts = []
            for block in content:
                if block.get("type") == "text":
                    parts.append(types.Part(text=block["text"]))
                elif block.get("type") == "image":
                    source = block["source"]
                    if source["type"] == "base64":
                        parts.append(
                            types.Part(
                                inline_data=types.Blob(
                                    mime_type=source["media_type"],
                                    data=source["data"],   # base64 string
                                )
                            )
                        )
            return parts

        # Fallback
        return [types.Part(text=str(content))]

    @staticmethod
    def _parse_retry_delay(error_str: str) -> float | None:
        match = re.search(r'retry[^\d]*(\d+(?:\.\d+)?)s', error_str, re.IGNORECASE)
        if match:
            return float(match.group(1)) + 2
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Response wrapper — keeps the rest of the code using the familiar interface:
#   completion.choices[0].message["content"]
# ─────────────────────────────────────────────────────────────────────────────
class _GeminiResponseWrapper:
    def __init__(self, text: str):
        self.choices = [_Choice(text)]

class _Choice:
    def __init__(self, text: str):
        self.message = {"content": text}