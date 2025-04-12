from time import sleep
import mllm
import retriever
import asyncio
import json
import utils
from trim import trim_json
from state import NLWebHandlerState


class PostPrepare:
    """This class is used to check if the pre processing for the query (i.e., before retrieval 
       from vector db and subsequent ranking) is done."""
    
    def __init__(self, handler):
        self.handler = handler

    async def do(self):
        if (self.handler.is_connection_alive == False):
            self.handler.query_done = True
            return
       
        while (self.handler.state.analyze_query != NLWebHandlerState.DONE or
               self.handler.state.query_relevance != NLWebHandlerState.DONE or
               self.handler.state.required_info != NLWebHandlerState.DONE or
               self.handler.state.decontextualization != NLWebHandlerState.DONE or
               self.handler.state.memory_items != NLWebHandlerState.DONE):
            await asyncio.sleep(.05)
        print("Post prepare done")
        if (self.handler.is_connection_alive == False):
            self.handler.query_done = True
            return
        
        
      
       
        
