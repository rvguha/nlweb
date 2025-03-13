import mllm
import retriever
from trim import trim_json
from prompts import find_prompt, fill_prompt

class NoOpDecontextualizer:
    def __init__(self, handler):
        self.handler = handler

    async def do(self):
        self.handler.decontextualized_query = self.handler.query
        return
    
class PrevQueryDecontextualizer:

   # this is the default, if something in not found in the prompts file
    DECONTEXTUALIZE_QUERY_PROMPT = ["""This site has information about {self.item_type}
     Does answering this query require access to earlier queries? 
    If so, rewrite the query to decontextualize it so that it can be answered 
    without reference to earlier queries. If not, don't change the query.
  . The user's query is: {self.query}. Previous queries were: {self.prev_queries}.""",
                                    {"requires_decontextualization" : "True or False", 
                                     "decontextualized_query" : "The rewritten query"}]
    
    DECONTEXTUALIZE_QUERY_PROMPT_NAME = "PrevQueryDecontextualizer"

    def get_prompt(self):
        item_type = self.handler.item_type
        site = self.handler.site
        prompt_str, ans_struc = find_prompt(site, item_type, self.DECONTEXTUALIZE_QUERY_PROMPT_NAME)
        if prompt_str is None:
            return self.DECONTEXTUALIZE_QUERY_PROMPT
        else:
            return prompt_str, ans_struc
      
    def __init__(self, handler):
        self.handler = handler

    async def do(self):
        prompt_str, ans_struc = self.get_prompt()
        prompt = fill_prompt(prompt_str, self.handler)
        response = await mllm.get_structured_completion_async(prompt, ans_struc, "gpt-4o")
        self.handler.requires_decontextualization = response["requires_decontextualization"]
        if (self.handler.requires_decontextualization == "True"):
            self.handler.decontextualized_query = response["decontextualized_query"]
            message = {"message_type": "decontextualized_query", "query": self.handler.decontextualized_query}
            try:
                await self.handler.http_handler.write_stream(message)
                print(f"Decontextualized query: {self.handler.decontextualized_query}")
            except (BrokenPipeError, ConnectionResetError):
                print("Client disconnected during decontextualization")
                self.handler.is_connection_alive = False
                self.handler.decontextualized_query = self.handler.query
        else:
            self.handler.decontextualized_query = self.handler.query
        print(f"decontextualized_query: {self.handler.decontextualized_query}")
        return

class ContextUrlDecontextualizer(PrevQueryDecontextualizer):
    DECONTEXTUALIZE_QUERY_PROMPT = [
          """The use is asking the following question: '{self.handler.query}' in the context of 
          the an item with the following description: {context_description}. 
            Rewrite the query to decontextualize it so that it can be answered 
            without reference to earlier queries or to the item description.""",
                                 
                                    {"decontextualized_query" : "The rewritten query"}]
    
    DECONTEXTUALIZE_QUERY_PROMPT_NAME = "DecontextualizeContextPrompt"
     
    def __init__(self, handler):
        self.handler = handler
        self.context_url = handler.context_url
        self.retriever = self.retriever()

    def retriever(self):
        return retriever.MilvusItemRetriever(self.handler)  

    async def do(self):
        await self.retriever.do()
        item = self.retriever.handler.context_item
        self.context_description = trim_json(item["text"])
        self.handler.context_description = self.context_description
        super().do()
        

class FullDecontextualizer(ContextUrlDecontextualizer):
    DECONTEXTUALIZE_QUERY_PROMPT = [
         """The use is asking the following question: '{self.handler.query}' in the context of 
          the an item with the following description: {description_context}. 
          Previous queries from the user were: {self.handler.prev_queries}.
            Rewrite the query to decontextualize it so that it can be answered 
            without reference to earlier queries or to the item description.""",
                                    {"decontextualized_query" : "The rewritten query"}]
    
    DECONTEXTUALIZE_QUERY_PROMPT_NAME = "DecontextualizePrompt"

    def __init__(self, handler):
       super().__init__(handler)
   