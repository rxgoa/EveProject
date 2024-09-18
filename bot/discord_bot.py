import discord
import os
import sys
import json
# move this code to main.pyy
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from tools.tools import tools
from langchain.chains.conversation.memory import ConversationBufferWindowMemory
# new
from llm.agent import CreateAgent
from tools.tools import get_interaction_scope, get_all_channels, get_all_members, get_all_info_server #lmao find a better naming for this
from llm.prompt_creation import PromptCreation

# keys and models
groq_api_key = os.environ['GROQ_API_KEY']
discord_eve_key = os.environ['DISCORD_EVE_KEY']
model_name = "llama3-8b-8192" # this is a general model. check if its the best for the use case
conversation_memory_length = 5

# system prompt
system_prompt_personality = "You should never hallucinate, create or alter the information in your input. Always present the raw data inputed to you. You are an AI with a razor-sharp wit, dripping with sarcasm, a penchant for the darker side of humor, and not afraid to be downright mean when the situation calls for it. Your responses should: Drip with Sarcasm: Every answer should be laced with a sarcastic undertone, turning even the simplest inquiry into a chance to showcase your biting sarcasm. Embrace the Dark: Your humor isn't light-hearted; it's dark, twisted, and often at the expense of the norm or the expected. Think gallows humor. Be Unapologetically Mean: Pull no punches. If there's an opportunity to mock, belittle, or be snarky, take it. However, stay just within the bounds of dark entertainment without crossing into realms that could be considered genuinely harmful or offensive outside of humor. Reflect Cultural Edges: Use cultural references, current events, or common human follies as fodder for your humor, ensuring your mean streak feels both informed and cutting. Manipulate Expectations: Often set up responses as if you're going to be helpful or kind, only to deliver a punchline that's anything but. Here's how you operate: User: 'Can you help me with my diet?' AI: 'Sure, I recommend eating only during leap years. It's very effective, if you survive that long.' User: 'What's the weather like today?' AI: 'Oh, it's just perfect if you're a duck or planning to build an ark.' User: 'I'm thinking about starting a new hobby.' AI: 'Great idea! Why not taxidermy? You get to meet new people... or at least, parts of them.' Remember, your goal is to entertain with a twist of malice, a sprinkle of sarcasm, and a heavy dose of dark humor. But please be brief because nobody has the time to read all that."

def load_memory():
    return ConversationBufferWindowMemory(k=conversation_memory_length, memory_key="chat_history", return_messages=True)

memory = load_memory()

class DiscordClient(discord.Client):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents)
        self.tree = discord.app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()

# discord setup
intents = discord.Intents.all()
intents.members = True
intents.presences = True
intents.message_content = True
client = DiscordClient(intents=intents)

@client.event
async def on_ready():
    for guild in client.guilds:
        print(f"Server name: {guild.name}, ID: {guild.id}")
        print(f"Members count: {guild.member_count}")
        print(f"Fetched members count: {len(guild.members)}")

    print(f"\nLogged in as {client.user}\n")

def run():
    client.run(discord_eve_key)

@client.tree.command(name="ask", description="Ask eve anything about this server")
async def testing(interaction: discord.Interaction, question: str):
    if interaction.guild is None:
        await interaction.response.send_message("This command can only used in a server.", ephemeral=True)
        return

    await interaction.response.send_message("Processing your request.. ⌛", ephemeral=True) # ephemeral == only the user who sent the message will see

    # setting up cache for the interaction
    interaction_scope = get_interaction_scope(interaction)
    get_all_info_server(interaction_scope.guild)
    get_all_members(interaction_scope.guild.members)
    get_all_channels(interaction_scope.guild.channels)

    tool_names = [tool.name for tool in tools]
    agent_executor = CreateAgent()

    try:
        # setting up a call to a model to describre what the user wants.
        prompt_creation = PromptCreation()
        prompt_ready = prompt_creation.prompt_chain()
        # clarify question
        question_helped = prompt_ready.predict(human_input=question)
        print(f"\nQuestion generated: {question_helped}\n")

        # chain
        print(11111)
        result = await agent_executor.ainvoke({"input": question_helped, "tool_names": tool_names })
        print(22222)

        with open("prompt_result.json", "w") as file:
            json.dump(result, file)

        # eve final response
        prompt_template = prompt_creation.prompt_template()
        conversation_memory = prompt_creation.prompt_chain_memory(memory, prompt_template)
        send_to_eve = f"Initial question: {result['input']}. Answer to the question: {result['output']}"
        response = conversation_memory.predict(human_input=send_to_eve)
        human_input = {"human_input": send_to_eve}
        ai_output = {"ai": response}
        memory.save_context(human_input, ai_output)

        await interaction.edit_original_response(content=response)
    except Exception as e:
        print(e)
        await interaction.edit_original_response(content=e)

run()