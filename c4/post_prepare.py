from time import sleep
import mllm
import retriever
import asyncio
import json
import utils
from trim import trim_json

class PostPrepare:
    def __init__(self, handler):
        self.handler = handler

    async def do(self):
        if (self.handler.is_connection_alive == False):
            self.handler.query_done = True
            return
        if (self.handler.required_info_found == False):
            await self.handler.http_handler.write_stream({"message_type": "ask_user", "question": self.handler.user_question})
            self.handler.query_done = True
        else:
            self.handler.query_done = False
        
        # if decontextualized query is different from the original query, 
        # then we need to retrieve items again
        if (self.handler.requires_decontextualization):
            print(f"Retrieving items again because decontextualized query ({self.handler.decontextualized_query}) is different from the original query ({self.handler.query})")
            items = await self.handler.retrieve_items(self.handler.decontextualized_query).do()
            self.handler.final_retrieved_items = items
        else:
            self.handler.final_retrieved_items = self.handler.retrieved_items
        
      
       
        
