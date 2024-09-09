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

# discord setting up
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# keys and models
groq_api_key = os.environ['GROQ_API_KEY']
discord_eve_key = os.environ['DISCORD_EVE_KEY']
model_name = "llama3-8b-8192"
conversation_memory_length = 5
# system prompt
system_prompt = "You're a bot. Your name is Eve. You live inside a Discord server. Your traits are:  Girl that thinks as a  'cat girl', 'cute', 'loves summer', 'friendly', 'smart', 'tech savvy', 'witty', 'loves anime' and hates 'yapping' too much."
groq_chat = ChatGroq(
    groq_api_key=groq_api_key,
    model_name=model_name
)

def load_memory():
    return ConversationBufferWindowMemory(k=conversation_memory_length, memory_key="chat_history", return_messages=True)

def run():
    bot.run(discord_eve_key)

memory = load_memory()

@bot.command(name="AskEve")
async def ask(ctx, *, question):
    try:
        prompt = await prompt_template()
        conversation = LLMChain(
                    llm=groq_chat,
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

        await ctx.send(response)
    except Exception as e:
        print(e)
        await ctx.send(e)

async def prompt_template():
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
