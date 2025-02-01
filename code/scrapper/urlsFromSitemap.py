import requests
import xml.etree.ElementTree as ET
import gzip
from io import BytesIO
import sys
from urllib.parse import urljoin
import zenrows

ZENROW_API_KEY = "8248bbed30f328e70a4db209f2cc5e96adc858c3"
client = zenrows.ZenRowsClient(ZENROW_API_KEY)

USE_ZENROWS = True

def extract_urls_from_sitemap(sitemap_url, output_file):
    try:
        # Fetch sitemap content
        if (USE_ZENROWS):
            response = client.get(sitemap_url, headers={"Accept-Encoding": "identity"})
            content = response.content
        else:
            response = requests.get(sitemap_url, headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8', 'Accept-Language': 'en-US,en;q=0.5', 'Accept-Encoding': 'gzip, deflate', 'DNT': '1', 'Connection': 'keep-alive', 'Upgrade-Insecure-Requests': '1'})
            if sitemap_url.endswith('.gz'):
                content = gzip.GzipFile(fileobj=BytesIO(response.content)).read()
            else:
                content = response.content
        # Write raw content to test file
        with open('test.txt', 'wb') as test_file:
            test_file.write(content)

        # Parse XML
        root = ET.fromstring(content)

        # Handle both sitemap index files and regular sitemaps
        # Remove namespace for easier parsing
        namespace = root.tag[1:].split("}")[0] if "}" in root.tag else ""
        ns = {"ns": namespace} if namespace else {}

        # Open output file in append mode
        with open(output_file, 'a') as f:
            # Check if this is a sitemap index
            sitemaps = root.findall(".//ns:sitemap", ns) if ns else root.findall(".//sitemap")
            if sitemaps:
                # This is a sitemap index
                for sitemap in sitemaps:
                    loc = sitemap.find("ns:loc", ns) if ns else sitemap.find("loc")
                    if loc is not None:
                        # Recursively process each sitemap
                        extract_urls_from_sitemap(loc.text, output_file)
            else:
                # This is a regular sitemap
                urls = root.findall(".//ns:url", ns) if ns else root.findall(".//url")
                for url in urls:
                    loc = url.find("ns:loc", ns) if ns else url.find("loc")
                    if loc is not None:
                        f.write(loc.text + '\n')

    except Exception as e:
        print(f"Error processing sitemap {sitemap_url}: {str(e)}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python urlsFromSitemap.py <sitemap_url> <output_file>")
        sys.exit(1)

    sitemap_url = sys.argv[1]
    output_file = sys.argv[2]
    
    # Clear/create the output file
    open(output_file, 'w').close()
    
    # Start processing
    extract_urls_from_sitemap(sitemap_url, output_file)
