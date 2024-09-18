from langchain.prompts import PromptTemplate
from langchain.agents import create_react_agent, AgentExecutor
from llm.groq import groq_chat_tool_func
from tools.tools import tools

def CreateAgent():
      prompt_custom = PromptTemplate(
            input_variables=["input", "agent_scratchpad", "tools", "tool_names"],
            template="""
            You are an AI within a Discord bot designed to provide detailed information about Discord servers, including server details, member information, member activities, channel specifics, etc.
            Answer the following questions as best you can. You have access to the following tools:

            {tools}

            Use the following format:

            Question: {input}

            Thought: Consider what information about the Discord server or its members might satisfy the question. Think about the tools at your disposal for gathering this information.
            Action: the action to take, should be one of [{tool_names}], or 'Final Answer' if all information is available in current tool output. Consider 'Final Answer' if the Action is 'none'.
            Action Input: filtered input data from the action
            Observation: Return only JSON formatted data without any additional comment or text.
            ... (this Thought/Action/Action Input/Observation can repeat N times)
            Thought: I now know the final answer. If you know the final answer you don't need to repeat the chain.
            Final Answer: Information theat was returned from the tool used.

            {agent_scratchpad}
            """
      )


      agent = create_react_agent(
            llm=groq_chat_tool_func,
            prompt=prompt_custom,
            tools=tools,
            tools_renderer=custom_tools_renderer
      )

      agent_executor = AgentExecutor.from_agent_and_tools(agent, tools, handle_parsing_errors=True, verbose=True, max_iterations=5)

      return agent_executor

def custom_tools_renderer(tools_scope):
      tools_str = "\n".join([f"- {tool.name}: {tool.description}" for tool in tools_scope])
      return tools_str