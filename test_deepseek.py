from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()
api_key = os.getenv("DEEPSEEK_API_KEY")

if not api_key or api_key == "your_deepseek_api_key_here":
    print("API Key not found or still a placeholder! Please update .env")
else:
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello, who are you?"},
            ],
            stream=False
        )
        print("Response:", response.choices[0].message.content)
    except Exception as e:
        print(f"Error: {e}")
