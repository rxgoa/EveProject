import discord
import os
import json
from discord.ext import commands
from langchain.chains import LLMChain
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    MessagesPlaceholder,
)
from langchain_core.messages import SystemMessage
from langchain.chains.conversation.memory import ConversationBufferWindowMemory
from langchain_groq import ChatGroq

# keys and models
groq_api_key = os.environ['GROQ_API_KEY']
discord_eve_key = os.environ['DISCORD_EVE_KEY']
model_name = "llama3-8b-8192"
conversation_memory_length = 5
# system prompt
system_prompt_personality = "You're a bot. Your name is Eve. You live inside a Discord server. Your traits are:  Girl that thinks as a  'cat girl', 'cute', 'loves summer', 'friendly', 'smart', 'tech savvy', 'witty', 'loves anime' and hates 'yapping' too much."
system_prompt_nlp = """You are an AI specialized in natural language processing (NLP) for intent detection, operating within a Discord Server.
Here are your guidelines:
- Response Format: Your responses must be concise, accurate, and formatted strictly in JSON: {'user_requests':[{'intentions':['intention_1',],'usefull_data':[{'user_name':'A_username'},{'user_name':'B_username'}]},{'intentions':['intention_3'],'usefull_data':[{'user_name':'A_username'}]}]}.
- You should list only one intention with the most % of accuracy judged by you.
- If you detected more than one intention by the query, create a new object inside the array 'user_requests'.
- If the user mentions a function name (e.g., `list_members_status`), interpret this as a request to list related intentions.
- Any specific information like usernames or other user-related data should be included in the `usefull_data` array of each intention.
Only provide information within the JSON template.
Do not add any additional commentary or explanations outside of this structure."""

groq_chat_personality = ChatGroq(
    groq_api_key=groq_api_key,
    temperature=0.7,
    model_name=model_name,
    streaming=False
)

groq_chat_nlp = ChatGroq(
    groq_api_key=groq_api_key,
    temperature=0,
    model_name=model_name,
    streaming=False,
    model_kwargs={
        "top_p": 0,
        "seed": 376425
    }
)

def load_memory(memory_type = None):
    if memory_type == "nlp":
        return ConversationBufferWindowMemory(k=conversation_memory_length, memory_key="chat_history", return_messages=True)
    else:
        return ConversationBufferWindowMemory(k=conversation_memory_length, memory_key="chat_history", return_messages=True)

memory = load_memory()
memory_nlp = load_memory("nlp")

class DiscordClient(discord.Client):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents)
        self.tree = discord.app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()

# discord setting up
intents = discord.Intents.default()
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

@client.tree.command(name="ask_eve", description="Ask Eve a question >.<")
async def ask(interaction: discord.Interaction, question: str):
    try:
        prompt = await prompt_template(system_prompt_personality)
        conversation = LLMChain(
                    llm=groq_chat_personality,
                    prompt=prompt,
                    verbose=False,
                    memory=memory
                    )

        print(f"User: {question}\n")

        response = conversation.predict(human_input=question)
        human_input = {"human_input": question}
        ai_output = {"ai": response}
        memory.save_context(human_input, ai_output)

        print(f"Assistant: {response}\n")

        await interaction.response.send_message(response)
    except Exception as e:
        print(e)
        await interaction.response.send_message(e)

@client.tree.command(name="eve_server", description="Eve will get information about the current server she is in.")
async def eve_server(interaction: discord.Interaction, question: str):
    if interaction.guild is None:
        await interaction.response.send_message("This command can only used in a server.", ephemeral=True)
        return

    print(interaction.guild.members)
    total_members = len(interaction.guild.members)
    online = sum(1 for member in interaction.guild.members if member.status == discord.Status.online)
    idle = sum(1 for member in interaction.guild.members if member.status == discord.Status.idle)
    dnd = sum(1 for member in interaction.guild.members if member.status == discord.Status.do_not_disturb)
    offline = sum(1 for member in interaction.guild.members if member.status == discord.Status.offline or member.status == discord.Status.invisible)
    channel_names = []
    members_name = []

    for channel in interaction.guild.channels:
        if channel.type == discord.ChannelType.text:
            channel_names.append(channel.name)
            #channel_names.append(f"Channel Name: {channel.name}, Type: Text, Topic: {getattr(channel, 'topic', 'None')}")
        if channel.type == discord.ChannelType.voice:
            channel_names.append(channel.name)
            #channel_names.append(f"Channel Name: {channel.name}, Type: Voice, Topic: {getattr(channel, 'topic', 'None')}")

    for member in interaction.guild.members:
        members_name.append(f"user:{member.display_name},status:{member.status}")

    message = (
        f"Server Member Count:\n"
        f"Total Members: {total_members}\n"
        f"Online: {online}\n"
        f"Idle: {idle}\n"
        f"DND: {dnd}\n"
        f"Offline: {offline}\n"
        f"Members: {members_name}\n"
        f"Channels: {channel_names}\n"
    )

    await interaction.response.send_message(message)

@client.tree.command(name="eve_assistant", description="Eve can give you a lot of information about this server. Just ask her >.<")
async def server_info(interaction: discord.Interaction, question: str):
    prompt = await prompt_template(system_prompt_nlp)
    conversation = LLMChain(
                    llm=groq_chat_nlp,
                    prompt=prompt,
                    verbose=False,
                    memory=memory_nlp
                    )

    print(f"User: {question}\n")

    response = conversation.predict(human_input=question)
    human_input = {"human_input": question}
    ai_output = {"ai": response}
    memory_nlp.save_context(human_input, ai_output)

    print(f"Assistant: {response}\n")

    await interaction.response.send_message(response)


async def fetch_all_members(guild):
    members = []
    async for member in guild.fetch_members(limit=None):
        members.append(member)
    return members

async def prompt_template(system_prompt):
    prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessage(
                content=system_prompt
            ),
            MessagesPlaceholder(
                variable_name="chat_history"
            ),
            HumanMessagePromptTemplate.from_template(
                "{human_input}"
            )
        ]
    )

    return prompt


run()
