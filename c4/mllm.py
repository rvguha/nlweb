from typing import Any, Dict, Optional
import json
from enum import Enum
import asyncio
import anthropic
from anthropic import AsyncAnthropic
import google.generativeai as genai
from openai import OpenAI, AsyncOpenAI, AzureOpenAI
import jsonschema
import os
from azure.ai.inference import ChatCompletionsClient
from azure.core.credentials import AzureKeyCredential
from azure.ai.inference.models import SystemMessage, UserMessage
import time
import concurrent.futures

class ModelProvider(Enum):
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    AZURE_OPENAI = "azure_openai"
    AZURE_DEEPSEEK = "azure_deepseek"


def determine_best_model(prompt, query_id="Ranking", model_family="gpt"):
    return "gpt-4o-mini"

azure_openai_4o_endpoint = "https://guha-m91xe3zb-westus.cognitiveservices.azure.com/"
deepseek_endpoint = "https://guha-m91xe3zb-westus.services.ai.azure.com/models"
azure_embedding_endpoint = "https://guha-m91xe3zb-westus.cognitiveservices.azure.com/"
azure_embedding_api_version = "2024-02-01"
azure_embedding_deployment = "text-embedding-3-small"

# Global thread pool for CPU-bound tasks
_thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=10)

class LLMClients:
    openai = None
    async_openai = None
    anthropic = None
    async_anthropic = None
    azure_openai4o = None
    deepseek = None
    azure_embedding_client = None
    
    # Connection pools - reuse connections
    _http_sessions = {}
    
    @classmethod
    def get_openai(cls):
        if cls.openai is None:
            cls.openai = OpenAI(timeout=30.0)  # Set timeout explicitly
        return cls.openai
    
    @classmethod
    def get_async_openai(cls):
        if cls.async_openai is None:
            cls.async_openai = AsyncOpenAI(timeout=30.0)  # Set timeout explicitly
        return cls.async_openai
    
    @classmethod
    def get_anthropic(cls):
        if cls.anthropic is None:
            cls.anthropic = anthropic.Anthropic(timeout=30.0)  # Set timeout explicitly
        return cls.anthropic
    
    @classmethod
    def get_async_anthropic(cls):
        if cls.async_anthropic is None:
            cls.async_anthropic = AsyncAnthropic(timeout=30.0)  # Set timeout explicitly
        return cls.async_anthropic
    
    @classmethod
    def get_azure_openai4o(cls):
        if cls.azure_openai4o is None:
            cls.azure_openai4o = AzureOpenAI(
                azure_endpoint=azure_openai_4o_endpoint,
                api_key=os.environ.get("AZURE_OPENAI_4o_API_KEY"),
                api_version="2024-12-01-preview",
                timeout=30.0  # Set timeout explicitly
            )
        return cls.azure_openai4o
    
    @classmethod
    def get_deepseek(cls):
        if cls.deepseek is None:
            cls.deepseek = ChatCompletionsClient(
                endpoint=deepseek_endpoint,
                credential=AzureKeyCredential(os.environ["AZURE_DEEPSEEK_KEY"])
            )
        return cls.deepseek
        
    @classmethod
    def get_azure_embedding_client(cls):
        if cls.azure_embedding_client is None:
            cls.azure_embedding_client = AzureOpenAI(
                azure_endpoint=azure_embedding_endpoint,
                api_key=os.environ.get("AZURE_EMBEDDING_API_KEY"),
                api_version=azure_embedding_api_version,
                timeout=15.0  # Shorter timeout for embeddings
            )
        return cls.azure_embedding_client


def get_provider(model_name):
    model_name_lower = model_name.lower()
    
    if "OAI" in model_name or "gpt" in model_name:
        return ModelProvider.OPENAI
    elif "Azure" in model_name:
        return ModelProvider.AZURE_OPENAI
    elif "claude" in model_name or "anthropic" in model_name or "haiku" in model_name:
        return ModelProvider.ANTHROPIC
    elif model_name_lower.startswith("deepseek"):
        return ModelProvider.AZURE_DEEPSEEK
    else:
        raise ValueError(f"Unknown model provider for model: {model_name}")


