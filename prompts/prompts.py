from langchain.prompts import PromptTemplate

prompt_category_graph = PromptTemplate(
    template="""<|begin_of_text|><|start_header_id|>system<|end_header_id|>
    You are a Input Categorizer Agent You are a master at understanding what the user wants when they write an question and are able to categorize it in a useful way

     <|eot_id|><|start_header_id|>user<|end_header_id|>
    Conduct a comprehensive analysis of the input provided and categorize into the following categories:
        server_information - used when someone is asking about for information about the server. \
        server_information - also used when someone ask about activities in the server. Listening to music, streaming, gaming etc \
        members_information - used when someone is asking about for information about the members or users of the server. Always make sure if you indentify as members_information also indentify as server_information.\
        members_information - also used when someone ask about activities about members or users of the server. Listening to music, streaming, gaming etc \
        channel_information_list - used when someone ask general information about channels without mentioning any specific channel name. \
        channel_information_list - Always make sure to identify server_information together with channel_information_list.  \
        channel_information_by_name - only use when someone passes a channel name on {initial_question} and if channel_information_list isn't identified. \
        channel_information_by_name - Always make sure to identify server_information together with channel_information_by_name. \
        channel_history_information_by_id - Only use when someone passes a channel name on {initial_question} and if channel_information_list isn't identified. \
        channel_history_information_by_id - also used when someone is asking about information on a specific channel name. Always make sure if you indentify as channel_information_by_name also indentifies as channel_history_information_by_id if channel_information_list isn't also identified. \

        final_response - used when someone greets you or ask something about yourself (AI) \

            Output N categories from the types ([{tools}]) \

    Return in JSON format exactly like the rules bellow: \
    exactly N categories where N is the number of applicable categories from the list [{tools}]. \
    exactly N categories_scope where N is the number of applicable data from our categories. \
    In case the {initial_question} mention any specific information about {tools}, create an object inside our categories_scope where the key is the tool in {tools} where the information is from and the value is the specific data input from {initial_question}. \
    In case one of the keys inside categories_scope are: members_information, channel_information_by_name only store the data itself. \
    In case one of the keys inside categories_scope are: server_information, channel_information_list you don't need to store anything. Leave empty. \n
    In case {initial_question} exactly mentions both channel by name and user name, you should store in the key channel_information_by_name where it become a list of object where the key for channel name is channel_name and value is the channel name itself and the key for the user name is user_name and the value is the user name itself. \

    USER QUESTION INPUT CONTENT:\n\n {initial_question} \n\n
    <|eot_id|>
    <|start_header_id|>assistant<|end_header_id|>
    """,
    input_variables=["initial_question", "tools"],
)