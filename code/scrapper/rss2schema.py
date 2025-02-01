import xml.etree.ElementTree as ET
import json
import os

def process_rss_file(rss_file, output_file):
    # Parse RSS XML
    tree = ET.parse(rss_file)
    root = tree.getroot()
    
    # Find channel element
    channel = root.find('channel')
    if channel is None:
        print(f"No channel found in {rss_file}")
        return
        
    # Extract channel metadata, checking both default and itunes namespaces
    ns = {'itunes': 'http://www.itunes.com/dtds/podcast-1.0.dtd'}
    
    channel_title = channel.findtext('title') or channel.findtext('itunes:title', namespaces=ns)
    channel_desc = channel.findtext('description') or channel.findtext('itunes:summary', namespaces=ns)
    channel_link = channel.findtext('link')
    
    # Get image URL from either RSS image element or itunes:image
    image_url = None
    image_elem = channel.find('image')
    if image_elem is not None:
        image_url = image_elem.findtext('url')
    if not image_url:
        itunes_image = channel.find('itunes:image', namespaces=ns)
        if itunes_image is not None:
            image_url = itunes_image.get('href')

    # Process each item
    for item in channel.findall('item'):
        # Get item link
        item_link = item.findtext('link')
        if not item_link:
            continue
            
        # Get item metadata
        item_title = item.findtext('title') or item.findtext('itunes:title', namespaces=ns)
        item_desc = item.findtext('description') or item.findtext('itunes:summary', namespaces=ns)
        pub_date = item.findtext('pubDate')
            
        # Create schema.org JSON-LD
        schema = {
            "@context": "https://schema.org",
            "@type": "PodcastEpisode",
            "name": item_title,
            "description": item_desc,
            "datePublished": pub_date,
            "url": item_link,
            "partOfSeries": {
                "@type": "PodcastSeries",
                "name": channel_title,
                "description": channel_desc
            }
        }
            
        if image_url:
            schema["image"] = image_url
                
        # Write tab-separated line with URL and JSON-LD
        json_ld = json.dumps(schema, separators=(',', ':'))
        output_file.write(f"{item_link}\t[{json_ld}]\n")

def output_file(directory):
    # Get directory name and parent directory
    dir_name = os.path.basename(directory)
    parent_dir = os.path.dirname(directory)
    
    # Create output filename in parent directory
    return os.path.join(parent_dir, f"{dir_name}_schemas.txt")
    
     

def process_directory(directory):
    # Create output file
    
    file = output_file(directory)
    output = open(file, 'w')
    # Process each RSS file
    for filename in os.listdir(directory):
        if filename.endswith('.xml') or filename.endswith('.rss') or filename.endswith('.html'):
            input_path = os.path.join(directory, filename)
            try:
                process_rss_file(input_path, output)
                print(f"Processed {filename}")
            except Exception as e:
                print(f"Error processing {filename}: {str(e)}")

    output.close()
if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python rss2schema.py <directory>")
        sys.exit(1)
        
    directory = sys.argv[1]
    process_directory(directory)

