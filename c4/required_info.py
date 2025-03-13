import mllm
import asyncio
from prompts import find_prompt, fill_prompt



class RequiredInfo:

    REQUIRED_INFO_PROMPT = ["""The user is querying the site {self.handler.site} for {self.handler.item_type}. This requires
                            the following information: {self.handler.required_info}. Do you have this information from this
                            query or the previous queries or the context or memory about the user? 
                            The user's query is: {self.handler.query}. The previous queries are: {self.handler.prev_queries}. 
                            The context is: {self.handler.context}. The memory is: {self.handler.memory}.
                            """,
                            {"required_info_found" : "True or False", "User_question": "Question to ask the user for the required information"}]
    
    REQUIRED_INFO_PROMPT_NAME = "RequiredInfoPrompt"

    def __init__(self, handler):
        self.handler = handler

    def get_required_info_prompt(self):
        site = self.handler.site
        item_type = self.handler.item_type
        prompt_str, ans_struc = find_prompt(site, item_type, self.REQUIRED_INFO_PROMPT_NAME)
        if prompt_str is None:
            return self.REQUIRED_INFO_PROMPT
        else:
            return prompt_str, ans_struc

    async def do(self):
        if (self.handler.required_info and len(self.handler.required_info) > 0):
            prompt_str, ans_struc = self.REQUIRED_INFO_PROMPT
            prompt = prompt_str.format(self=self)
            response = await mllm.get_structured_completion_async(prompt, ans_struc, "gpt-4o")
       #     print(f"response: {response}")
            self.handler.required_info_found = response["required_info_found"]
            self.handler.user_question = response["User_question"]
        else:
            self.handler.required_info_found = True
            self.handler.user_question = ""


if __name__ == "__main__":
    class MockHandler:
        def __init__(self, site, query, item_type, required_info, prev_queries, context, memory):
            self.site = site
            self.query = query
            self.item_type = item_type
            self.required_info = required_info
            self.prev_queries = prev_queries
            self.context = context
            self.memory = memory

    async def test_required_info():
        # Get inputs from user
        site = input("Enter site name (e.g. imdb, seriouseats): ")
        query = input("Enter query: ")
        item_type = input("Enter item type (e.g. Recipe, Movie): ")
        required_info = input("Enter required info (comma separated, or empty): ").split(",")
        prev_queries = input("Enter previous queries (comma separated, or empty): ").split(",")
        context = input("Enter context (or empty): ")
        memory = input("Enter memory about user (or empty): ")

        # Create mock handler
        handler = MockHandler(site, query, item_type, required_info, prev_queries, context, memory)
        
        # Create and test RequiredInfo instance
        required_info = RequiredInfo(handler)
        
        print("\nChecking required info...")
        await required_info.do()
        
        print(f"\nResults:")
        print(f"Required info found: {handler.required_info_found}")
        print(f"Question to ask user: {handler.user_question}")

    # Run the test
    asyncio.run(test_required_info())

