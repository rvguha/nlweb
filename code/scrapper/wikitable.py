

import requests
from bs4 import BeautifulSoup
import json
import sys


def parse_wikitable(url, type):
    # Fetch the Wikipedia page
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    # Find all wikitables with the specified class
    tables = soup.find_all('table', class_='wikitable')
   
    all_table_data = []
    
    for table in tables:
        # Get all rows
        rows = table.find_all('tr')
        
        if not rows:
            continue
            
        # Extract headers from first row
        headers = []
        header_row = rows[0]
        for header in header_row.find_all(['th', 'td']):
            # Clean header text by removing newlines and extra spaces
            header_text = header.text.strip().replace('\n', ' ').replace('\xa0', ' ')
            headers.append(header_text)
        
        # Process remaining rows
        for row in rows[1:]:
            cells = row.find_all(['td', 'th'])
            
            # Create dictionary for this row
            row_data = {}
            row_data['type'] = type
            for header, cell in zip(headers, cells):
                # Clean cell text
                cell_content= cell.text.strip().replace('\n', ' ').replace('\xa0', ' ')
             #   cell_content = cell.find_all(recursive=False)
             #   print("header=%s, cell_content=%s" % (header, cell_content))
                row_data[header] = str(cell_content)
                
            all_table_data.append(row_data)
    
    return all_table_data

def save_to_json(data, output_file):
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def extract_tables_from_wiki(wiki_url, output_file, type):
    # Parse the wikitables from the URL
    table_data = parse_wikitable(wiki_url, type)
    # Save the extracted data to JSON file
    save_to_json(table_data, output_file)
    
    return output_file

if __name__ == "__main__":
    # Example usage
    if len(sys.argv) != 3:
        print("Usage: python wikitable.py <wikipedia_url> <type>")
        sys.exit(1)
        
    wiki_url = sys.argv[1]
    type = sys.argv[2]
    # Extract the last segment of the URL to use as filename
    output_file = wiki_url.rstrip('/').split('/')[-1] + '.json'
    
    extract_tables_from_wiki(wiki_url, output_file, type)

