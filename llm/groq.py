import os
from langchain_groq import ChatGroq

groq_api_key = os.environ['GROQ_API_KEY']

# this is our instance where we enable eve's personality
groq_chat_personality = ChatGroq(
    groq_api_key=groq_api_key,
    temperature=0.7,
    model_name="llama-3.1-8b-instant",
    model_kwargs={
        "top_p": 0.9,
        "seed": 424242
    },
    streaming=False
)

groq_chat_tool_func = ChatGroq(
      groq_api_key=groq_api_key,
      temperature=0,
      model_kwargs={
          "top_p": 0.85,
          "seed": 376425376425
      },
      model_name="llama3-groq-70b-8192-tool-use-preview",
      streaming=False,
      max_tokens=8192
)

groq_chat_question_helper = ChatGroq(
    groq_api_key=groq_api_key,
    temperature=0.4,
    model_name="llama3-70b-8192",
    model_kwargs={
        "top_p": 0.85,
        "seed": 69420
    },
    streaming=False
)