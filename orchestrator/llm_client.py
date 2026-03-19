import os
import requests
import json
import re

API_URL = os.getenv("LLM_GATEWAY_URL", "https://imllm.intermesh.net/v1/chat/completions").strip()

def call_llm(api_key: str, system_prompt: str, user_prompt: str, model: str = "google/gemini-2.5-flash", tools=None) -> str:
    """
    Generic function to call the custom LLM API.
    This ensures all agents use the same gateway.
    """
    if not api_key:
        print("Error: API Key is missing. Attempting to run without LLM credentials.")
        return None

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    payload = {
        "model": model, 
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    }
    
    if tools:
        payload["tools"] = tools
    
    url = API_URL
    if "/chat/completions" not in url:
        url = f"{url.rstrip('/')}/chat/completions"

    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code != 200:
            print(f"LLM API Error {response.status_code}: {response.text[:500]}")
        response.raise_for_status()
        
        # Safely extract the content string
        content = response.json().get("choices", [{}])[0].get("message", {}).get("content", "")
        # Clean markdown formatting if present
        if content:
            content = content.replace("```json", "").replace("```", "").strip()
        return content
    except Exception as e:
        print(f"Error calling LLM: {str(e)}")
        return None

def stream_llm(api_key: str, system_prompt: str, user_prompt: str, model: str = "google/gemini-2.5-flash"):
    """
    Streaming version of call_llm.
    Yields text chunks as they arrive from the gateway.
    """
    if not api_key:
        yield "Error: API Key is missing."
        return

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "stream": True
    }

    url = API_URL
    if "/chat/completions" not in url:
        url = f"{url.rstrip('/')}/chat/completions"

    try:
        response = requests.post(url, headers=headers, json=payload, stream=True)
        response.raise_for_status()

        for line in response.iter_lines():
            if line:
                line_str = line.decode("utf-8")
                if line_str.startswith("data: "):
                    data_str = line_str[6:]
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        content = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                        if content:
                            yield content
                    except:
                        continue
    except Exception as e:
        yield f"\n[STREAM_ERROR] {str(e)}"

def extract_json(llm_output: str) -> dict:
    if not llm_output:
        return {}
        
    def scrub_json(s: str) -> str:
        # Step 1: Replace common problematic quotes and dashes
        s = s.replace("“", "\"").replace("”", "\"").replace("‘", "'").replace("’", "'")
        
        # Step 2: Industrial Clean (Remove control characters and non-ASCII garbage)
        # Often LLMs spit out hidden control chars or non-UTF8 noise
        s = re.sub(r'[\x00-\x1F\x7F]', '', s) 
        
        # Step 3: Repair trailing commas in lists/objects
        s = re.sub(r",\s*([}\]])", r"\1", s)
        
        # Step 4: Brace Balancing (Recovery from Truncation)
        # If the LLM was cut off, try to add missing closing braces
        open_braces = s.count('{')
        close_braces = s.count('}')
        open_brackets = s.count('[')
        close_brackets = s.count(']')
        
        if open_braces > close_braces: s += '}' * (open_braces - close_braces)
        if open_brackets > close_brackets: s += ']' * (open_brackets - close_brackets)
        
        return s.strip()

    # Strategy 1: The Marker Strategy (Most Precise)
    if "[JSON_PAYLOAD_START]" in llm_output:
        try:
            parts = llm_output.split("[JSON_PAYLOAD_START]")
            candidate = parts[-1].split("[JSON_PAYLOAD_END]")[0]
            if "```json" in candidate:
                candidate = candidate.split("```json")[-1].split("```")[0]
            return json.loads(scrub_json(candidate))
        except:
            pass

    # Strategy 2: Triple Backtick Strategy (Markdown blocks)
    try:
        blocks = re.findall(r"```(?:json)?\s*([\s\S]*?)\s*```", llm_output)
        for b in reversed(blocks):
            try:
                if b.strip(): return json.loads(scrub_json(b))
            except:
                continue
    except:
        pass

    # Strategy 3: Brute Force Brace Search (Find largest container)
    try:
        # Regex to find anything starting with { or [ and ending with } or ]
        matches = re.findall(r"([\{\[].*[\}\]])", llm_output, re.DOTALL)
        if matches:
            longest = max(matches, key=len)
            try:
                return json.loads(scrub_json(longest))
            except:
                # Fallback: find any { and just try the scrubbed rest
                idx = llm_output.find('{')
                if idx != -1:
                    try: return json.loads(scrub_json(llm_output[idx:]))
                    except: pass
    except:
        pass

    # Final Failure Mode
    return {"error": "All JSON extraction strategies failed", "raw_snippet": llm_output[-300:]}
