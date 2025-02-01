
import time
import openai 
import numpy as np
import sys

# Set your OpenAI API key
openai.api_key = "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"


client = openai.OpenAI()

EMBEDDINGS_PATH_SMALL = "/Users/guha/mahi/data/sites/embeddings/small"
EMBEDDINGS_PATH_LARGE = "/Users/guha/mahi/data/sites/embeddings/large"

EMBEDDING_MODEL_SMALL = "text-embedding-3-small"
EMBEDDING_MODEL_LARGE = "text-embedding-3-large"

JSONL_PATH = "/Users/guha/mahi/data/sites/jsonl/"

def get_embedding(text, model="text-embedding-3-small"):
   text = text.replace("\n", " ")
   return client.embeddings.create(input = [text], model=model).data[0].embedding


def read_file_content(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        return content
    except Exception as e:
        print(f"Error reading file {file_path}: {str(e)}")
        return None
    
def clean_utf8(text):
    return text.encode('utf-8', errors='ignore').decode('utf-8')

def process_files(input_file, size="small", model="text-embedding-3-small", num_to_process=10000000):
    num_done = 0
    if (size == "small"):
        output_path = EMBEDDINGS_PATH_SMALL + "/" + input_file + ".txt"
        model = EMBEDDING_MODEL_SMALL
    else:
        output_path = EMBEDDINGS_PATH_LARGE + "/" + input_file + ".txt"
        model = EMBEDDING_MODEL_LARGE
    input_path = JSONL_PATH + input_file + "_schemas.txt"
    
    try:
        with open(input_path, 'r') as input_file, \
             open(output_path, 'w', encoding='utf-8') as output_file:
            
            batch = []
            batch_urls = []
            batch_jsons = []
            
            for line in input_file:
                # Skip empty lines
                if not line.strip():
                    continue
                
                line = clean_utf8(line)
                try:
                    # Split line by tab
                    url, json_str = line.strip().split('\t')
                    
                    batch_urls.append(url)
                    batch_jsons.append(json_str)
                    batch.append(json_str[0:6000])
                    num_done += 1
                    # Process batch when it reaches size 100
                    if len(batch) == 100 or (num_done > num_to_process):
                        # Get embeddings for the batch
                        embeddings = client.embeddings.create(input=batch, model=model).data
                        
                        # Write results for the batch
                        for i in range(len(batch)):
                            output_file.write(f"{batch_urls[i]}\t{batch_jsons[i]}\t{embeddings[i].embedding}\n")
                        print(f"Processed {num_done} lines")
                        # Clear the batches
                        batch = []
                        batch_urls = []
                        batch_jsons = []
                        time.sleep(5)
                except Exception as e:
                    print(f"Error processing line: {str(e)}")
                    continue
                if num_done > num_to_process:
                    break
            # Process any remaining items in the final batch
            if batch:
                embeddings = client.embeddings.create(input=batch, model=model).data
                for i in range(len(batch)):
                    output_file.write(f"{batch_urls[i]}\t{batch_jsons[i]}\t{embeddings[i].embedding}\n")
                    
    except Exception as e:
        print(f"Error processing files: {str(e)}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python embedding.py <input_file> <model>")
        sys.exit(1)
        
    input_file = sys.argv[1]
    model = sys.argv[2] # "small" or "large"        
    process_files(input_file, model)

