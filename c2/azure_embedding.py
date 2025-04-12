import os
from openai import AzureOpenAI

api_version = "2024-02-01"
endpoint = "https://guha-m91xe3zb-westus.cognitiveservices.azure.com/"
model_name = "text-embedding-3-small"
deployment = "text-embedding-3-small"

azure_embedding_client = None
async def get_azure_embedding(text):
    """Get embedding for a single text input using text-embedding-3-small model"""
    global azure_embedding_client
    if azure_embedding_client is None:
        azure_embedding_client = AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=os.environ.get("AZURE_EMBEDDING_API_KEY"),
            api_version=api_version
        )
    response = azure_embedding_client.embeddings.create(
        input=text,
        model=deployment
    )
    # Return the embedding vector
    return response.data[0].embedding




