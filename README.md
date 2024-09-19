# MVP - Discord bot
This is a very MVP discord bot with a few features. This is very much a project for me to study the tech.

# How to run
You will need:
- Discord API Key
- Groq API Key

then you'll need to create a venv, install deps and run:
```
python3 -m venv env
source env/bin/activate
pip3 install -r requirements.txt
python3 main.py
```
![](/images/eve_hello.jpeg)

# LLM Wrapper (Groq+Langchain+llama3)
This is a simple Discord bot using `Langchain`(and it's memory function) for keeping track of conversations, `Groq` API integration for access to our models `llama3` and also `groq-fine-tunned-llama3`.

# Langchain
The memory retreivel for this project is simple and local (past 5 chats). Basically this function is very simple right now where, for example, if you ask Eve what the user is listening to and then you asked again (given the user changed the song), Eve will comment on that. She also can check the list of members of the server, channels and messages.

*First Song*
![](/images/eve_memory.png)

*Second Song*
![](/images/eve_memory_remember.png)

Notice how she knows about the last song and comments on it. She is salty 😜

# system prompts
This project have 3 types of prompts (in a way):
1. A simple prompt where ask the model to understand what the user want, so that we can sent this new "input" to our Tool calling model.
2. The most "complex" prompt of the project. This prompt basically will try to: understand what the user want, think about it, call a tool and then, if necessary, call another tool with it's input. Basically using the chain idea of langchain so that we can have different tools for each type of function. Right now we only have tools for: Server Info, Search Channels by name and by id and also for getting members of the server.
3. This prompt is the final result you see when using. Basically we send the data(the information that you wanted) and apply a prompt of personality from `Eve`.

