import openai 
import numpy as np
import sys
from pymilvus import MilvusClient

milvus_client = MilvusClient("./milvus_test.db")

client = openai.OpenAI()
url_json = {}
def load_embeddings(file_path):
    embeddings = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            # Skip empty lines
            if not line.strip():
                continue
                
            try:
                # Split line by tab into url and embedding string
                url, embedding_str = line.strip().split('\t')
                
                # Convert embedding string to list of floats
                embedding = [float(x) for x in embedding_str.strip('[]').split(',')]
                
                # Add [url, embedding] pair to results
                embeddings.append([url, embedding])
                
            except Exception as e:
                print(f"Error processing line: {str(e)}")
                continue
 #   print(f"Loaded {len(embeddings)} embeddings from {file_path}")
    return embeddings

def load_json(input_path):
    num_lines = 0
    try:
        with open(input_path, 'r', encoding='utf-8') as input_file:
            for line in input_file:
                # Skip empty lines
                if not line.strip():
                    continue
                url, json_str = line.strip().split('\t')
                url_json[url] = json_str
                num_lines += 1
    except Exception as e:
        print(f"Error processing line: {str(e)}")
 #   print(f"Loaded {num_lines} lines from {input_path}")
    return url_json
        

def get_embedding(text, model="text-embedding-3-small"):
   text = text.replace("\n", " ")
   return client.embeddings.create(input = [text], model=model).data[0].embedding

def cosine_similarity(vec1, vec2):
    return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

def retrieve_similar_urls(query_embedding, embeddings, threshold=0.3, num_results=20):
    similar_urls = []
    for url, embedding in embeddings:
        similarity = cosine_similarity(query_embedding, embedding)
        if similarity >= threshold:
            json_str = url_json[url]
            similar_urls.append([url, similarity, json_str])
    # Sort similar_urls by similarity score in descending order
    similar_urls.sort(key=lambda x: x[1], reverse=True)
    return similar_urls[:num_results]

def search_db(query):
    embedding = get_embedding(query)
    res = milvus_client.search(
        collection_name="test_collection",
        data=[embedding],
        limit=5,
        output_fields=["url", "text", "name"],
    )
    retval = []
#   print(len(res))
    for item in res[0]:
   #     print(len(item))
        ent = item["entity"]
        retval.append([ent["url"], ent["text"], ent["name"]])
    return retval

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python retrieval.py <query_text> <embeddings_file>")
        sys.exit(1)

    query_text = sys.argv[1]
    embeddings_file = sys.argv[2]
    
    embeddings = load_embeddings(embeddings_file)
    query_embedding = get_embedding(query_text)
    similar_urls = retrieve_similar_urls(query_embedding, embeddings)
    
    print(f"Similar URLs to '{query_text}':")
    for url in similar_urls:
        print(url)
