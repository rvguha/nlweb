import mllm
from prompts import find_prompt, fill_prompt

class AnalyzeQuery:
  
    DETERMINE_ITEM_TYPE_PROMPT = [
        """What is the kind of item the query is seeking with this query: {self.handler.query}? 
        Pick one of [Recipe, Restaurant, Movie, Paper, Outdoor Gear, Podcast]""", 
        {"item_type" : ""}]
    
    QUERY_TYPE_PROMPT = ["""The user is interacting with the site {self.handler.site}. Analyze the following query from the user. 
     Is the user asking for a list {self.handler.item_type} that match a certain description or are they asking for the details of a particular {self.handler.item_type}?
      If the user for the details of a particular {self.handler.item_type}, what is the title of the {self.handler.item_type} and what details are they asking for?
     The user's statement is: {self.handler.query}.""", 
     {"item_details_query" : "True or False", "item_title" : "The title of the {self.item_type}, if any", 
      "details_being_asked": "what details the user is asking for"}]
    
    QUERY_TYPE_PROMPT_NAME = "DetectQueryTypePrompt"
    DETERMINE_ITEM_TYPE_PROMPT_NAME = "DetectItemTypePrompt"

    def __init__(self, handler):
        self.handler = handler

    def get_query_type_prompt(self):
        item_type = self.handler.item_type
        site = self.handler.site
        prompt_str, ans_struc = find_prompt(site, item_type, self.QUERY_TYPE_PROMPT_NAME)
        if prompt_str is None:
            return self.QUERY_TYPE_PROMPT
        else:
            return prompt_str, ans_struc
    
    def get_determine_item_type_prompt(self):
        item_type = self.handler.item_type
        site = self.handler.site
        prompt_str, ans_struc = find_prompt(site, item_type, self.DETERMINE_ITEM_TYPE_PROMPT_NAME)
        if prompt_str is None:
            return self.DETERMINE_ITEM_TYPE_PROMPT
        else:
            return prompt_str, ans_struc
        
    async def do(self):
        item_type_prompt_str, item_type_ans_struc = self.get_determine_item_type_prompt()
        item_type_prompt = fill_prompt(item_type_prompt_str, self.handler)
        response = await mllm.get_structured_completion_async(item_type_prompt, item_type_ans_struc, "gpt-4o")
        self.handler.item_type = response["item_type"]
        query_type_prompt_str, query_type_ans_struc = self.get_query_type_prompt()
        query_type_prompt = fill_prompt(query_type_prompt_str, self.handler)
        response = await mllm.get_structured_completion_async(query_type_prompt, query_type_ans_struc, "gpt-4o")
        self.handler.item_details_query = response["item_details_query"]
        self.handler.item_title = response["item_title"]
        self.handler.details_being_asked = response["details_being_asked"]
        return
    

if __name__ == "__main__":
    class MockHandler:
        def __init__(self, site, query):
            self.site = site
            self.query = query

    async def test_analyze_query():
        # Get inputs from user
        site = input("Enter site name (e.g. imdb, seriouseats): ")
        query = input("Enter query: ")

        # Create mock handler
        handler = MockHandler(site, query)
        
        # Create and test AnalyzeQuery instance
        analyzer = AnalyzeQuery(handler)
        
        print("\nAnalyzing query...")
        await analyzer.do()
        
        print(f"\nResults:")
        print(f"Item Type: {handler.item_type}")
        print(f"Is Item Details Query: {handler.item_details_query}")
        print(f"Item Title: {handler.item_title}")
        print(f"Details Being Asked: {handler.details_being_asked}")

    # Run the test
    import asyncio
    asyncio.run(test_analyze_query())