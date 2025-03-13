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
import llm


NUM_RESULTS_TO_SEND = 15
EARLY_SEND_THRESHOLD = 70


milvus_client_prod = MilvusClient("./milvus_prod.db")
milvus_client_small = MilvusClient("./milvus_small.db")
milvus_client_large = MilvusClient("./milvus_large.db")


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
   client = llm.get_client("oai_sync")
   return client.embeddings.create(input = [text], model="text-embedding-3-small").data[0].embedding
    

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

class SE_OAI_Ranking(BaseModel):
    score: int
    description: str
  #  explanation: str
   
 #   pros: str
 #   cons: str

class SE_QueryAnalysis(BaseModel):
    is_related_to_previous_queries: bool
    is_related_to_previous_answers: bool
    decontextualized_query: str

class SE_IsRemember(BaseModel):
    is_dietary_restriction_statement: bool
    dietary_restriction: str


seriouseats_ranking_prompt = """Assign a score between 0 and 100 to the following recipe
based on how relevant it is to the user's question. 
Provide a short description of the itemrecipe that is relevant to the user's question, without mentioning the user's question.
The description should highlight aspects of the recipe the user is looking for. If the recipe is not for the dish that the user is looking for, specify, in the description, how this recipe might be useful in preparing what the user is trying to cook. 
The user's question is: {query}.
The item is: {description}.
"""

is_memory_request_prompt = """The user is interacting with the site seriouseats.com. Analyze the following statement from the user. 
     Is the user asking you to remember, something about their dietary restriction? For example, are they
     saying that they are vegetarian, or have some allergy? If so, what is the restriction?
     The user's statement is: {query}.
     """
 
query_analysis_prompt_template = """The user is asking a query on the site seriouseats.com. Analyze the query.
     Does answering this query require access to earlier queries or answers? If so, rewrite the query to decontextualize it so that it can be answered independently.
     If so, rewrite the query to decontextualize it so that it can 
     be answered independently.
     The user's query is: {query}. Previous query was: {previous_query}.
"""

async def ask_llm(prompt, model, response_format):
    client = llm.get_client("oai_async")
    completion = await client.beta.chat.completions.parse(
        model=model,
        messages=[
                {"role": "system", "content": "Analyze the user's query and answer the following questions about it: "},
                {"role": "user", "content": prompt},
            ],
            response_format=response_format,
        )
    return completion.choices[0].message.parsed

async def execute_task_set (task_set):
    tasks = []
    for task in task_set:
        prompt = task[0]
        model = task[1]
        response_format = task[2]
        tasks.append(asyncio.create_task(ask_llm(prompt, model, response_format)))
    results =  await asyncio.gather(*tasks)
    print(results)
    return results


def extract_json_str(text):
    return text.split("```json")[1].split("```")[0]

def make_ranking_prompt(site, query, item_type, json_str):
    return seriouseats_ranking_prompt.format(query=query, item_type=item_type, description=trim_json(json_str))

async def get_ranking(prompt, model):
    if (model.find("gpt") != -1):
        client = llm.get_client("oai_async")
        completion = await client.beta.chat.completions.parse(
            model=model,
            temperature=0.0,
            messages=[
                {"role": "system", "content": "Rank the answer based on how relevant it is to the user's question."},
                {"role": "user", "content": prompt},
            ],
            response_format=SE_OAI_Ranking,
        )
        ranking = completion.choices[0].message.parsed
        return ranking
    elif (model.find("gemini") != -1):
        client = llm.get_client("google")
        prompt = prompt + """   
                                List the answer in JSON format.
        Use this JSON schema: 
        Ranking: {score: int, description: str, explanation: str}
        Return: list[Ranking]"""
        result = client.generate_content(prompt)
        js_str = extract_json_str(result.candidates[0].content.parts[0].text)
        js = json.loads(js_str)
        r = SE_OAI_Ranking(score=js[0]["score"], description=js[0]["description"], explanation=js[0]["explanation"])
        return r
    else:
        raise ValueError(f"Invalid model: {model}")