# Memoization cache for embeddings to avoid redundant calls
_embedding_cache = {}

async def get_embedding(query):
    # Check cache first
    cache_key = query
    if cache_key in _embedding_cache:
        return _embedding_cache[cache_key]
    
    # Not in cache, get from API
    client = LLMClients.get_azure_embedding_client()
    response = client.embeddings.create(
        input=query,
        model=azure_embedding_deployment
    )
    embedding = response.data[0].embedding
    
    # Cache the result
    _embedding_cache[cache_key] = embedding
    return embedding

async def get_azure_embedding(text):
    # Check cache first
    cache_key = text
    if cache_key in _embedding_cache:
        return _embedding_cache[cache_key]
    
    # Use thread pool for I/O operation to avoid blocking
    loop = asyncio.get_event_loop()
    client = LLMClients.get_azure_embedding_client()
    
    # Run in thread pool
    response = await loop.run_in_executor(
        _thread_pool,
        lambda: client.embeddings.create(
            input=text,
            model=azure_embedding_deployment
        )
    )
    
    embedding = response.data[0].embedding
    
    # Cache the result
    _embedding_cache[cache_key] = embedding
    return embedding


def clean_ds_response(content):
    response_text = content.strip()
    response_text = content.replace('```json', '').replace('```', '').strip()
            
    start_idx = response_text.find('{')
    end_idx = response_text.rfind('}') + 1
    if start_idx == -1 or end_idx == 0:
        raise ValueError("No valid JSON object found in response")
        
    json_str = response_text[start_idx:end_idx]
            
    try:
        result = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse response as JSON: {e}")
    return result


async def get_azure_openai_completion(prompt, json_schema, model_name="gpt-4o", temperature=0.7):
    client = LLMClients.get_azure_openai4o()
    system_prompt = f"""Provide a response that matches this JSON schema: {json.dumps(json_schema)}"""
    
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(
        _thread_pool,
        lambda: client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2056,
            temperature=temperature,
            top_p=0.1,
            stream=False,
            presence_penalty=0.0,
            frequency_penalty=0.0,
            model=model_name
        )
    )
    ansr_str = response.choices[0].message.content
    ansr = clean_ds_response(ansr_str)
    return ansr


async def get_deepseek_completion(prompt, json_schema, model_name="DeepSeek-V3", temperature=0.7):
    client = LLMClients.get_deepseek()
    system_prompt = f"""Provide a response that matches this JSON schema: {json.dumps(json_schema)}"""
    
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(
        _thread_pool,
        lambda: client.complete(
            messages=[
                SystemMessage(content=system_prompt),
                UserMessage(content=prompt)
            ],
            max_tokens=2056,
            temperature=temperature,
            top_p=0.1,
            stream=False,
            presence_penalty=0.0,
            frequency_penalty=0.0,
            model=model_name
        )
    )
    ansr_str = response.choices[0].message.content
    ansr = clean_ds_response(ansr_str)
    return ansr

async def get_openai_completion(prompt, json_schema, model_name, temperature=0.7):
    model_name = model_name.replace(" OAI", "")
    client = LLMClients.get_async_openai()
    system_prompt = f"""Provide a response that matches this JSON schema: {json.dumps(json_schema)}"""
    
    # Use response_format for OpenAI to ensure JSON output
    response = await client.chat.completions.create(
        model=model_name,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        temperature=temperature,
        timeout=30  # Explicit timeout
    )
    result = json.loads(response.choices[0].message.content)
    return result

