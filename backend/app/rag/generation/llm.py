"llm service interface and implementations."
from urllib import response
from sqlalchemy import false
import httpx
from asyncio import timeout
from fsspec import asyn
from typing import Protocol
from app.core.config import Settings

class LLM(Protocol):
    "llm service interface. The pipline calls generate() only."

    async def genereate(self,prompt:str,settings:Settings)->str:
        "Generate a completion for the given prompt."
        ...

#Line by line
# - Protocol --Structural subtyping (duck typing for static checkers). Any class with generate() matches. 
# genereate(self,prompt:str,settings:Settings)->str -- single method the pipeline uses. Takes the full prompt and settings (for tmodel name,URL,etc.). Returns the answer the answer string. 
# ... -- ellipsis means "no body", this is just the contract. 

"Python feature: Protocols from typing lets you define interface without inheritance. Class don't need to implement llm; they just need method."

class OllamaLLM:
    "Ollama LLM service implementation using httpx."

    def __init__(self,timeout:float=120.0):
        self.timeout=timeout

    async def generate(self, prompt:str,settings:Settings)->str:
        import httpx

        url=f"{settings.llm_base_url}/api/generate"
        payload={
            "model":settings.llm_model_name,
            "prompt":prompt,
            "stream":False,
            "options":{
                "num_ctx":settings.llm_num_ctx,
            },
        }
        if not settings.llm_think:
            payload["think"]=False

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp=await client.post(url,json=payload)
                resp.raise_for_status()
                data=resp.json()
        except httpx.ConnectError as e:
            raise RuntimeError(
                "Cannot reach Ollama. Is it running? Start with ollama serve") from e
        except httpx.TimeoutException as e:
            raise RuntimeError(f"Ollama timed out after {self.timeout}s. First load can take 25-35s.") from e

        answer= data.get("response","").strip()

        import re
        answer=re.sub(r"<think>.*","",answer,flags=re.DOTALL).strip()

        return answer

# Line by line:
# - timeout=120.0 -- generous for first model load(25-35s). 
# - httpx.AsyncClient -- async http client, already installed.
# - payload -- ollama /api/generate/ format. steam=false=sigle response. 
# - options.num_ctx -- context window. 
# - think=False -- disables qwen3 thinking mode
# - ConnectError -- friendly error:"Is ollama running?" 
# - TimeoutException -- friendly error:"ollama timed out"
# - re.sub(r"<think>.*?</think>", "", ...) — strips any thinking tokens the model emits anyway.

"""Python features:
- async with httpx.AsyncClient() — async context manager, closes connections automatically.
- raise ... from e — chains exceptions, preserves original traceback.
- re.DOTALL — makes . match newlines too."""

class FakeLLM:
    "Fake llm for tests. Returns a fixed responce or a sequence."

    def __init__(self, responses:str| list[str]="This is a fake answer."):
        self.responses=[responses] if isinstance(responses,str) else list(responses)
        self.call_count=0
    async def generate(self,prompt:str,settings:Settings)->str:
        response=self.responses[min(self.call_count,len(self.responses)-1)]


# Line-by-line:
# - __init__(self, responses: str | list[str] = "...") — accepts one string or a list. If string, wraps in list.
# - self.call_count — tracks how many times generate was called.
# - min(self.call_count, len(self.responses) - 1) — returns last response if called more times than responses provided.
# - async def generate — matches the LLM protocol (async, same signature).
# Why this design: Tests can inject FakeLLM(["answer 1", "answer 2"]) to simulate multi-turn or verify prompt content.