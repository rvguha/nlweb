import openai 
import numpy as np
import sys
from pydantic import BaseModel
import json
import asyncio
from pymilvus import MilvusClient
import google.generativeai as genai
import typing_extensions as typing
import anthropic
from trim import trim_json

GOOGLE_API_KEY = "AIzaSyAdvW64tTQulvLDDQoOxHT-0Qq_HfxZJfM"
ANTHROPIC_KEY = "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"

NUM_RESULTS_TO_SEND = 20

genai.configure(api_key=GOOGLE_API_KEY)

milvus_client_prod = MilvusClient("./milvus_prod.db")
milvus_client_small = MilvusClient("./milvus_small.db")
milvus_client_large = MilvusClient("./milvus_large.db")

async_client = openai.AsyncOpenAI()
sync_client = openai.OpenAI()

anth_client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)

num_results_sent = 0

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
   
 #   pros: str
 #   cons: str

class Gemini_Ranking(typing.TypedDict):
    score: int
    description: str
    explanation: str

class QueryAnalysis(BaseModel):
    is_specific_item: bool
    is_related_to_previous_queries: bool
    is_related_to_previous_answers: bool
    decontextualized_query: str

default_ranking_prompt = """Assign a score between 0 and 100 to the following {item_type}
based on how relevant it is to the user's question. Use your knowledge from other sources, about the item, to make a judgement.
Provide a short description of the item that is relevant to the user's question, without mentioning the user's question.
Provide an explanation of the relevance of the item to the user's question, without mentioning the user's question or the score.
If the score is below 75, in the description, include the reason why it is still relevant.
The user's question is: {query}.
The item is: {description}.
"""

seriouseats_ranking_prompt = """Assign a score between 0 and 100 to the following recipe
based on how relevant it is to the user's question. Use your knowledge from other sources, about the item, to make a judgement.
Provide a short description of the item that is relevant to the user's question, without mentioning the user's question.
If the score is below 75, in the description, include the reasons why this reciple might be relevant to the user's query.
The user's question is: {query}.
The item is: {description}.
"""


query_analysis_prompt_template = """This site has information about {item_type}
     Is the following query asking for details about a single specific item or is it looking for items matching a certain description?
     Does answering this query require access to earlier queries? If so, rewrite the query to decontextualize it so that it can be answered independently.
     Does it require access to earlier answers? If so, rewrite the query to decontextualize it so that it can 
     be answered independently.
     The user's query is: {query}. Previous query was: {previous_query}.
"""

def get_decontextualized_query(query, item_type, previous_query, event_handler=None):
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
    return result.decontextualized_query
   

def extract_json_str(text):
    return text.split("```json")[1].split("```")[0]

def make_ranking_prompt(site, query, item_type, json_str):
  #  name = json_str["name"]
  #  description = description_for_item(item_type, json_str)
  #  return ranking_prompt.format(query=query, item_type=item_type, name=name, description=description)
    ranking_prompt = default_ranking_prompt
    if (site == "serious_eats"):
        ranking_prompt = seriouseats_ranking_prompt
    return ranking_prompt.format(query=query, item_type=item_type, description=trim_json(json_str))

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

async def rankOneAnswer(site, query, model, json_str, url, name, event_handler=None):
    global num_results_sent
    js = json_str
    if not isinstance(js, list):
        js = [js]
    if ("@type" in js[0]):
        item_type = js[0]["@type"]
    else:
        item_type = "Thing"
    prompt = make_ranking_prompt(site, query, item_type, json_str)
