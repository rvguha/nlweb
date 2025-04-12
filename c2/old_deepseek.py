from azure.ai.inference import ChatCompletionsClient
from azure.core.credentials import AzureKeyCredential
import os
import json
import asyncio
# For Serverless API or Managed Compute endpoints
deepseek_client = None
def get_deepseek_client ():
    global deepseek_client
    if (deepseek_client is None):
        deepseek_client = ChatCompletionsClient(
            endpoint="https://guha-m91xe3zb-westus.services.ai.azure.com/models",
            credential=AzureKeyCredential(os.environ["AZURE_DEEPSEEK_KEY"])
        )
    return deepseek_client

import os
from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage
from azure.core.credentials import AzureKeyCredential

endpoint = "https://guha-m91xe3zb-westus.services.ai.azure.com/models"
model_name = "DeepSeek-V3"

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
        raise ValueError(f"Failed to parse DeepSeek response as JSON: {e}")
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

def test_deepseek():
    client = get_deepseek_client()
    response = client.complete(
        messages=[
            SystemMessage(content="You are a helpful assistant."),
        UserMessage(content="I am going to Paris, what should I see?")
    ],
    max_tokens=2048,
    temperature=0.8,
    top_p=0.1,
    presence_penalty=0.0,
        frequency_penalty=0.0,
        model=model_name
    )
    print(response.choices[0].message.content)

if __name__ == "__main__":
    test_deepseek()


