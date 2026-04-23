import asyncio
import re
import streamlit as st
from google import genai
from google.genai import types

GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]


class GoogleGenAIAPI:
    def __init__(self, retries=5):
        self.retries = retries
        self.client = genai.Client(api_key=GOOGLE_API_KEY)

    async def chat_completion(self, model, messages, temperature, max_tokens):
        # ------------------------------------------------------------------ #
        # 1. Parse messages into components                                   #
        # ------------------------------------------------------------------ #
        system_instruction = None
        history = []
        last_user_content = None   # raw content (str or list)
        has_image = False

        for msg in messages:
            role    = msg["role"]
            content = msg["content"]

            if role == "system":
                system_instruction = content

            elif role == "user":
                last_user_content = content
                # Check if this message contains an image
                if isinstance(content, list):
                    for block in content:
                        if block.get("type") == "image":
                            has_image = True
                parts = self._build_parts(content)
                history.append(types.Content(role="user", parts=parts))

            elif role == "assistant":
                text = content if isinstance(content, str) else str(content)
                history.append(types.Content(role="model", parts=[types.Part(text=text)]))

        # Remove last user turn from history — sent separately
        if history and history[-1].role == "user":
            history.pop()

        # ------------------------------------------------------------------ #
        # 2. Build config                                                     #
        # ------------------------------------------------------------------ #
        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
            system_instruction=system_instruction,
        )

        # ------------------------------------------------------------------ #
        # 3. Call API — images use generate_content, text uses chat session  #
        # ------------------------------------------------------------------ #
        last_parts = self._build_parts(last_user_content)

        for attempt in range(self.retries):
            try:
                loop = asyncio.get_event_loop()

                if has_image:
                    # Images MUST use generate_content directly, not chat
                    def _call_image():
                        # Build full contents: history + last user message
                        all_contents = history + [
                            types.Content(role="user", parts=last_parts)
                        ]
                        return self.client.models.generate_content(
                            model=model,
                            contents=all_contents,
                            config=config,
                        )
                    response = await loop.run_in_executor(None, _call_image)
                    return _GeminiResponseWrapper(response.text)

                else:
                    # Text-only — use chat session
                    def _call_text():
                        chat = self.client.chats.create(
                            model=model, history=history, config=config
                        )
                        if len(last_parts) == 1 and last_parts[0].text is not None:
                            return chat.send_message(last_parts[0].text)
                        return chat.send_message(last_parts)

                    response = await loop.run_in_executor(None, _call_text)
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
        """Convert OpenAI-style content into Gemini Part objects."""
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
                        import base64
                        # Decode base64 string to bytes
                        image_bytes = base64.b64decode(source["data"])
                        parts.append(
                            types.Part(
                                inline_data=types.Blob(
                                    mime_type=source["media_type"],
                                    data=image_bytes,
                                )
                            )
                        )
            return parts

        return [types.Part(text=str(content))]

    @staticmethod
    def _parse_retry_delay(error_str: str):
        match = re.search(r'retry[^\d]*(\d+(?:\.\d+)?)s', error_str, re.IGNORECASE)
        if match:
            return float(match.group(1)) + 2
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Response wrapper — completion.choices[0].message["content"]
# ─────────────────────────────────────────────────────────────────────────────
class _GeminiResponseWrapper:
    def __init__(self, text: str):
        self.choices = [_Choice(text)]

class _Choice:
    def __init__(self, text: str):
        self.message = {"content": text}