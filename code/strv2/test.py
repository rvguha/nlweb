import openai
import json
from typing import List, Optional
from datetime import datetime

# Define the JSON schema for structured output
RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {
            "type": "string",
            "description": "The title of the book"
        },
        "author": {
            "type": "string",
            "description": "The author of the book"
        },
        "publication_year": {
            "type": "integer",
            "description": "The year the book was published"
        },
        "genres": {
            "type": "array",
            "items": {
                "type": "string"
            },
            "description": "List of genres the book belongs to"
        },
        "rating": {
            "type": "number",
            "minimum": 0,
            "maximum": 5,
            "description": "Average rating out of 5 stars"
        },
        "is_available": {
            "type": "boolean",
            "description": "Whether the book is currently available"
        }
    },
    "required": ["title", "author", "publication_year", "genres", "rating", "is_available"]
}

def get_book_info(title: str) -> dict:
    """
    Get structured book information using OpenAI API.
    
    Args:
        title (str): The title of the book to get information about
        
    Returns:
        dict: Structured book information following the defined schema
    """
    client = openai.OpenAI()
    
    # Construct the system message with schema instructions
    system_message = f"""
    You are a helpful assistant that provides book information in a structured format.
    Your response must be valid JSON that follows this schema:
    {json.dumps(RESPONSE_SCHEMA, indent=2)}
    
    Provide only the JSON response, without any additional text or explanation.
    """
    
    # Construct the user message
    user_message = f"Provide information about the book '{title}' in the specified JSON format."
    
    # Make the API call
    response = client.chat.completions.create(
        model="gpt-4-turbo-preview",
        response_format={ "type": "json_object" },
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message}
        ],
        temperature=0.7,
    )
    
    # Parse the response
    try:
        book_info = json.loads(response.choices[0].message.content)
        return book_info
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse API response as JSON: {e}")

# Example usage
if __name__ == "__main__":
    try:
        book_info = get_book_info("The Great Gatsby")
        print(json.dumps(book_info, indent=2))
    except Exception as e:
        print(f"Error: {e}")