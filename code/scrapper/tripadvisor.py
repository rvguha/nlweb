import os
import xml.etree.ElementTree as ET
import requests
import time
import json
from datetime import datetime

def extract_urls_from_sitemaps(sitemap_dir, output_file):
    """
    Extract URLs from XML sitemaps in a directory and write them to a file.
    
    Args:
        sitemap_dir (str): Directory containing XML sitemap files
        output_file (str): File to write extracted URLs to
    """
    # Open output file for writing
    with open(output_file, 'w') as outfile:
        # Iterate through files in directory
        for filename in os.listdir(sitemap_dir):
            if filename.endswith('.gz'):
                import gzip
                sitemap_path = os.path.join(sitemap_dir, filename)
                with gzip.open(sitemap_path, 'rb') as gz_file:
                    content = gz_file.read()
                unzipped_path = sitemap_path[:-3] # Remove .gz extension
                with open(unzipped_path, 'wb') as unzipped_file:
                    unzipped_file.write(content)
                filename = filename[:-3] # Update filename to unzipped version
            if filename.endswith('.xml'):
                sitemap_path = os.path.join(sitemap_dir, filename)
                
                try:
                    # Parse XML sitemap
                    tree = ET.parse(sitemap_path)
                    root = tree.getroot()
                    
                    # Extract namespace from root tag
                    namespace = root.tag.split('}')[0] + '}'
                    
                    # Find all URL elements and extract loc
                    for url in root.findall('.//' + namespace + 'loc'):
                        if is_location_url(url.text, region='bay_area'):
                            outfile.write(url.text + '\n')
                    
                        
                except ET.ParseError as e:
                    print(f"Error parsing {filename}: {e}")
                except Exception as e:
                    print(f"Error processing {filename}: {e}")

def get_silicon_valley_cities():
    """Returns a list of Bay Area cities (Silicon Valley, SF, North Bay, East Bay) and their component words"""
    cities = [
        # Silicon Valley cities
        "Palo Alto",
        "Mountain View", 
        "Sunnyvale",
        "Santa Clara",
        "San Jose",
        "Cupertino",
        "Campbell",
        "Los Gatos",
        "Saratoga",
        "Los Altos",
        "Menlo Park",
        "Redwood City",
        "San Mateo",
        "Milpitas",
        "Morgan Hill",
        
        # San Francisco
        "San Francisco",
        
        # North Bay cities
        "San Rafael",
        "Novato",
        "Mill Valley",
        "Sausalito",
        "Tiburon",
        "Larkspur",
        "Corte Madera",
        
        # East Bay cities
        "Oakland",
        "Berkeley",
        "Alameda",
        "Emeryville",
        "Albany",
        "El Cerrito",
        "Richmond",
        "San Leandro",
        "Hayward",
        "Fremont",
        "Union City",
        "Newark",
        "Dublin",
        "Pleasanton",
        "Livermore",
        "Walnut Creek",
        "Pleasant Hill",
        "Concord",
        "Martinez"
    ]
    
    # Split multi-word cities into component words
    city_words = []
    for city in cities:
        words = city.lower().split()
        city_words.append({
            'full_name': city,
            'words': words
        })
    return city_words

def get_nyc_area_cities():
    """Returns a list of NYC area cities/boroughs/neighborhoods and their component words"""
    cities = [
        # Manhattan
        "Manhattan",
        "New York",
        "Upper East Side",
        "Upper West Side",
        "Lower Manhattan",
        "Midtown",
        "Greenwich Village",
        "SoHo",
        "Tribeca",
        "Harlem",
        "Chelsea",
        "Financial District",
        
        # Other NYC Boroughs
        "Brooklyn",
        "Queens",
        "Bronx",
        "Staten Island",
        "Long Island City",
        "Astoria",
        "Williamsburg",
        "Park Slope",
        "DUMBO",
        
        # Nearby Cities/Areas
        "Jersey City",
        "Hoboken",
        "Newark",
        "Weehawken",
        "Union City",
        "Fort Lee",
        "Yonkers",
        "New Rochelle",
        "White Plains",
        "Stamford",
        "Greenwich"
    ]
    
    # Split multi-word cities into component words
    city_words = []
    for city in cities:
        words = city.lower().split()
        city_words.append({
            'full_name': city,
            'words': words
        })
    return city_words