async def get_anthropic_completion(prompt, json_schema, model_name, temperature=0.7):
    client = LLMClients.get_async_anthropic()
    formatted_prompt = f"Provide a response in JSON format that conforms to the schema: {json.dumps(json_schema)}\n\n{prompt}"
    
    response = await client.messages.create(
        model=model_name,
        max_tokens=2056,
        temperature=temperature,
        system="Respond ONLY with valid JSON that follows the specified schema exactly. No explanations.",
        messages=[
            {"role": "user", "content": formatted_prompt}
        ]
        # Removed the response_format parameter as it's not supported by Claude
    )
    
    # More robust handling of Anthropic API responses
    if hasattr(response, 'content') and isinstance(response.content, list) and len(response.content) > 0:
        content_item = response.content[0]
        if hasattr(content_item, 'text'):
            text_content = content_item.text
        elif isinstance(content_item, dict) and 'text' in content_item:
            text_content = content_item['text']
        else:
            raise ValueError(f"Unexpected Anthropic response structure: {content_item}")
        
        # Clean the response to ensure it's valid JSON
        text_content = text_content.strip()
        if text_content.startswith("```json"):
            text_content = text_content.replace("```json", "", 1)
        if text_content.endswith("```"):
            text_content = text_content.replace("```", "", text_content.count("```") - 1)
        text_content = text_content.strip()
        
        # Extract JSON if wrapped in other text
        json_start = text_content.find('{')
        json_end = text_content.rfind('}') + 1
        if json_start >= 0 and json_end > 0:
            text_content = text_content[json_start:json_end]
            
        result = json.loads(text_content)
        return result
    else:
        raise ValueError(f"Invalid or empty response from Anthropic API: {response}")

# Response cache to avoid duplicate calls
_response_cache = {}

async def get_structured_completion_async(
    prompt,
    json_schema,
    model_name="auto",
    temperature=0.7
):
    # Generate cache key
    cache_key = f"{prompt}:{model_name}:{temperature}:{json.dumps(json_schema)}"
    
    # Check cache first
    if cache_key in _response_cache:
        return _response_cache[cache_key]
    
    # Not in cache, proceed with API call
    if (model_name == "auto"):
        model_name = determine_best_model(prompt)
    
    provider = get_provider(model_name)
    
    start_time = time.time()
    try:
        if provider == ModelProvider.OPENAI:
            result = await get_openai_completion(prompt, json_schema, model_name, temperature)
            
        elif provider == ModelProvider.ANTHROPIC:
            result = await get_anthropic_completion(prompt, json_schema, model_name, temperature)
            
        elif provider == ModelProvider.AZURE_OPENAI:
            model_name = model_name.replace(" (Azure)", "")
            result = await get_azure_openai_completion(
                prompt=prompt,
                json_schema=json_schema,
                model_name=model_name,
                temperature=temperature
            )
            
        elif provider == ModelProvider.AZURE_DEEPSEEK:
            result = await get_deepseek_completion(
                prompt=prompt,
                json_schema=json_schema,
                model_name=model_name,
                temperature=temperature
            )
            
        else:
            raise ValueError(f"Unsupported model provider: {provider}")

        # Validate the result
        jsonschema.validate(instance=result, schema=json_schema)
        
        # Cache the successful result
        _response_cache[cache_key] = result
        
        # Optionally log completion time
        elapsed = time.time() - start_time
     #   print(f"LLM call to {model_name} completed in {elapsed:.2f}s")
        
        return result

    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse model response as JSON: {e}")
    except jsonschema.exceptions.ValidationError as e:
        raise ValueError(f"Model response did not match schema: {e}")
    except Exception as e:
        raise ValueError(f"Error getting completion: {e}")
        
