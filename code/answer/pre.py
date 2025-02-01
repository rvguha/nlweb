from typing import List
import openai 
import numpy as np
import sys
from pydantic import BaseModel
import json
import asyncio
import answer


async_client = openai.AsyncOpenAI()
sync_client = openai.OpenAI()

prompt_template = """This site has information about {item_type}
     Is the following query asking for details about a single specific item or is it looking for items matching a certain description?
     Does answering this query require access to earlier queries? If so, rewrite the query to decontextualize it so that it can be answered independently.
     Does it require access to earlier answers? If so, rewrite the query to decontextualize it so that it can be answered independently. 
     The user's query is: {query}. Previous query was: {previous_query}. 
"""

class QueryAnalysis(BaseModel):
    is_specific_item: bool
    is_related_to_previous_queries: bool
    is_related_to_previous_answers: bool
    decontextualized_query: str

def analyze_query(item_type, query, previous_query):
    prompt = prompt_template.format(item_type=item_type, query=query, previous_query=previous_query)
    completion = sync_client.beta.chat.completions.parse(
        model="gpt-4o",
        messages=[
                {"role": "system", "content": "Analyze the user's query and answer the following questions about it: "},
                {"role": "user", "content": prompt},
            ],
            response_format=QueryAnalysis,
        )
    result = completion.choices[0].message.parsed
    print(result)

full_prompt_template = """This site has information about {item_type}
     Is the following query asking for details about a single specific item or is it looking for items matching a certain description?
     Does this query refer to previously mentioned {item_type} in the conversation? Is it a modification of a previous query?
     If so, rewrite the query to decontextualize it so that it can be answered independently. The user's query is: {query}. Previous query was: {previous_query}. Previous answer was: {previous_answer}
"""

def get_previous_answer_context(query):
    results = asyncio.run(answer.get_ranked_answers(query, 'imdb', 'gpt-4o-mini', 'small', 1))
    json_results = json.dumps(results)
    return json_results



def analyze_query_full(item_type, query, previous_query):
    previous_answer = get_previous_answer_context(previous_query)
    prompt = full_prompt_template.format(item_type=item_type, query=query, previous_query=previous_query, previous_answer=previous_answer)
    completion = sync_client.beta.chat.completions.parse(
        model="gpt-4o",
        messages=[
                {"role": "system", "content": "Analyze the user's query and answer the following questions about it: "},
                {"role": "user", "content": prompt},
            ],
            response_format=QueryAnalysis,
        )
    result = completion.choices[0].message.parsed
    print(result)
    print("\nQuery Analysis:")
    print(f"Is about specific item: {result.is_specific_item}")
    print(f"Requires previous queries: {result.is_related_to_previous_queries}")
    print(f"Requires previous answers: {result.is_related_to_previous_answers}")
    print(f"Decontextualized query: {result.decontextualized_query}")
    return result

def analyze_query(item_type, query, previous_query):
    prompt = prompt_template.format(item_type=item_type, query=query, previous_query=previous_query)
    completion = sync_client.beta.chat.completions.parse(
        model="gpt-4o",
        messages=[
                {"role": "system", "content": "Analyze the user's query and answer the following questions about it: "},
                {"role": "user", "content": prompt},
            ],
            response_format=QueryAnalysis,
        )
    result = completion.choices[0].message.parsed
    print(result)
    print("\nQuery Analysis:")
    print(f"Is about specific item: {result.is_specific_item}")
    print(f"Requires previous queries: {result.is_related_to_previous_queries}")
    print(f"Requires previous answers: {result.is_related_to_previous_answers}")
    print(f"Decontextualized query: {result.decontextualized_query}")

    return result

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Please provide a query as a command line argument")
        sys.exit(1)
        
    query = sys.argv[1]
    item_type = sys.argv[2]
    previous_query = sys.argv[3]
    analyze_query(item_type, query, previous_query)
 #   analyze_query_full(item_type, query, previous_query)

    