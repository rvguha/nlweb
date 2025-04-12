import mllm
import asyncio
from prompts import find_prompt, fill_prompt
from state import NLWebHandlerState


class RequiredInfo:
    """For some sites, we will need to make sure that we have enough information, either from the user
       or context, before we process the query. This class is used to check if we have the required information.
       Whether the information is required or not is determined by whether we have a prompt for it"""


    REQUIRED_INFO_PROMPT_NAME = "RequiredInfoPrompt"

    def __init__(self, handler):
        self.handler = handler

    def get_required_info_prompt(self):
        site = self.handler.site
        item_type = self.handler.item_type
        prompt_str, ans_struc = find_prompt(site, item_type, self.REQUIRED_INFO_PROMPT_NAME)
        if prompt_str:
            return prompt_str, ans_struc
        else:
            return None, None

    async def do(self):
        prompt_str, ans_struc = self.get_required_info_prompt()
        print(f"prompt_str: {prompt_str}")
        if prompt_str:
            prompt = fill_prompt(prompt_str, self.handler)
            response = await mllm.get_structured_completion_async(prompt, ans_struc, "gpt-4o")
            print(f"response: {response}")
            self.handler.required_info_found = response["required_info_found"] == "True"
            if (not self.handler.required_info_found):
                await self.handler.http_handler.write_stream({"message_type": "ask_user", "message": response["user_question"]})
                self.handler.query_done = True
        else:
            self.handler.required_info_found = True
            self.handler.user_question = ""
        self.handler.state.required_info = NLWebHandlerState.DONE

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

