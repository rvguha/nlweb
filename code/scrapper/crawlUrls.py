import sys
import os
import requests
from urllib.parse import urlparse
from zenrows import ZenRowsClient
import time


ZENROW_API_KEY = "8248bbed30f328e70a4db209f2cc5e96adc858c3"
client = ZenRowsClient(ZENROW_API_KEY)

def crawl_urls(input_file, target_dir):
    # Create target directory if it doesn't exist
    os.makedirs(target_dir, exist_ok=True)
    
    # Read URLs from input file
    with open(input_file, 'r') as f:
        urls = f.readlines()
 #   client = ZenRowsClient(ZENROW_API_KEY)
    # Process each URL
    for url in urls:
        url = url.strip()
        if not url:
            continue
        
        try:
            # Fetch URL content
            
           
            
            # Generate filename from URL
            parsed_url = urlparse(url)
            filename = parsed_url.netloc + parsed_url.path
            if filename.endswith('/'):
                filename = filename[:-1]
            filename = filename.replace('/', '_') + '.html'
            
            # Write content to file
            output_path = os.path.join(target_dir, filename)

              # Skip if file already exists
            if os.path.exists(output_path):
                print(f"File already exists, skipping: {output_path}")
                continue
                
            # Fetch URL content
            response = client.get(url)
            if (len(response.text) < 1000):
                print(f"Too small ({len(response.text)} bytes) for {url}")
                continue
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(response.text)

            print(f"Successfully crawled: {url} %i " % (len(response.text)))
            time.sleep(2)
        except Exception as e:
            print(f"Error crawling {url}: {str(e)}")
            # Sleep for 5 seconds between requests
            time.sleep(5)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python crawlUrls.py <input_file> <target_directory>")
        sys.exit(1)
        
    input_file = sys.argv[1]
    target_dir = sys.argv[2]

    input_file = "/Users/guha/mahi/data/sites/" + input_file
    target_dir = "/Users/guha/mahi/data/sites/" + target_dir
    
    crawl_urls(input_file, target_dir)
