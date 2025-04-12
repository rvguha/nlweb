import os
import csv
import json
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SearchField,
    SearchFieldDataType,
    SimpleField,
    SearchableField,
    VectorSearch,
    VectorSearchAlgorithmConfiguration,
    VectorSearchProfile,
    HnswAlgorithmConfiguration,
    VectorSearchAlgorithmKind
)

from db_create_utils import documentsFromCSVLine

SEARCH_SERVICE_ENDPOINT = "https://mahi-vector-search.search.windows.net"

EMBEDDINGS_PATH_SMALL = "/Users/guha/mahi/data/sites/embeddings/small/"
EMBEDDINGS_PATH_LARGE = "/Users/guha/mahi/data/sites/embeddings/large/"

all_dbs = ["seriouseats",
    "woksoflife",
    "imdb", 
   # "npr podcasts", 
    "neurips", 
    "backcountry", 
    "zillow", 
    "tripadvisor", 
    "seriouseats",
    "spruce",
    "cheftariq",
    "hebbarskitchen",
    "latam_recipes",
  #  "med podcast"
]  

test_db = ["nytimes"]

search_clients = {}
index_names = ["embeddings1536", "embeddings3072"]
SEARCH_SERVICE_ENDPOINT = "https://mahi-vector-search.search.windows.net"

def get_index_client(index_name):
    """Get a search client for a specific index"""
    if (index_name in search_clients):
        return search_clients[index_name]
    else:
        initialize_clients()
        return search_clients[index_name]

def initialize_clients():
    # Use provided API key or get from environment variable
    
    api_key = os.environ.get("AZURE_SEARCH_API_KEY")
    if not api_key:
        raise ValueError("API key not provided and AZURE_SEARCH_API_KEY environment variable not set")
    
    credential = AzureKeyCredential(api_key)
    # Create index client for managing indexes
    index_client = SearchIndexClient(endpoint=SEARCH_SERVICE_ENDPOINT, credential=credential)
    search_clients["index_client"] = index_client
    
    # Create search clients for document operations
    for index_name in index_names:
        search_client = SearchClient(endpoint=SEARCH_SERVICE_ENDPOINT, index_name=index_name, credential=credential)
        search_clients[index_name] = search_client


def create_vector_search_config(algorithm_name="hnsw_config", profile_name="vector_config"):
    """Create and return a vector search configuration"""
    return VectorSearch(
        algorithms=[
            HnswAlgorithmConfiguration(
                name=algorithm_name,
                kind=VectorSearchAlgorithmKind.HNSW,
                parameters={
                    "m": 4,
                    "efConstruction": 400,
                    "efSearch": 500,
                    "metric": "cosine"
                }
            )
        ],
        profiles=[
            VectorSearchProfile(
                name=profile_name,
                algorithm_configuration_name=algorithm_name,
            )
        ]
    )


def drop_all_indices(service_endpoint, index_names=None):
    """
    Drop all specified indices from Azure Search service
    
    Args:
        service_endpoint (str): Azure Search service endpoint URL
        index_names (list, optional): List of index names to drop. If None, drops the default indices.
        
    Returns:
        list: List of dropped indices names
    """
    if index_names is None:
        index_names = ["embeddings1536", "embeddings3072"]
    
    dropped_indices = []    
    errors = []
    index_client = get_index_client("index_client")
    for index_name in index_names:
        try:
            index_client.delete_index(index_name)
            print(f"Index '{index_name}' dropped successfully.")
            dropped_indices.append(index_name)
        except Exception as e:
            error_message = str(e)
            if "ResourceNotFound" in error_message:
                print(f"Index '{index_name}' does not exist, skipping.")
            else:
                print(f"Error dropping index '{index_name}': {error_message}")
                errors.append({"index": index_name, "error": error_message})
    
    # Summary of operation
    if not errors:
        print(f"Successfully dropped {len(dropped_indices)} indices.")
    else:
        print(f"Dropped {len(dropped_indices)} indices with {len(errors)} errors.")
    
    return dropped_indices

def create_index_definition(index_name, embedding_size, profile_name="vector_config"):
    """Create and return an index definition with specified embedding size"""
    fields = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True, filterable=True),
        SimpleField(name="url", type=SearchFieldDataType.String,  filterable=True),
        SimpleField(name="name", type=SearchFieldDataType.String, filterable=True, sortable=True),
        SimpleField(name="site", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="schema_json", type=SearchFieldDataType.String, filterable=False),
        SearchField(
            name="embedding",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            vector_search_dimensions=embedding_size,
            vector_search_profile_name=profile_name
        )
    ]
    
    vector_search = create_vector_search_config(profile_name=profile_name)
    return SearchIndex(name=index_name, fields=fields, vector_search=vector_search)

