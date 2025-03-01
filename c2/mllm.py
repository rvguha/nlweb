from typing import Any, Dict, Optional
import json
from enum import Enum
import asyncio
import anthropic
from anthropic import AsyncAnthropic
import google.generativeai as genai
from openai import OpenAI, AsyncOpenAI
import jsonschema

class ModelProvider(Enum):
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GEMINI = "gemini"


def determine_best_model(prompt, query_id="Ranking", model_family="gpt") -> str:
    return "gpt-4o-mini"

class LLMClients:
    _openai: Optional[OpenAI] = None
    _async_openai: Optional[AsyncOpenAI] = None
    _anthropic: Optional[anthropic.Anthropic] = None
    _async_anthropic: Optional[AsyncAnthropic] = None
    
    @classmethod
    def get_openai(cls) -> OpenAI:
        if cls._openai is None:
            cls._openai = OpenAI()
        return cls._openai
    
    @classmethod
    def get_async_openai(cls) -> AsyncOpenAI:
        if cls._async_openai is None:
            cls._async_openai = AsyncOpenAI()
        return cls._async_openai
    
    @classmethod
    def get_anthropic(cls) -> anthropic.Anthropic:
        if cls._anthropic is None:
            cls._anthropic = anthropic.Anthropic()
        return cls._anthropic
    
    @classmethod
    def get_async_anthropic(cls) -> AsyncAnthropic:
        if cls._async_anthropic is None:
            cls._async_anthropic = AsyncAnthropic()
        return cls._async_anthropic


def get_provider(model_name: str) -> ModelProvider:
    """Determine the provider from the model name."""
    if model_name.startswith(("gpt-")):
        return ModelProvider.OPENAI
    elif model_name.startswith(("claude-", "anthropic.")):
        return ModelProvider.ANTHROPIC
    elif model_name.startswith("gemini-"):
        return ModelProvider.GEMINI
    else:
        raise ValueError(f"Unknown model provider for model: {model_name}")


def get_embedding(query: str) -> list[float]:
    client = LLMClients.get_openai()
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=query
    )
    return response.data[0].embedding

def get_structured_completion(
    prompt: str,
    json_schema: Dict[str, Any],
    model_name: str,
    temperature: float = 0.7
) -> Dict[str, Any]:
    """
    Synchronously get a structured completion from various LLM providers.
    
    Args:
        prompt (str): The prompt to send to the model
        json_schema (Dict[str, Any]): The JSON schema that the response should conform to
        model_name (str): The model name (e.g., "gpt-4", "claude-3-opus-20240229", "gemini-pro")
        temperature (float, optional): Sampling temperature. Defaults to 0.7
        
    Returns:
        Dict[str, Any]: The structured response conforming to the provided schema
    """
    if (model_name == "auto"):
        model_name = determine_best_model(prompt)
    provider = get_provider(model_name)
    
    # Create the system prompt that includes the schema
    system_prompt = f"""
    Provide a response that matches this JSON schema:
    {json.dumps(json_schema)}
    """

    try:
        if provider == ModelProvider.OPENAI:
            client = LLMClients.get_openai()
            response = client.chat.completions.create(
                model=model_name,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
              #  temperature=temperature
            )
            result = json.loads(response.choices[0].message.content)

        elif provider == ModelProvider.ANTHROPIC:
            client = LLMClients.get_anthropic()
            response = client.messages.create(
                model=model_name,
                max_tokens=1024,
                temperature=temperature,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            result = json.loads(response.content[0].text)

        elif provider == ModelProvider.GEMINI:
            genai.configure()
            model = genai.GenerativeModel(model_name)
            
            # Modify prompt to strongly emphasize JSON output
            gemini_prompt = f"""
            {system_prompt}
            
            IMPORTANT: Your response must be ONLY valid JSON - no other text, no markdown formatting.
            Start your response with a curly brace and end with a curly brace.
            
            User request: {prompt}
            """
            
            response = model.generate_content(
                gemini_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=temperature
                )
            )
            
            # Clean up the response to ensure it's valid JSON
            response_text = response.text.strip()
            response_text = response_text.replace('```json', '').replace('```', '').strip()
            
            # Ensure we're only getting the JSON part
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            if start_idx == -1 or end_idx == 0:
                raise ValueError("No valid JSON object found in response")
                
            json_str = response_text[start_idx:end_idx]
            
            try:
                result = json.loads(json_str)
            except json.JSONDecodeError as e:
                raise ValueError(f"Failed to parse Gemini response as JSON: {e}")

        # Validate the response against the schema
        jsonschema.validate(instance=result, schema=json_schema)
        return result

    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse model response as JSON: {e}")
    except jsonschema.exceptions.ValidationError as e:
        raise ValueError(f"Model response did not match schema: {e}")
    except Exception as e:
        raise ValueError(f"Error getting completion: {e}")

