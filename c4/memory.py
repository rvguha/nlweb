import mllm
import retriever
import asyncio
import json
import utils
from trim import trim_json
from prompts import find_prompt, fill_prompt
from state import NLWebHandlerState



class Memory:

    MEMORY_PROMPT = ["""The user is querying the site {self.handler.site} for {self.handler.item_type}. Analyze the following statement from the user. 
    Is the user asking you to remember, that may be relevant to not just this query, but also future queries? 
    If so, what is the user asking us to remember?
    The user should be explicitly asking you to remember something for future queries, 
    not just expressing a requirement for the current query.
    The user's query is: {self.handler.query}.""", 
     {"is_memory_request" : "True or False", "memory_request" : "The memory request, if any"}]

    MEMORY_PROMPT_NAME = "DetectMemoryRequestPrompt"

    def get_prompt(self):
        item_type = self.handler.item_type
        site = self.handler.site
        prompt_str, ans_struc = find_prompt(site, item_type, self.MEMORY_PROMPT_NAME)

        if (prompt_str is None):
            prompt_str, ans_struc = self.MEMORY_PROMPT
        return prompt_str, ans_struc

    def __init__(self, handler):
        self.handler = handler

    async def do(self):
        prompt_str, ans_struc = self.get_prompt()
        prompt = fill_prompt(prompt_str, self.handler)
        response = await mllm.get_structured_completion_async(prompt, ans_struc, "gpt-4o")
        self.is_memory_request = response["is_memory_request"]
        self.memory_request = response["memory_request"]
        if (self.is_memory_request == "True"):
            print(f"writing memory request: {self.memory_request}")
            message = {"message_type": "remember", "item_to_remember": self.memory_request, "message": "I'll remember that"}
            await self.handler.http_handler.write_stream(message)
        self.handler.state.memory_items = NLWebHandlerState.DONE


if __name__ == "__main__":
    class MockHandler:
        def __init__(self, site, query, item_type):
            self.site = site
            self.query = query
            self.item_type = item_type
            
        async def write_stream(self, message):
            print(f"Would send message: {message}")


    async def test_memory():
        # Get inputs from user
        site = input("Enter site name (e.g. allrecipes.com): ")
        query = input("Enter query (e.g. Remember I'm vegetarian): ")
        item_type = input("Enter item type (e.g. Recipe): ")

        # Create mock handler
        handler = MockHandler(site, query, item_type)
        
        # Create and test Memory instance
        memory = Memory(handler)
        
        
        print("\nTesting memory analysis...")
        await memory.do()
        
        print(f"\nResults:")
        print(f"Is memory request: {memory.is_memory_request}")
        print(f"Memory request: {memory.memory_request}")

    # Run the test
    asyncio.run(test_memory())

