import sys
import os
import requests
from urllib.parse import urlparse
from zenrows import ZenRowsClient
import time
import json
from bs4 import BeautifulSoup

ZENROW_API_KEY = "8248bbed30f328e70a4db209f2cc5e96adc858c3"
client = ZenRowsClient(ZENROW_API_KEY)

def get_base_neurips_urls():
    urls = []
    for year in range(2017, 2023):
        url = f"https://neurips.cc/virtual/{year}/calendar"
        urls.append(url)
    return urls

def get_neurips_session_urls(year):
    url = f"https://neurips.cc/virtual/{year}/calendar"
    response = client.get(url)
    urls = []
    soup = BeautifulSoup(response.text, 'html.parser')
    timeboxes = soup.find_all('div', class_='timebox')
    
    for timebox in timeboxes:
        links = timebox.find_all('a')
        for link in links:
            if 'href' in link.attrs:
                if link['href'].startswith('/virtual/'):
                    urls.append('https://neurips.cc' + link['href'])
    
    print(f"Found {len(urls)} session URLs for year {year}")
    return urls

def get_text(bs):
    if bs is None:
        return ""           
    text = bs.text.replace("\n", "").replace("\t", " ")
    while "  " in text:
        text = text.replace("  ", " ")
    return text

def extract_talk_details(url, type):
    response = client.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    title = get_text(soup.find('h2', class_='main-title'))
    authors = get_text(soup.find('h3', class_='card-subtitle'))
    abstract = get_text(soup.find('div', id='abstractExample'))
    if (title == ""):
        print(f"No title found for {url}")
        return None
    schema = {
        "@context": "https://schema.org",
        "@type": type, 
        "name": title,
        "description": abstract,
        "author": authors,
        "url": url
    }
    json_ld = json.dumps(schema, separators=(',', ':'))
    return json_ld
    
def extract_item_details(url):
    type = None
    if ("poster" in url):
        type = "NeurIPSPoster"
    elif ("oral" in url):
        type = "Oral"
    elif ("invited" in url):
        type = "InvitedTalk"
    if (type is not None):
        return extract_talk_details(url, type)
    else:
        return None

def extract_neurips_items(year, output):
    urls = get_neurips_session_urls(year)
    all_items = []
    for url in urls:
        item = extract_item_details(url)
        if (item is not None):  
            output.write(f"{url}\t{item}\n")
            all_items.append(item)
    return all_items

def extract_neurips_items_all():
    output = open("neurips_schemas.txt", "w")
    for year in range(2017, 20245):
        items = extract_neurips_items(year, output)
        count = len(items)
        print(f"Found {count} items for year {year}")
    output.close()

def extract_neurips_items_2023():
    output = open("neurips_schemas_2023.txt", "w")
    items = extract_neurips_items(2023, output)
    count = len(items)
    print(f"Found {count} items for year 2023")
    output.close()

extract_neurips_items_2023()
    
