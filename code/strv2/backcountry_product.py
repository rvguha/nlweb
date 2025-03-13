import json
import asyncio
from baseHandler import BaseNLWebHandler
import mllm
from retriever import retrieve_item_with_url
from trim import trim_json

#http://localhost:8000/html/str_chat.html?query=similar+jackets+from+patagonia+with+hood&site=bc_product&context_url=https://www.backcountry.com/mountain-hardwear-firefall-2-jacket-womens

EARLY_SEND_THRESHOLD = 65

class BCProductHandler(BaseNLWebHandler):

    RANKING_PROMPT = ["""The user is interacting with the site {self.site} on the page for the product with the following description:
                      {description_context}.
    Assign a score between 0 and 100 to the product with the following description based on how relevant it is to the user's 
                      question, when asked in the context of the product page mentioned above.
    The user's question is: {self.decontextualized_query}.
    The description of the product is: {description}.""", 
    {"score" : "integer between 0 and 100", 
     "description" : "short description of the product",
     "explanation" : "explanation of the relevance of the product to the user's question"}]
    
    DECONTEXTUALIZE_QUERY_PROMPT = ["""The use is asking the following question: '{self.query}' in the context of the product with the following description: {description_context}. 
                                    Rewrite the query to decontextualize it so that it can be answered without reference to earlier queries or to the product description.""",
                                 
                                    {"decontextualized_query" : "The rewritten query"}]

    def __init__(self, site, query, prev_queries=[], model="gpt-4o-mini", http_handler=None, query_id=None, context_url=None):
        super().__init__(site, query, prev_queries, model, http_handler, query_id)
        self.context_url = context_url
        self.getDescriptionContext()
       # self.firstQueryResponse()

    def getDescriptionContext(self):
        item = retrieve_item_with_url(self.context_url)
        self.description_context = trim_json(item["text"])

    async def decontextualizeQuery(self):
        prompt_str, ans_struc = self.DECONTEXTUALIZE_QUERY_PROMPT
        prompt = prompt_str.format(self=self, description_context=self.description_context)
        response = await mllm.get_structured_completion_async(prompt, ans_struc, "gpt-4o")
        self.decontextualized_query = response["decontextualized_query"]
        if (self.decontextualized_query != self.query):
            message = {"message_type": "decontextualized_query", "query": self.decontextualized_query}
            await self.http_handler.write_stream(message)
            print(f"Decontextualized query: {self.decontextualized_query}")  


    async def rankItem (self, url, json_str, name, site):
        prompt_str, ans_struc = self.RANKING_PROMPT
        description = trim_json(json_str)
        description_context = self.description_context
        prompt = prompt_str.format(self=self, description=description, description_context=description_context)
        ranking = await mllm.get_structured_completion_async(prompt, ans_struc, self.model)
        # print(f"Ranking: {ranking}")
        ansr = {
            'url': url,
            'site': site,
            'name': name,
            'ranking': ranking,
            'schema_object': json_str,
            'sent': False
        }
        if (ranking["score"] > EARLY_SEND_THRESHOLD and self.streaming):
            await self.sendAnswers([ansr])
        self.rankedAnswers.append(ansr)
       


