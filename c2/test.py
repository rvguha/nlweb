import os
from openai import AzureOpenAI

endpoint = "https://guha-m91xe3zb-westus.cognitiveservices.azure.com/"
model_name = "gpt-4o"
deployment = "gpt-4o"

subscription_key = "GCr013lpyI1Zf3o3sUSoVQGYS0nrsP1LDHSoGGnOnhZqiZCYVIILJQQJ99BDAC4f1cMXJ3w3AAAAACOGDKue" #os.environ.get("AZURE_OPENAI_4o_API_KEY")
api_version = "2024-12-01-preview"

client = AzureOpenAI(
    api_version=api_version,
    azure_endpoint=endpoint,
    api_key=subscription_key,
)

response = client.chat.completions.create(
    messages=[
        {
            "role": "system",
            "content": "You are a helpful assistant.",
        },
        {
            "role": "user",
            "content": "I am going to Paris, what should I see?",
        }
    ],
    max_tokens=4096,
    temperature=1.0,
    top_p=1.0,
    model=deployment
)

print(response.choices[0].message.content)