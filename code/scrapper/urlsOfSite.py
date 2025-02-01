import requests
import xml.etree.ElementTree as ET
import os
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser
import sys
import re
from bs4 import BeautifulSoup
from zenrows import ZenRowsClient
import gzip
import io

ZENROW_API_KEY = "8248bbed30f328e70a4db209f2cc5e96adc858c3"
client = ZenRowsClient(ZENROW_API_KEY)

def fetch_with_zenrows(url):
    # ZenRows API endpoint and your API key
    response = client.get(url)
    if (".gz" in url):
        with gzip.GzipFile(fileobj=io.BytesIO(response.content)) as gz:
        # Read the decompressed data
            decompressed_data = gz.read()
            return decompressed_data.decode(utf-8)
    else:
        return response.text

def get_sitemaps_from_robots(site):
    try:
        robots_content = client.get(f"{site}/robots.txt").content.decode('utf-8')
        sitemaps = []
        print(robots_content)
        for line in robots_content.split('\n'):
            line = line.strip()
            print(line)
            if line.lower().startswith('sitemap:'):
                sitemap_url = line.split(':', 1)[1].strip()
                sitemaps.append(sitemap_url)
        return sitemaps
    except:
        print("Error getting sitemaps from robots.txt")
        return []

def parse_sitemap(sitemap_url, f):
    print("Parsing sitemap: %s" % sitemap_url)
    try:
        response = client.get(sitemap_url).content.decode('utf-8')
       
        root = ET.fromstring(response)
      
        # Check if this is a sitemap index
        sitemaps = root.findall('.//{*}sitemap')
        if sitemaps:
            # Recursively process each sitemap in the index
            for sitemap in sitemaps:
                sitemap_loc = sitemap.find('.//{*}loc').text.strip()
                parse_sitemap(sitemap_loc, f)
        else:
            # This is a regular sitemap, extract URLs
            urls = root.findall('.//{*}url')
            print(len(urls))
            for url in urls:
                url_loc = url.find('.//{*}loc').text.strip()
                f.write(url_loc + "\n")
    except Exception as e:
        print(f"Error processing sitemap {sitemap_url}: {str(e)}")
        

def get_site_urls(site, sitemap=None):
    if not site.startswith(('http://', 'https://')):
        site = 'https://' + site
    
    # Create output directory if it doesn't exist
    output_dir = '/Users/guha/mahi/data/sites'
    os.makedirs(output_dir, exist_ok=True)
    
    # Get domain name for file naming
    domain = urlparse(site).netloc
    output_file = open(os.path.join(output_dir, f"{domain}_urls.txt"), 'w')
    
    # Get sitemaps from robots.txt
    if (sitemap is None):
        sitemaps = get_sitemaps_from_robots(site)
    else:
        sitemaps = [sitemap]
    
    for sitemap in sitemaps:
        parse_sitemap(sitemap, output_file)
   
    output_file.close()

if __name__ == "__main__":
    # Example usage
    if len(sys.argv) == 2:
        site = sys.argv[1]
        output_file = get_site_urls(site)
        print(f"URLs have been written")
    elif len(sys.argv) == 3:
        site = sys.argv[1]
        sitemap = sys.argv[2]
        output_file = get_site_urls(site, sitemap)
        print(f"URLs have been written")
    else:
        print("Usage: python urlsOfSite.py <site> <sitemap>")
        sys.exit(1)
