import discord
import requests
import os
from pathlib import Path
from dotenv import load_dotenv

import socket
socket.AF_INET = socket.AF_INET  # Force IPv4
# --- Configuration ---
# Explicitly point to your custom filename
env_path = Path(__file__).parent / "keys.env"
load_dotenv(dotenv_path=env_path)

# Load environment variables
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
ANYTHINGLLM_URL = os.getenv("ANYTHINGLLM_URL", "http://localhost:3001")
ANYTHINGLLM_API_KEY = os.getenv("ANYTHINGLLM_API_KEY")
WORKSPACE_SLUG = os.getenv("ANYTHINGLLM_WORKSPACE")

# Construct the API endpoint
if WORKSPACE_SLUG and ANYTHINGLLM_URL:
    API_ENDPOINT = f"{ANYTHINGLLM_URL}/api/v1/workspace/{WORKSPACE_SLUG}/chat"
else:
    API_ENDPOINT = None
    print("⚠️ Warning: AnythingLLM URL or Workspace Slug not found in environment.")

# Initialize Discord Client
intents = discord.Intents.default()
intents.message_content = True  # Required to read message content
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'✅ Logged in as {client.user}')
    if WORKSPACE_SLUG:
        print(f'🤖 Connected to AnythingLLM workspace: {WORKSPACE_SLUG}')

@client.event
async def on_message(message):
    # Ignore messages from the bot itself
    if message.author == client.user:
        return

    # Command: !ask <your question>
    if message.content.startswith("!ask"):
        user_query = message.content[len("!ask"):].strip()
        
        if not user_query:
            await message.channel.send("❌ Please provide a question. Usage: `!ask <your question>`")
            return

        # Indicate typing while waiting for AI
        async with message.channel.typing():
            try:
                if not API_ENDPOINT or not ANYTHINGLLM_API_KEY:
                    await message.channel.send("❌ **Error:** Bot configuration missing. Check console logs.")
                    return

                # Prepare API Request
                headers = {
                    "Authorization": f"Bearer {ANYTHINGLLM_API_KEY}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "message": user_query,
                    "mode": "chat" 
                }

                # Send request to AnythingLLM
                response = requests.post(API_ENDPOINT, headers=headers, json=payload, timeout=500)   
                
                if response.status_code == 200:
                    data = response.json()
                    ai_response = data.get("textResponse", "No response received.")
                    sources = data.get("sources", [])

                    # Format Output
                    final_output = f"{ai_response}"
                    
                    if sources:
                        # Limit sources to top 3 to avoid huge messages
                        source_list = "\n".join([f"• [{s['title']}]({s['url']})" if s.get('url') else f"• {s['title']}" for s in sources[:3]])
                        final_output += f"\n\n📚 *Sources:*\n{source_list}"

                    await message.channel.send(final_output)
                else:
                    await message.channel.send(f"❌ **Error:** Failed to contact AnythingLLM (Status: {response.status_code})")
                    print(f"API Error: {response.text}")

            except Exception as e:
                await message.channel.send(f"❌ **Exception:** {str(e)}")
                print(f"Python Exception: {e}")

# Start the Bot
if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("❌ Error: Missing DISCORD_TOKEN in keys.env file.")
        print("Please ensure your 'keys.env' file contains: DISCORD_TOKEN=your_actual_token")
    elif not ANYTHINGLLM_API_KEY:
        print("❌ Error: Missing ANYTHINGLLM_API_KEY in keys.env file.")
    else:
        print("🚀 Starting bot...")
        try:
            # FIXED: Use the variable from .env, NOT the hardcoded string
            client.run(DISCORD_TOKEN)
        except discord.errors.LoginFailure:
            print("❌ Login Failed: The token in keys.env is invalid or expired.")
            print("Please check your Discord Developer Portal and update keys.env.")
        except Exception as e:
            print(f"❌ An unexpected error occurred: {e}")