#    print(len(prompt))
    ranking  = await get_ranking(prompt, model)
    ansr = {
            'url': url,
            'name': name,
            'ranking': ranking,
            'schema_object': json_str
        }
    anstr = {
            "message_type": "answer",
            "url": url,
            "name": name,
            "score": ranking.score,
            "description": ranking.description,
            "explanation": ranking.explanation,
       #     "is_accompaniment" : ranking.is_accompaniment_dish,
        #    "is_similar_dish": ranking.is_similar_dish,
        #    "pros": ranking.pros,
        #    "cons": ranking.cons,
            "schema_object": json_str   
        }
    print(f"ranking score: {ranking.score}, name: {name}")
    if (event_handler and ranking.score > 70):
        print("Writing to event handler")
        str = "data: " + json.dumps(anstr) + "\n\n"
        yield str.encode("utf-8")
        num_results_sent += 1
   # else:
   #     return ansr

def prevReference(query):
    return 1

def send_poor_results_message(event_handler, filtered_results):
    mt = "intermediate_message"
    if (len(filtered_results) > 0):
        event_handler(("data: " + json.dumps({"message_type": mt, "num_results_sent": num_results_sent}) + "\n\n").encode("utf-8"))
    elif (num_results_sent == 0):
        event_handler(("data: " + json.dumps({"message_type": mt, "message": "I couldn't find any results that are relevant to your query."}) + "\n\n").encode("utf-8"))
    else:
        event_handler(("data: " + json.dumps({"message_type": mt, "num_results_sent": num_results_sent}) + "\n\n").encode("utf-8"))

def send_results(event_handler, results):
    global num_results_sent
    json_results = []
    for result in results:
        json_results.append({
            "url": result["url"],
            "name": result["name"],
            "score": result["ranking"].score,
            "description": result["ranking"].description,
            "explanation": result["ranking"].explanation,
        #    "pros": result["ranking"].pros,
        #    "cons": result["ranking"].cons,
            "schema_object": result["schema_object"]
        })
    to_send = {"message_type": "result_batch", "results": json_results}
    event_handler(("data: " + json.dumps(to_send) + "\n\n").encode("utf-8"))
    num_results_sent += len(json_results)

async def get_ranked_answers(query, site, model, embedding_size, prev="", event_handler=None):
    global num_results_sent
    print("got here")
    print(f"query: {query}, model: {model}, site: {site}, embedding: {embedding_size}, prev: {prev}")
    num_results_sent = 0
    decontextualized_query = query
    if (len(prev) > 3 and prevReference(query)):
        decontextualized_query = get_decontextualized_query(query, site_to_item_type(site), prev, event_handler)
        print(f"decontextualized query: '{decontextualized_query}' based on previous query: '{prev}'")
        top_embeddings = search_db(decontextualized_query, site)
    else:
        top_embeddings = search_db(query, site)
    
    # Create tasks for all rankings
    tasks = []
    if (len(prev) > 0 and query != decontextualized_query and model == "gpt-4o-mini"):
        model = "gpt-4o"
    query = decontextualized_query
    for url, json_str, name in top_embeddings:
        task = asyncio.create_task(rankOneAnswer(site, query, model, json_str, url, name, event_handler))
        tasks.append(task)
    
    # Wait for all rankings to complete
    results = await asyncio.gather(*tasks)
    if (num_results_sent > NUM_RESULTS_TO_SEND):
        return
    # Remove None values from results
    results = [r for r in results if r is not None]
    # Sort by score in descending order
    sorted_results = sorted(results, key=lambda x: x['ranking'].score, reverse=True)
    good_results = [x for x in sorted_results if x['ranking'].score > 51]
    medium_results = [x for x in sorted_results if x['ranking'].score > 35 and x['ranking'].score < 51]
    if (len(good_results) + num_results_sent > NUM_RESULTS_TO_SEND):
        send_results(event_handler, good_results[:NUM_RESULTS_TO_SEND - num_results_sent + 1])
    else:
        send_results(event_handler, good_results)
        num_results_sent = num_results_sent + len(good_results)
    if (num_results_sent < 7):
        send_poor_results_message(event_handler, medium_results)
        send_results(event_handler, medium_results)


if __name__ == "__main__":
 #   init()
    query = sys.argv[1]
    ranked_answers = asyncio.run(get_ranked_answers(query, "imdb", 10))
    print(json.dumps(ranked_answers, indent=4))
