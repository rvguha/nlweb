import sys
import os
import requests
from urllib.parse import urlparse

def fetch_url(url):
    # Create target directory if it doesn't exist
    target_dir = '/Users/guha/mahi/data/sites/temp'
    os.makedirs(target_dir, exist_ok=True)

    try:
        # Fetch URL content
        response = requests.get(url)
        
        # Generate filename from URL
        parsed_url = urlparse(url)
        filename = parsed_url.netloc + parsed_url.path
        if filename.endswith('/'):
            filename = filename[:-1]
        filename = filename.replace('/', '_') + '.html'
        
        # Write content to file
        output_path = os.path.join(target_dir, filename)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(response.text)
            
        print(f"Successfully fetched {url} to {output_path}")
        
    except Exception as e:
        print(f"Error fetching {url}: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python fetch.py <url>")
        sys.exit(1)
        
    url = sys.argv[1]
    fetch_url(url)