async def retry_structured_completion(
    prompt,
    json_schema,
    model_name,
    temperature=0.7,
    retries=3,
    wait_time=0.25
):
    last_error = None
    
    # Using exponential backoff for retries
    for attempt in range(retries + 1):
        try:
            return await get_structured_completion_async(
                prompt=prompt,
                json_schema=json_schema,
                model_name=model_name,
                temperature=temperature
            )
        except Exception as e:
            last_error = e
            if attempt < retries:
                # Exponential backoff: wait_time * (2^attempt)
                backoff_time = wait_time * (2 ** attempt)
                await asyncio.sleep(backoff_time)
            else:
                raise ValueError(f"All {retries} retries failed. Last error: {last_error}")

# Batch processing function for multiple prompts
async def batch_process_completions(prompts, json_schema, model_name, temperature=0.7):
    """Process multiple prompts in parallel"""
    tasks = [
        get_structured_completion_async(prompt, json_schema, model_name, temperature)
        for prompt in prompts
    ]
    return await asyncio.gather(*tasks, return_exceptions=True)

async def main():
    BOOK_REVIEW_SCHEMA = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "title": "BookReview",
        "description": "A structured book review with ratings and analysis",
        "properties": {
            "title": {"type": "string"},
            "rating": {
                "type": "number",
                "minimum": 1,
                "maximum": 5
            },
            "summary": {"type": "string"},
            "pros": {
                "type": "array",
                "items": {"type": "string"}
            },
            "cons": {
                "type": "array",
                "items": {"type": "string"}
            }
        },
        "required": ["title", "rating", "summary", "pros", "cons"]
    }

    prompt = "Give me a review of the book '1984' by George Orwell"

    try:
        print("\nSequential calls:")
        
        try:
            # Using the retry wrapper instead of direct call
            response = await retry_structured_completion(
                prompt=prompt,
                json_schema=BOOK_REVIEW_SCHEMA,
                model_name="gpt-4o-mini",
                retries=3,
                wait_time=0.25
            )
            print("\nResponse from gpt-4o-mini:")
            print(json.dumps(response, indent=2))
        except Exception as e:
            print(f"Error with gpt-4o-mini at line {e.__traceback__.tb_lineno}: {e}")

        try:
            response = await get_structured_completion_async(
                prompt=prompt,
                json_schema=BOOK_REVIEW_SCHEMA,
                model_name="claude-3-opus-20240229"
            )
            print("\nResponse from claude-3-opus:")
            print(json.dumps(response, indent=2))
        except Exception as e:
            print(f"Error with claude-3-opus at line {e.__traceback__.tb_lineno}: {e}")

        try:
            response = await get_structured_completion_async(
                prompt=prompt,
                json_schema=BOOK_REVIEW_SCHEMA,
                model_name="gpt-4o"
            )
            print("\nResponse from gpt-4o:")
            print(json.dumps(response, indent=2))
        except Exception as e:
            print(f"Error with gpt-4o at line {e.__traceback__.tb_lineno}: {e}")

        try:
            response = await get_structured_completion_async(
                prompt=prompt,
                json_schema=BOOK_REVIEW_SCHEMA,
                model_name="deepseek-v3"
            )
            print("\nResponse from deepseek-v3:")
            print(json.dumps(response, indent=2))
        except Exception as e:
            print(f"Error with deepseek-v3 at line {e.__traceback__.tb_lineno}: {e}")

        # Demonstrate batch processing
        print("\nBatch processing example:")
        book_prompts = [
            "Review the book 'To Kill a Mockingbird'",
            "Review the book 'The Great Gatsby'",
            "Review the book 'Brave New World'"
        ]
        batch_results = await batch_process_completions(
            prompts=book_prompts,
            json_schema=BOOK_REVIEW_SCHEMA,
            model_name="gpt-4o-mini"
        )
        for i, result in enumerate(batch_results):
            if isinstance(result, Exception):
                print(f"Error processing prompt {i}: {result}")
            else:
                print(f"\nResult {i}:")
                print(json.dumps(result, indent=2))

    except Exception as e:
        print(f"Error in test harness at line {e.__traceback__.tb_lineno}: {e}")

if __name__ == "__main__":
    asyncio.run(main())