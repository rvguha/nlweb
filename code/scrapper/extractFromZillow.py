import sys
import openai
from bs4 import BeautifulSoup
import json
import os

extraction_prompt = """The following text contains a real estate listing. Extract the details of the house, including the address, 
number of rooms, square footage, price, the school district, schools, etc. and return the result in a schema.org format. The 
result should be a JSON object, which includes the url to the listing and has a title.
"""
sync_client = openai.OpenAI()

def extract_visible_text(html_file):
    """
    Takes an HTML file path as input, parses it using BeautifulSoup,
    and returns the visible text that would be displayed in a browser.
    
    Args:
        html_file (str): Path to HTML file
        
    Returns:
        str: Visible text content from the HTML
    """
    try:
        # Read the HTML file
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
            
        # Parse with BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
            
        # Get text and clean up whitespace
        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
            
        return text
        
    except Exception as e:
        print(f"Error processing {html_file}: {str(e)}")
        return None

def extract_schema_markup(html_file):
    # Read the HTML file
    with open(html_file, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Parse HTML with BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Find all script tags with type "application/ld+json"
    schema_tags = soup.find_all('script', type='application/ld+json')
    
    schemas = []
    for tag in schema_tags:
        try:
            # Parse JSON content
            schema = json.loads(tag.string)
            schemas.append(schema)
        except json.JSONDecodeError as e:
            print(f"Error parsing schema JSON: {e}")
            continue
            
    return schemas

def extract_first_image(schemas):
    """
    Extract the first image URL found in schema.org JSON objects.
    
    Args:
        schemas (list): List of schema.org JSON objects
        
    Returns:
        str: First image URL found, or None if no images found
    """
    for schema in schemas:
        # Check for direct image property
        if isinstance(schema, dict):
            if 'image' in schema:
                # Handle both string and list/array image values
                if isinstance(schema['image'], str):
                    return schema['image']
                elif isinstance(schema['image'], list) and len(schema['image']) > 0:
                    return schema['image'][0]
                elif isinstance(schema['image'], dict) and 'url' in schema['image']:
                    return schema['image']['url']
            
            # Check for nested image properties
            for value in schema.values():
                if isinstance(value, dict) and 'image' in value:
                    if isinstance(value['image'], str):
                        return value['image']
                    elif isinstance(value['image'], list) and len(value['image']) > 0:
                        return value['image'][0]
                    elif isinstance(value['image'], dict) and 'url' in value['image']:
                        return value['image']['url']
                        
    return None


def extract_from_zillow(html_file):
   
    sep = "moreAboutZestimatesResearchCareersCareers"
    full_text = extract_visible_text(html_file)
    text = full_text.split(sep)[0]
    image = extract_first_image(extract_schema_markup(html_file))
    prompt = extraction_prompt + text
    completion = sync_client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        temperature=0.0,
        messages=[
                {"role": "system", "content": "Rank the answer based on how relevant it is to the user's question."},
                {"role": "user", "content": prompt},
            ],
        )
    #  print(completion.choices[0].message.content)
    json_content = completion.choices[0].message.content.replace("```json", "").replace("```", "")
    js = json.loads(json_content)
    js["image"] = image
    return js