async def rankOneAnswer(site, query, model, json_str, url, name, request_handler=None):
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
            "explanation": "", #ranking.explanation,
       #     "is_accompaniment" : ranking.is_accompaniment_dish,
        #    "is_similar_dish": ranking.is_similar_dish,
        #    "pros": ranking.pros,
        #    "cons": ranking.cons,
            "schema_object": json_str   
        }
    
    if (request_handler and ranking.score > EARLY_SEND_THRESHOLD):
        request_handler.wfile.write(("data: " + json.dumps(anstr) + "\n\n").encode("utf-8"))
        request_handler.wfile.flush()
        num_results_sent += 1
        return None
    else:
        return ansr

def prevReference(query):
    return 1

def send_poor_results_message(request_handler, filtered_results):
    mt = "intermediate_message"
    if (len(filtered_results) > 0):
        request_handler.wfile.write(("data: " + json.dumps({"message_type": mt, "num_results_sent": num_results_sent}) + "\n\n").encode("utf-8"))
    elif (num_results_sent == 0):
        request_handler.wfile.write(("data: " + json.dumps({"message_type": mt, "message": "I couldn't find any results that are relevant to your query."}) + "\n\n").encode("utf-8"))
    else:
        request_handler.wfile.write(("data: " + json.dumps({"message_type": mt, "num_results_sent": num_results_sent}) + "\n\n").encode("utf-8"))
    request_handler.wfile.flush()

def send_results(request_handler, results):
    global num_results_sent
    json_results = []
    for result in results:
        json_results.append({
            "url": result["url"],
            "name": result["name"],
            "score": result["ranking"].score,
            "description": result["ranking"].description,
            "explanation": "", #result["ranking"].explanation,
        #    "pros": result["ranking"].pros,
        #    "cons": result["ranking"].cons,
            "schema_object": result["schema_object"]
        })
    to_send = {"message_type": "result_batch", "results": json_results}
    request_handler.wfile.write(("data: " + json.dumps(to_send) + "\n\n").encode("utf-8"))
    request_handler.wfile.flush()
    num_results_sent += len(json_results)

async def get_ranked_answers(query, site, model, embedding_size, prev="", request_handler=None, item_to_remember=""):
    global num_results_sent
    print(f"query: {query}, model: {model}, site: {site}, embedding: {embedding_size}, prev: {prev}")
    num_results_sent = 0
    if (len(prev) > 3):
        task_set = [
            [query_analysis_prompt_template.format(query=query, previous_query=prev), "gpt-4o", SE_QueryAnalysis],
            [is_memory_request_prompt.format(query=query), "gpt-4o", SE_IsRemember]
        ]
        (query_analysis, is_memory_request) = await execute_task_set(task_set)

        if (is_memory_request.is_dietary_restriction_statement):
            item_to_remember = is_memory_request.dietary_restriction
            message = {"message_type": "remember", "item_to_remember": item_to_remember, "message": "I'll remember that"}
            request_handler.wfile.write(("data: " + json.dumps(message) + "\n\n").encode("utf-8"))
            request_handler.wfile.flush()
            print(f"I'll remember that {item_to_remember}")
    # Create tasks for all rankings
    
        if (query_analysis.is_related_to_previous_queries):
            query = query_analysis.decontextualized_query
            print(f"decontextualized query: '{query}' based on previous query: '{prev}'")
            if (model == "gpt-4o-mini"):
                model = "gpt-4o"
            
    top_embeddings = search_db(query, site)
    tasks = []
    for url, json_str, name in top_embeddings:
        task = asyncio.create_task(rankOneAnswer(site, query, model, json_str, url, name, request_handler))
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
        send_results(request_handler, good_results[:NUM_RESULTS_TO_SEND - num_results_sent + 1])
    else:
        send_results(request_handler, good_results)
        num_results_sent = num_results_sent + len(good_results)
    if (num_results_sent < 7):
        send_poor_results_message(request_handler, medium_results)
        send_results(request_handler, medium_results)
    print(f"num_results_sent: {num_results_sent}")

if __name__ == "__main__":
 #   init()
    query = sys.argv[1]
    ranked_answers = asyncio.run(get_ranked_answers(query, "imdb", 10))
    print(json.dumps(ranked_answers, indent=4))
