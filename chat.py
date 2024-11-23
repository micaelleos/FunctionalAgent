
import streamlit as st
import os
import time
from langchain.memory import ConversationBufferMemory
from langchain.agents import AgentExecutor
from langchain.agents.format_scratchpad import format_to_openai_functions
from langchain.agents.output_parsers import OpenAIFunctionsAgentOutputParser
from langchain.tools.render import format_tool_to_openai_function
from langchain.prompts import ChatPromptTemplate
from langchain.chat_models import ChatOpenAI
from langchain.prompts import MessagesPlaceholder
from langchain.schema.runnable import RunnablePassthrough
from tools_jira import tools
from prompt import *

st.html(
    '''
        <style>
            div[aria-label="dialog"]>button[aria-label="Close"] {
                display: none;
            }
            .st-emotion-cache-ocqkz7{
                position: sticky;
                top: 3.75rem; 
                // width: 50%; 
                z-index:999991; 
                background-color: white;}
        </style>
    '''
)


@st.dialog("Configuração de Login")
def config():
    st.write(f"Entre com as suas credenciais do Jira:")
    url = st.text_input("Jira URL")
    email = st.text_input("Email")
    api_key = st.text_input("API Key")

    col11, col22 = st.columns([0.5,0.5])
    with col11:
        if st.button("Submit",use_container_width=True):
            st.session_state.credenciais = {"url": url, "email": email,"api_key": api_key}
            st.rerun()
    with col22:
        if st.button("Close",use_container_width=True):
            st.rerun()


prompt = ChatPromptTemplate.from_messages([
    ("system", f"{prompt_2}"),
    MessagesPlaceholder(variable_name="chat_history"),
    ("user", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad")
])

OPENAI_API_KEY = os.environ['OPEN_API_KEY']

model = ChatOpenAI(openai_api_key=OPENAI_API_KEY,temperature=0.5)

model_jira_with_tool_test = model.bind(functions=[format_tool_to_openai_function(t) for t in tools])

agent_chain_2 = RunnablePassthrough.assign(
    agent_scratchpad= lambda x: format_to_openai_functions(x["intermediate_steps"])
) | prompt | model_jira_with_tool_test | OpenAIFunctionsAgentOutputParser()

@st.cache_resource()
def memory():
    memory = ConversationBufferMemory(return_messages=True,memory_key="chat_history")
    return memory

memory = memory()
agent_executor = AgentExecutor(agent=agent_chain_2, tools=tools, verbose=True, memory=memory,)


# Streamed response emulator
def response_generator(response):
    time.sleep(0.03)
    for word in response.split(" "):
        yield word+ " "
        time.sleep(0.03)

if "messages" not in st.session_state:
    st.session_state.messages = []

with st.container():
    col1, col2 = st.columns([0.8,0.2])
    with col1:
        st.title("Agente Funcional")
    with col2:
        if st.button(":gear:",use_container_width=True):
            config()


@st.fragment
def atualizar_chat(chat_container,prompt=None):
    with chat_container:
        if not prompt:
            initial_message = st.chat_message("assistant")
            initial_message.write("Olá, como posso ajudá-lo hoje?")
        messages = st.session_state.messages

        for i in range(0,len(messages)):
            message = messages[i]       
                                
            if message['role'] == "assistant":
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
            else:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])    

        if prompt:
            with st.chat_message("assistant"):
                with st.spinner(''):
                    response=agent_executor.invoke({'input':prompt})['output']
                st.write_stream(response_generator(response))

            st.session_state.messages.append({"role": "assistant", "content": response})


chat_container = st.container(height=400,border=False)
atualizar_chat(chat_container)

if prompt:= st.chat_input("Faça uma pergunta", key="user_input"):

    st.session_state.messages.append({"role": "user", "content": prompt})
    atualizar_chat(chat_container,prompt)