def process_zillow_files(input_dir, output_file):
    """
    Process all files in input directory and write extracted data to output file.
    
    Args:
        input_dir (str): Directory containing HTML files to process
        output_file (str): Path to output file to write results
    """
    try:
        with open(output_file, 'w', encoding='utf-8') as out_f:
            # Iterate through all files in input directory
            for filename in os.listdir(input_dir):
                filepath = os.path.join(input_dir, filename)
                
                # Skip if not a file
                if not os.path.isfile(filepath):
                    continue

                # Skip if filename contains San-Jose or San-Francisco
                if 'San-Jose' in filepath or 'San-Francisco' in filepath:
                  #  print(f"Skipping {filepath} - matches exclusion criteria")
                    continue
                
                if ("Los-Altos-Hills-CA" not in filepath and "Los-Altos-CA" not in filepath):
                    continue
                try:
                    # Extract data from file
                    extracted_data = extract_from_zillow(filepath)
                    
                    # Get URL from extracted data
                    url = extracted_data.get('url', '')
                    
                    # Convert extracted data to JSON string
                    json_str = json.dumps(extracted_data)
                    
                    # Write URL and JSON to output file
                    out_f.write(f"{url}\t[{json_str}]\n")
                    out_f.flush()
                    print(f"processed {filepath}")
                except Exception as e:
                    print(f"Error processing file {filepath}: {str(e)}")
                    continue
                    
    except Exception as e:
        print(f"Error writing to output file: {str(e)}")

home = "/Users/guha/mahi/data/sites/zillow/www.zillow.com_homedetails_409-Sycamore-St-San-Carlos-CA-94070_15556958_zpid.html"
#print(json.dumps(extract_from_zillow(home), indent=2))



def street_city_from_filename(filename):
    parts = filename.split('_')
    if len(parts) < 5:  # Need at least 5 parts to extract city (3 to N-2)
        return ""
    street_city_parts = parts[2:-2]  # Take from position 3 to N-2
   # print(street_city_parts)
    return "-".join(street_city_parts), parts[-2]

def get_third_path_component(url):
    # Split URL by '/' and return the 3rd component (index 2)
    parts = url.split('/')
    if len(parts) > 4:
        return parts[4]
    return ""

def create_street_city_dict(directory):
    street_city_dict = {}
    
    # List all files in directory
    for filename in os.listdir(directory):
        # Get full file path
        filepath = os.path.join(directory, filename)
        
        # Skip if not a file
        if not os.path.isfile(filepath):
            continue
            
        # Get street and city from filename
        street, city = street_city_from_filename(filename)
        
        # Add to dictionary if street is not empty
        if street:
            street_city_dict[street] = city
            
    return street_city_dict

def construct_valid_url(street_city, zpid):
    return f"https://www.zillow.com/homedetails/{street_city}/{zpid}_zpid/"

def process_urls_and_json(directory, input_file):
    # Get mapping of streets to cities
    street_city_dict = create_street_city_dict(directory)
    
    # Process each line in input file
    with open(input_file, 'r') as f:
        for line in f:
            # Split line into URL and JSON parts
            try:
                url, json_str = line.strip().split('\t')
                
                # Get key from URL
                key = get_third_path_component(url)
                if key in street_city_dict:
                    # Get city value and construct new URL
                    zpid = street_city_dict[key]
                    new_url = construct_valid_url(key, zpid)
               #     print(new_url)
                    # Update URL in JSON
                    json_data = json.loads(json_str)
                    json_data[0]['url'] = new_url
                    
                    # Print results
                  #  print(f"New URL: {new_url}")
                  #  print(f"Updated JSON: {json.dumps(json_data)}")
                    print(f"{new_url}\t[{json.dumps(json_data)}]")
                else:
                    print(f"No mapping found for key: {key}")
                    
            except Exception as e:
                print(f"Error processing line: {str(e)}")
                continue

#process_urls_and_json("/Users/guha/mahi/data/sites/zillow", "/Users/guha/mahi/data/sites/jsonl/zillow_schemas.txt")

if __name__ == "__main1__":
    if len(sys.argv) != 3:
        print("Usage: python extractFromZillow.py <input_dir> <output_file>")
        sys.exit(1)
        
    input_dir = sys.argv[1]
    output_file = sys.argv[2]
    
    # Validate input directory exists
    if not os.path.isdir(input_dir):
        print(f"Error: Input directory '{input_dir}' does not exist")
        sys.exit(1)
        
    print(f"Processing files from {input_dir}")
    print(f"Writing output to {output_file}")
    
    process_zillow_files(input_dir, output_file)
    
    print("Processing complete")