async def get_structured_completion_async(
    prompt: str,
    json_schema: Dict[str, Any],
    model_name: str,
    temperature: float = 0.7
) -> Dict[str, Any]:
   # print(prompt)
    if (model_name == "auto"):
        model_name = determine_best_model(prompt)

    """
    Asynchronously get a structured completion from various LLM providers.
    
    Args:
        prompt (str): The prompt to send to the model
        json_schema (Dict[str, Any]): The JSON schema that the response should conform to
        model_name (str): The model name (e.g., "gpt-4", "claude-3-opus-20240229", "gemini-pro")
        temperature (float, optional): Sampling temperature. Defaults to 0.7
        
    Returns:
        Dict[str, Any]: The structured response conforming to the provided schema
    """
    provider = get_provider(model_name)
    
    # Create the system prompt that includes the schema
    system_prompt = f"""Provide a response that matches this JSON schema: {json.dumps(json_schema)}"""
    
    try:
        if provider == ModelProvider.OPENAI:
            client = LLMClients.get_async_openai()
            response = await client.chat.completions.create(
                model=model_name,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature
            )
            result = json.loads(response.choices[0].message.content)

        elif provider == ModelProvider.ANTHROPIC:
            client = LLMClients.get_async_anthropic()
            response = await client.messages.create(
                model=model_name,
                max_tokens=1024,
                temperature=temperature,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            result = json.loads(response.content[0].text)

        elif provider == ModelProvider.GEMINI:
            # Note: As of now, Gemini doesn't have an official async API
            # We'll run it in a thread pool to avoid blocking
            genai.configure()
            model = genai.GenerativeModel(model_name)
            
            # Modify prompt to strongly emphasize JSON output
            gemini_prompt = f"""
            {system_prompt}
            
            IMPORTANT: Your response must be ONLY valid JSON - no other text, no markdown formatting.
            Start your response with a curly brace and end with a curly brace.
            
            User request: {prompt}
            """
            
            # Run Gemini in a thread pool since it doesn't have async API
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: model.generate_content(
                    gemini_prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=temperature
                    )
                )
            )
            
            # Clean up the response to ensure it's valid JSON
            response_text = response.text.strip()
            response_text = response_text.replace('```json', '').replace('```', '').strip()
            
            # Ensure we're only getting the JSON part
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            if start_idx == -1 or end_idx == 0:
                raise ValueError("No valid JSON object found in response")
                
            json_str = response_text[start_idx:end_idx]
            
            try:
                result = json.loads(json_str)
            except json.JSONDecodeError as e:
                raise ValueError(f"Failed to parse Gemini response as JSON: {e}")

        # Validate the response against the schema
        jsonschema.validate(instance=result, schema=json_schema)
        return result

    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse model response as JSON: {e}")
    except jsonschema.exceptions.ValidationError as e:
        raise ValueError(f"Model response did not match schema: {e}")
    except Exception as e:
        raise ValueError(f"Error getting completion: {e}")

# Example usage
async def main():
    # Example schema for a book review
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
        # Synchronous example
        print("\nSynchronous OpenAI call:")
        openai_response = get_structured_completion(
            prompt=prompt,
            json_schema=BOOK_REVIEW_SCHEMA,
            model_name="gpt-4-turbo-preview"
        )
        print(json.dumps(openai_response, indent=2))

        # Asynchronous examples
        print("\nAsynchronous calls:")
        async_responses = await asyncio.gather(
            get_structured_completion_async(
                prompt=prompt,
                json_schema=BOOK_REVIEW_SCHEMA,
                model_name="gpt-4-turbo-preview"
            ),
            get_structured_completion_async(
                prompt=prompt,
                json_schema=BOOK_REVIEW_SCHEMA,
                model_name="claude-3-opus-20240229"
            ),
            get_structured_completion_async(
                prompt=prompt,
                json_schema=BOOK_REVIEW_SCHEMA,
                model_name="gemini-pro"
            )
        )
        
        for i, response in enumerate(async_responses):
            print(f"\nResponse {i + 1}:")
            print(json.dumps(response, indent=2))

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())