from azure.ai.inference import ChatCompletionsClient
from azure.core.credentials import AzureKeyCredential
from azure.ai.inference.models import SystemMessage, UserMessage
import os
import json
import asyncio
from openai import AzureOpenAI
import time
import mllm

# For Serverless API or Managed Compute endpoints
deepseek_client = None
azure_openai_4o_client = None

# Azure OpenAI endpoint (Make sure this matches your actual endpoint exactly)
azure_openai_4o_endpoint = "https://guha-m91xe3zb-westus.cognitiveservices.azure.com/"



deepseek_client = None
def get_deepseek_client ():
    global deepseek_client
    if (deepseek_client is None):
        deepseek_client = ChatCompletionsClient(
            endpoint="https://guha-m91xe3zb-westus.services.ai.azure.com/models",
            credential=AzureKeyCredential(os.environ["AZURE_DEEPSEEK_KEY"])
        )
    return deepseek_client

def get_azure_openai_4o_client():
    global azure_openai_4o_client
    if azure_openai_4o_client is None:
        azure_openai_4o_client = AzureOpenAI(
            azure_endpoint=azure_openai_4o_endpoint,
            api_key=os.environ.get("AZURE_OPENAI_4o_API_KEY"),
            api_version="2024-12-01-preview"
        )
    return azure_openai_4o_client

def clean_ds_response(content):
    response_text = content.strip()
    response_text = content.replace('```json', '').replace('```', '').strip()
            
    # Ensure we're only getting the JSON part
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

async def get_completion_ds(prompt, ans_struc, model_name="DeepSeek-V3"):
    client = get_deepseek_client()
    system_prompt = f"""Provide a response that matches this JSON schema: {json.dumps(ans_struc)}"""
    response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: client.complete(
                    messages=[
                        SystemMessage(content=system_prompt),
                        UserMessage(content=prompt)
                    ],
                    max_tokens=248,
                    temperature=0.7,
                    top_p=0.1,
                    stream=False,
                    presence_penalty=0.0,
                    frequency_penalty=0.0,
                  #  model="DeepSeek-V3"
                    model=model_name
                )
            )
    ansr_str = response.choices[0].message.content
    ansr = clean_ds_response(ansr_str)
    return ansr

async def get_completion_oai(prompt, ans_struc, model_name="gpt-4o"):   
    client = get_azure_openai_4o_client()
    system_prompt = f"""Provide a response that matches this JSON schema: {json.dumps(ans_struc)}"""
    
    # Map model names to deployment names if necessary
    deployment_name = model_name.lower()
        
    response = await asyncio.get_event_loop().run_in_executor(
        None,
        lambda: client.chat.completions.create(
            messages=[
                    SystemMessage(content=system_prompt),
                    UserMessage(content=prompt)
                ],
                max_tokens=248,
                temperature=0.7,
                top_p=0.1,
                stream=False,
                presence_penalty=0.0,
                frequency_penalty=0.0,
                model=model_name  # Changed 'model' to 'deployment_name'
            )
        )
    ansr_str = response.choices[0].message.content
    ansr = clean_ds_response(ansr_str)
    return ansr

async def get_completion(prompt, ans_struc, model_name="gpt-4o-mini"):
    if model_name.lower() in ["auto"]:
        model_name = "gpt-4o-mini"
    if model_name.lower() in ["gpt-4o", "gpt-4o-mini"]:
        return await get_completion_oai(prompt, ans_struc, model_name)
    elif model_name.lower() in ["deepseek-v3"]:
        return await get_completion_ds(prompt, ans_struc, model_name)
    else:
        raise ValueError(f"Unsupported model: {model_name}")

async def test_completions():
    prompt = "I am going to Paris, what should I see?"
    ans_struc = {
        "type": "object",
        "properties": {
            "answer": {"type": "string"}
        },
        "required": ["answer"]
    }
    start_time = time.time()
    ansr = await get_completion(prompt, ans_struc, model_name="deepseek-v3")
    deepseek_time = time.time() - start_time
    print(f"DeepSeek-V3 ({deepseek_time:.2f}s): {ansr}\n\n")

    start_time = time.time()
    ansr = await get_completion(prompt, ans_struc, model_name="gpt-4o") 
    gpt4_time = time.time() - start_time
    print(f"gpt-4o ({gpt4_time:.2f}s): {ansr}\n\n")

    start_time = time.time()
    ansr = await get_completion(prompt, ans_struc, model_name="gpt-4o-mini") 
    gpt4_mini_time = time.time() - start_time
    print(f"gpt-4o-mini ({gpt4_mini_time:.2f}s): {ansr}\n\n")

    start_time = time.time()
    ansr = await mllm.get_structured_completion_async(prompt, ans_struc, model_name="gpt-4o")
    mllm_time = time.time() - start_time
    print(f"mllm gpt-4o ({mllm_time:.2f}s): {ansr}\n\n")

    start_time = time.time()
    ansr = await mllm.get_structured_completion_async(prompt, ans_struc, model_name="gpt-4o-mini")
    mini_time = time.time() - start_time
    print(f"mllm gpt-4o-mini ({mini_time:.2f}s): {ansr}\n\n")
    # Print information for debugging
    
if __name__ == "__main__":
    # Uncomment one of these to test
    # test_deepseek()
    asyncio.run(test_completions())