import openai 
import numpy as np
import sys
from pydantic import BaseModel
import json
import asyncio
from pymilvus import MilvusClient
import google.generativeai as genai
import typing_extensions as typing
import anthropic
from trim import trim_json

GOOGLE_API_KEY = "AIzaSyAdvW64tTQulvLDDQoOxHT-0Qq_HfxZJfM"
ANTHROPIC_KEY = "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"
OPENAI_API_KEY = "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"

async_client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)
sync_client = openai.OpenAI(api_key=OPENAI_API_KEY)
anth_client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
genai.configure(api_key=GOOGLE_API_KEY)


NUM_RESULTS_TO_SEND = 20

def get_client(client_type):
    if client_type == "oai_async":
        return async_client
    elif client_type == "oai_sync":
        return sync_client
    elif client_type == "google":
        return genai.GenerativeModel("gemini-1.5-flash-latest")
    elif client_type == "anthropic":
        return anth_client
    else:
        raise ValueError(f"Invalid client type: {client_type}")

def get_embedding(text):
   text = text.replace("\n", " ")
   client = llm.get_client("oai_sync")
   return client.embeddings.create(input = [text], model="text-embedding-3-small").data[0].embedding
    