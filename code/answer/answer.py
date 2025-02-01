import openai 
import numpy as np
import sys
from pydantic import BaseModel
import json
import asyncio
from pymilvus import MilvusClient
import google.generativeai as genai
import typing_extensions as typing


GOOGLE_API_KEY = "AIzaSyAdvW64tTQulvLDDQoOxHT-0Qq_HfxZJfM"

genai.configure(api_key=GOOGLE_API_KEY)

milvus_client_prod = MilvusClient("./milvus_prod.db")
milvus_client_small = MilvusClient("./milvus_small.db")
milvus_client_large = MilvusClient("./milvus_large.db")
async_client = openai.AsyncOpenAI()
sync_client = openai.OpenAI()


def site_to_item_type(site):
    if site == "imdb":
        return "Movie"
    elif site == "seriouseats":
        return "Recipe"
    elif site == "npr podcasts":
        return "Thing"
    elif site == "neurips":
        return "Paper"
    elif site == "backcountry":
        return "Outdoor Gear"
    else:
        return "Items"

def get_embedding(text):
   text = text.replace("\n", " ")
   return sync_client.embeddings.create(input = [text], model="text-embedding-3-small").data[0].embedding
    

def search_db(query, site):
#    print(f"query: {query}, site: {site}")
    embedding = get_embedding(query)
    client = milvus_client_prod 
    if (site == "prod"):
        client = milvus_client_prod
    res = client.search(
        collection_name="prod_collection",
        data=[embedding],
        filter=f"site == '{site}'",
        limit=50,
   #     expr=f"score > 0.3",
        output_fields=["url", "text", "name", "site"],
    )

    retval = []
    for item in res[0]:
        ent = item["entity"]
        retval.append([ent["url"], ent["text"], ent["name"]])
    print(len(retval))
    return retval

class OAI_Ranking(BaseModel):
    score: int
    description: str
    explanation: str

class Gemini_Ranking(typing.TypedDict):
    score: int
    description: str
    explanation: str

class QueryAnalysis(BaseModel):
    is_specific_item: bool
    is_related_to_previous_queries: bool
    is_related_to_previous_answers: bool
    decontextualized_query: str

ranking_prompt = """The user has asked the following question: {query}. 
Assign a score between 0 and 100 to a {item_type} with the description {description} 
based on how relevant it is to the user's question. Use your knowledge from other sources, about the item, to make a judgement.
Provide a short description of the item that is relevant to the user's question, without mentioning the user's question.
Also provide a short explanation for the score without mentioning the score."""

query_analysis_prompt_template = """This site has information about {item_type}
     Is the following query asking for details about a single specific item or is it looking for items matching a certain description?
     Does answering this query require access to earlier queries? If so, rewrite the query to decontextualize it so that it can be answered independently.
     Does it require access to earlier answers? If so, rewrite the query to decontextualize it so that it can be answered independently.
     The user's query is: {query}. Previous query was: {previous_query}. 
"""

def get_decontextualized_query(query, item_type, previous_query):
    prompt = query_analysis_prompt_template.format(item_type=item_type, query=query, previous_query=previous_query)
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
    return result.decontextualized_query

def description_for_item(item_type, js):
    if (not "description" in js):
        return json.dumps(js)
    description = js["description"]
    if item_type == "Movie" or item_type == "TVSeries" or item_type == "TVSeason" or item_type == "TVEpisode":
        return js["description"]
    elif item_type == "Product" or item_type == "ProductGroup":
        return js["description"]
    elif item_type == "Recipe":
        return js["description"]
    else:
        return js["description"]

def extract_json_str(text):
    return text.split("```json")[1].split("```")[0]

def make_ranking_prompt(query, item_type, json_str):
  #  name = json_str["name"]
  #  description = description_for_item(item_type, json_str)
  #  return ranking_prompt.format(query=query, item_type=item_type, name=name, description=description)
   return ranking_prompt.format(query=query, item_type=item_type, description=json_str)

async def get_ranking(prompt, model):
    if (model.find("gpt") != -1):
        completion = await async_client.beta.chat.completions.parse(
            model=model,
            messages=[
                {"role": "system", "content": "Rank the answer based on how relevant it is to the user's question."},
                {"role": "user", "content": prompt},
            ],
            response_format=OAI_Ranking,
        )
        ranking = completion.choices[0].message.parsed
        return ranking
    elif (model.find("gemini") != -1):
        model = genai.GenerativeModel(model)
        prompt = prompt + """   
                                List the answer in JSON format.
        Use this JSON schema: 
        Ranking: {score: int, description: str, explanation: str}
        Return: list[Ranking]"""
        result = model.generate_content(prompt)
        js_str = extract_json_str(result.candidates[0].content.parts[0].text)
        js = json.loads(js_str)
        r = OAI_Ranking(score=js[0]["score"], description=js[0]["description"], explanation=js[0]["explanation"])
        return r
    else:
        raise ValueError(f"Invalid model: {model}")

async def rankOneAnswer(query, model, json_str, url, name):
    js = json_str
    if not isinstance(js, list):
        js = [js]
    if ("@type" in js[0]):
        item_type = js[0]["@type"]
    else:
        item_type = "Thing"
    prompt = make_ranking_prompt(query, item_type, json_str)
#    print(len(prompt))
    ranking  = await get_ranking(prompt, model)
    return {
            'url': url,
            'name': name,
            'ranking': ranking,
            'schema_object': json_str
        }

def prevReference(query):
    return 1

async def get_ranked_answers(query, site, model, embedding_size, prev="", num=10):
    print(f"query: {query}, model: {model}, site: {site}, embedding: {embedding_size}, prev: {prev}")
    decontextualized_query = query
    if (len(prev) > 0 and prevReference(query)):
        decontextualized_query = get_decontextualized_query(query, site_to_item_type(site), prev)
        print(f"decontextualized query: {decontextualized_query}")
        top_embeddings = search_db(decontextualized_query, site)
    else:
        top_embeddings = search_db(query, site)
    
    # Create tasks for all rankings
    tasks = []
    if (len(prev) > 0 and query != decontextualized_query and model == "gpt-4o-mini"):
        model = "gpt-4o"
    query = decontextualized_query
    for url, json_str, name in top_embeddings:
        task = asyncio.create_task(rankOneAnswer(query, model, json_str, url, name))
        tasks.append(task)
    
    # Wait for all rankings to complete
    results = await asyncio.gather(*tasks)
   
    # Sort by score in descending order
    sorted_results = sorted(results, key=lambda x: x['ranking'].score, reverse=True)
    filtered_results = [x for x in sorted_results if x['ranking'].score > 50]   
    if (len(filtered_results) < 2):
        filtered_results = sorted_results[:5]   
    # Convert to JSON-serializable format
    json_results = []
    for result in filtered_results:
        json_results.append({
            "url": result["url"],
            "name": result["name"],
            "score": result["ranking"].score,
            "description": result["ranking"].description,
            "explanation": result["ranking"].explanation,
            "schema_object": result["schema_object"]
        })
    
    return json_results



if __name__ == "__main__":
 #   init()
    query = sys.argv[1]
    ranked_answers = asyncio.run(get_ranked_answers(query, "imdb", 10))
    print(json.dumps(ranked_answers, indent=4))