def is_location_url(url, region='all'):
    """
    Check if URL contains both a city name and state/region identifier
    
    Args:
        url (str): URL to check
        region (str): 'bay_area', 'nyc', or 'all' (default)
    
    Returns:
        tuple: (bool, city_name) if found, (False, None) if not
    """
    url = url.lower()
    # Check Bay Area URLs
    if region in ['bay_area', 'all']:
        if 'california' in url:
            cities = get_silicon_valley_cities()
            for city in cities:
                if all(word in url for word in city['words']):
                    return True
    
    # Check NYC area URLs
    if region in ['nyc', 'all']:
        if 'new york' in url or 'ny' in url or 'new jersey' in url or 'nj' in url:
            cities = get_nyc_area_cities()
            for city in cities:
                if all(word in url for word in city['words']):
                    return True
                
  #  print(f"Saying no to {url} because it's not a {region} URL")
    return False

# Rename the old function to maintain backward compatibility
def is_silicon_valley_url(url):
    """
    Legacy function - redirects to is_location_url with bay_area region
    """
    return is_location_url(url, region='bay_area')

def crawl_urls(input_file, output_dir, zenrows_api_key):
    """
    Crawl URLs from input file using ZenRows API and save the HTML content
    
    Args:
        input_file (str): File containing URLs to crawl (one per line)
        output_dir (str): Directory to save crawled HTML files
        zenrows_api_key (str): ZenRows API key
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # ZenRows API endpoint
    api_url = f"https://api.zenrows.com/v1/?apikey={zenrows_api_key}&js_render=true&wait=2000"
    
    # Read URLs from input file
    with open(input_file, 'r') as f:
        urls = [line.strip() for line in f if line.strip()]
    
    # Process each URL
    for url in urls:
        try:
            # Generate filename from URL
            filename = url.replace('https://', '').replace('http://', '').replace('/', '_')
            filename = f"{filename}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            output_path = os.path.join(output_dir, filename)
            
            # Skip if already crawled
            if os.path.exists(output_path):
                print(f"Skipping {url} - already crawled")
                continue
            
            print(f"Crawling {url}")
            
            # Make request through ZenRows
            response = requests.get(api_url, params={'url': url})
            
            if response.status_code == 200:
                # Store both HTML content and metadata
                result = {
                    'url': url,
                    'timestamp': datetime.now().isoformat(),
                    'status_code': response.status_code,
                    'content': response.text,
                    'headers': dict(response.headers)
                }
                
                # Save to file
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                
                print(f"Successfully saved {url} to {output_path}")
            else:
                print(f"Error crawling {url}: Status code {response.status_code}")
            
            # Rate limiting - 1 request per second
            time.sleep(1)
            
        except Exception as e:
            print(f"Error processing {url}: {e}")
            continue

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python tripadvisor.py <command> [args...]")
        print("Commands:")
        print("  extract <sitemap_directory> <output_file>")
        print("  crawl <input_file> <output_directory> <zenrows_api_key>")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "extract":
        if len(sys.argv) != 4:
            print("Usage: python tripadvisor.py extract <sitemap_directory> <output_file>")
            sys.exit(1)
            
        sitemap_dir = sys.argv[2]
        output_file = sys.argv[3]
        
        if not os.path.isdir(sitemap_dir):
            print(f"Error: {sitemap_dir} is not a valid directory")
            sys.exit(1)
            
        try:
            extract_urls_from_sitemaps(sitemap_dir, output_file)
            print(f"Successfully extracted URLs to {output_file}")
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)
            
    elif command == "crawl":
        if len(sys.argv) != 5:
            print("Usage: python tripadvisor.py crawl <input_file> <output_directory> <zenrows_api_key>")
            sys.exit(1)
            
        input_file = sys.argv[2]
        output_dir = sys.argv[3]
        zenrows_api_key = sys.argv[4]
        
        if not os.path.isfile(input_file):
            print(f"Error: {input_file} is not a valid file")
            sys.exit(1)
            
        try:
            crawl_urls(input_file, output_dir, zenrows_api_key)
            print("Crawling completed successfully")
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)
    
    else:
        print(f"Unknown command: {command}")
        print("Available commands: extract, crawl")
        sys.exit(1)