def create_search_indices(service_endpoint, index_mapping=None):
    """Create search indices with different embedding sizes"""
    if index_mapping is None:
        # Default mapping between embedding sizes and index names
        index_mapping = {
            1536: "embeddings1536",
            3072: "embeddings3072"
        }
    
    # Make sure clients are initialized
    initialize_clients()
    
    # Get the proper index client for managing indices
    index_client = search_clients.get("index_client")
    if not index_client:
        raise ValueError("Index client not initialized properly")
        
    for embedding_size, index_name in index_mapping.items():
        index = create_index_definition(index_name, embedding_size)
        index_client.create_or_update_index(index)
        print(f"Index '{index_name}' created or updated successfully.")



def get_documents_from_csv(csv_file_path, site):
    """Read CSV file and return documents grouped by embedding size"""
    documents_by_size = {}
    
    with open(csv_file_path, 'r', encoding='utf-8') as file:
        for line in file:
            if line.strip():  # Skip empty lines
                try:
                    documents = documentsFromCSVLine(line, site)
                    for document in documents:
                        embedding_size = len(document['embedding'])
                        if embedding_size not in documents_by_size:
                            documents_by_size[embedding_size] = []
                
                        documents_by_size[embedding_size].append(document)
                except ValueError as e:
                    print(f"Skipping row due to error: {str(e)}")
    
    return documents_by_size

def upload_documents(service_endpoint, index_name, documents, site):
    """Upload documents to the specified index in batches"""
    index_client = get_index_client(index_name)
    
    batch_size = 500 if index_name == "embeddings3072" else 1000

    total_batches = (len(documents) + batch_size - 1) // batch_size
    
    for i in range(0, len(documents), batch_size):
        batch = documents[i:i+batch_size]
        current_batch = i // batch_size + 1
        index_client.upload_documents(batch)
        print(f"Uploaded batch {current_batch} of {total_batches} ({len(batch)} documents) to {index_name} from {site}")

def upload_data_from_csv(service_endpoint, csv_file_path, site, index_mapping=None, api_key=None):
    """Process CSV file and upload documents to appropriate indices"""
    if index_mapping is None:
        # Default mapping between embedding sizes and index names
        index_mapping = {
            1536: "embeddings1536",
            3072: "embeddings3072"
        }
    
    documents_by_size = get_documents_from_csv(csv_file_path, site)
    
    for size, documents in documents_by_size.items():
        if size in index_mapping:
            index_name = index_mapping[size]
            print(f"Found {len(documents)} documents with embedding size {size} from {site}")
            upload_documents(service_endpoint, index_name, documents, site)
        else:
            print(f"No index defined for embedding size {size}, skipping {len(documents)} documents")
    
    return sum(len(docs) for docs in documents_by_size.values())

def main():
    import sys

    # Parse command line argument
    complete_reload = False
    if len(sys.argv) > 1:
        reload_arg = sys.argv[1].lower()
        if reload_arg == "reload=true":
            complete_reload = True
        elif reload_arg == "reload=false":
            complete_reload = False
        else:
            print("Invalid argument. Use 'reload=true' or 'reload=false'")
            sys.exit(1)
    else:
        print("Please provide reload argument: reload=true or reload=false")
        sys.exit(1)
    # Azure AI Search configuration
    service_endpoint = SEARCH_SERVICE_ENDPOINT  # e.g., https://your-service-name.search.windows.net
    # API key will be read from environment variable AZURE_SEARCH_API_KEY
    
    # Define index mapping
    index_mapping = {
        1536: "embeddings1536",
        3072: "embeddings3072"
    }
    
    if (complete_reload):
        drop_all_indices(service_endpoint, list(index_mapping.values()))
        # Create indices if they don't exist
        create_search_indices(service_endpoint, index_mapping)
    
    # Delete all documents from indices
    # delete_all_documents(service_endpoint, list(index_mapping.values()))
    
    # Upload data from multiple CSV files
    #embdding_paths = [EMBEDDINGS_PATH_SMALL, EMBEDDINGS_PATH_LARGE]
    embdding_paths = [EMBEDDINGS_PATH_LARGE]
    for path in embdding_paths:
        csv_files = [f.replace('.txt', '') for f in os.listdir(path) if f.endswith('.txt')]
        
        total_documents = 0
        for csv_file in csv_files:
            print(f"\nProcessing file: {csv_file}")
            csv_file_path = f"{path}{csv_file}.txt"
            try:    
                documents_added = upload_data_from_csv(service_endpoint, csv_file_path, csv_file, index_mapping)
                total_documents += documents_added
            except Exception as e:
                print(f"Error processing file {csv_file}: {e}")
    
    print(f"\nData processing completed successfully. {total_documents} total documents added.")

if __name__ == "__main__":
    upload_data_from_csv(SEARCH_SERVICE_ENDPOINT, "/Users/guha/mahi/data/sites/embeddings/small/alltrails.txt", "alltrails", None)
   # main()