import openai 
import numpy as np
import sys
import asyncio

import anthropic
import json

ANTHROPIC_API_KEY = "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"

seriouseats = """The user is trying to query seriouseats.com, a recipe site. Analyze the user query. If the query specifies a particular item and wants details 
                           about it, the field "seeks_particular_item" must be true. If the query is asking for multiple items, 
                            e.g., "vegan tacos and some salsas to go with it", the field "seeks_multiple_items" must be true. The 
                            field "item_queries" should contain independent queries for the different items. Return the answer in the following JSON format:
                            {
                           "seeks_multiple_item_types": "boolean",
                           "item_queries": ["string"]
                           }
                           
                           Ensure  the output is valid JSON.
                           """


imdb = """The user is trying to query imdb.com, a movie site. Analyze the user query. If the query specifies a particular item (like a movie or actor) and wants details 
                           about it, the field "seeks_particular_item" must be true and the field "item_query" should have a query that will find the item.  Return the answer in the following JSON format:
                            {
                           "seeks_particular_item": "boolean",
                           "item_query": "string" or null
                           }
                           
                           Ensure  the output is valid JSON.
                           """

class QueryAnalyzer:
    def __init__(self):
        self.client = anthropic.Client(api_key=ANTHROPIC_API_KEY)
        
    def analyze_query(self, site, query):
        prompt = seriouseats
        if (site == "imdb"):
            prompt = imdb
        message = self.client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=1000,
            temperature=0,
            system=prompt,
            messages=[
                {
                    "role": "user",
                    "content": f"The user query is: {query}"
                }
            ]
        )
        
        # Parse Claude's response as JSON
        try:
            print(message.content)
            query_analysis = json.loads(message.content[0].text)
            return query_analysis
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse Claude's response as JSON: {e}")
        except Exception as e:
            raise ValueError(f"Failed to validate article data: {e}")

# Example usage
def main():
    
    if len(sys.argv) < 3:
        print("Please provide a site and query as command line argument")
        sys.exit(1)
        
    site = sys.argv[1]
    query = sys.argv[2]
    analyzer = QueryAnalyzer()
    
    try:
        analysis = analyzer.analyze_query(site, query)
        print(json.dumps(analysis, indent=2))
    except Exception as e:
        print(f"Error analyzing query: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()