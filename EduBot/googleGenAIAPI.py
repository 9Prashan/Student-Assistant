import asyncio
import re
from google import genai
from google.genai import types
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
        last_user_message = None
 
        for msg in messages:
            role    = msg["role"]
            content = msg["content"]
 
            if role == "system":
                system_instruction = content
            elif role == "user":
                last_user_message = content
                history.append(types.Content(role="user",  parts=[types.Part(text=content)]))
            elif role == "assistant":
                history.append(types.Content(role="model", parts=[types.Part(text=content)]))
 
        # Remove the last user turn from history — it's sent via send_message
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
        # 3. Call the API — on rate-limit, wait the time the API specifies   #
        # ------------------------------------------------------------------ #
        for attempt in range(self.retries):
            try:
                loop = asyncio.get_event_loop()
 
                def _call():
                    chat = self.client.chats.create(model=model, history=history, config=config)
                    return chat.send_message(last_user_message)
 
                response = await loop.run_in_executor(None, _call)
                return _GeminiResponseWrapper(response.text)
 
            except Exception as e:
                error_str = str(e)
 
                # Parse the retry delay the API sends back (e.g. "38.53s")
                wait_seconds = self._parse_retry_delay(error_str)
 
                if wait_seconds:
                    print(f"\n⏳ Rate limit hit — waiting {wait_seconds}s as requested by API (attempt {attempt + 1}/{self.retries})...")
                    await asyncio.sleep(wait_seconds)
                elif attempt < self.retries - 1:
                    fallback = 2 ** attempt
                    print(f"Error in Google GenAI API call (attempt {attempt + 1}): {e}")
                    print(f"Retrying in {fallback}s...")
                    await asyncio.sleep(fallback)
                else:
                    print(f"Error in Google GenAI API call (attempt {attempt + 1}): {e}")
                    raise e
 
        raise RuntimeError("Max retries exceeded.")
 
    @staticmethod
    def _parse_retry_delay(error_str: str) -> float | None:
        """Extract the retry delay in seconds from the API error message."""
        # Matches patterns like: "Please retry in 38.53248866s" or "retryDelay: '38s'"
        match = re.search(r'retry[^\d]*(\d+(?:\.\d+)?)s', error_str, re.IGNORECASE)
        if match:
            return float(match.group(1)) + 2  # add 2s buffer
        return None
 
 
# --------------------------------------------------------------------------- #
# Keeps the rest of the code working with completion.choices[0].message["content"]
# --------------------------------------------------------------------------- #
class _GeminiResponseWrapper:
    def __init__(self, text: str):
        self.choices = [_Choice(text)]
 
class _Choice:
    def __init__(self, text: str):
        self.message = {"content": text}