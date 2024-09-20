
import discord
import json
from discord import app_commands
from discord.ext import commands
from langchain.chains.conversation.memory import ConversationBufferWindowMemory
from tools.graph import GraphTool
from llm.prompt_creation import PromptCreation

class DiscordCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.conversation_memory_length = 5
        self.memory = self.load_memory()

    # Registering in log that our cog was loaded
    async def cog_load(self):
        print(f"{self.__class__.__name__} loaded!")

    @app_commands.command(name="ask", description="Ask Eve anything about this server")
    async def ask(self, interaction: discord.Interaction, question: str):
        if interaction.guild is None:
            await interaction.response.send_message("This command can only used in a server.", ephemeral=True)
            return

        await interaction.response.send_message("Processing your request.. ⌛", ephemeral=True) # ephemeral == only the user who sent the message will see

        # chain
        graph = GraphTool()

        # setting up cache for the interaction
        interaction_scope = graph.get_interaction_scope(interaction)
        graph.get_all_info_server(interaction_scope.guild)
        graph.get_all_members(interaction_scope.guild.members)
        graph.get_all_channels(interaction_scope.guild.channels)

        #tool_names = [tool.name for tool in tools]
        #agent_executor = CreateAgent()
        inputs = {
            "initial_question": question,
            "tools": ['server_information', 'members_information', 'channel_information_by_name', 'channel_history_information_by_id', 'channel_information_list'],
            "question_categories": [],
            "scope": {},
            "interaction": interaction,
            "categories_to_process": [],
            "num_steps": 0
        }
        try:
            # setting up a call to a model to describre what the user wants.
            prompt_creation = PromptCreation()
            prompt_ready = prompt_creation.prompt_chain()
            # # clarify question
            question_helped = prompt_ready.predict(human_input=question)
            print(f"\nQuestion generated: {question_helped}\n")


            inputs["initial_question"] = question_helped
            output = await graph.ainvoke(inputs)

            # eve final response
            prompt_template = prompt_creation.prompt_template()
            conversation_memory = prompt_creation.prompt_chain_memory(self.memory, prompt_template)
            send_to_eve = f"Initial question: {question_helped}. Answer to the question in JSON format: {json.dumps(output['scope'], indent=2)}"
            response = conversation_memory.predict(human_input=send_to_eve)
            human_input = {"human_input": send_to_eve}
            ai_output = {"ai": response}
            with open("eve_result.json", "w") as file:
                json.dump(response, file)
            self.memory.save_context(human_input, ai_output)

            await interaction.edit_original_response(content=response)
        except Exception as e:
            print(e)
            await interaction.edit_original_response(content=e)

    def load_memory(self):
        return ConversationBufferWindowMemory(k=self.conversation_memory_length, memory_key="chat_history", return_messages=True)

# this setup is automatically call when we .load_extensions in your bot.discord code
# this is a discord.py thing
async def setup(bot):
    await bot.add_cog(DiscordCommands(bot=bot))