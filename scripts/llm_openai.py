from dotenv import dotenv_values
from langchain.memory import ConversationBufferMemory
from langchain.agents import AgentExecutor
from langchain.agents.format_scratchpad import format_to_openai_functions
from langchain.agents.output_parsers import OpenAIFunctionsAgentOutputParser
from langchain.tools.render import format_tool_to_openai_function
from langchain.prompts import ChatPromptTemplate
from langchain.chat_models import ChatOpenAI
from langchain.prompts import MessagesPlaceholder
from langchain.schema.runnable import RunnablePassthrough
from langchain.memory import ConversationBufferMemory

class Jira_Agent:
    
    def __init__(self, tools, **params):
        self.config = dotenv_values(".env") 
        self.functions = [format_tool_to_openai_function(f) for f in tools]
        self.model = ChatOpenAI(model="gpt-4o",temperature=0,openai_api_key=self.config["OPENAI_API_KEY"]).bind(functions=self.functions)
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """Você é um especialista em documentação funcional e em Jira.
            Você escreve todo tipo de documentação funcional com base na orientação do usuário.
            Caso seja solicitado essas informações devem ser enviadas ao Jira.
            Caso o usuário não informe o nome do projeto, você deve avisá-lo que ele deve informar o nome do projeto do jira, para que você possa criar o issue.
            Ao criar um issue você deve me avisar qual é o id e a Key do issue, assim como o link para que eu possa abrir-lo no Jira.
            """),
            MessagesPlaceholder(variable_name="chat_history"),
            ("user", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad")
        ])
        self.memory = ConversationBufferMemory(return_messages=True,memory_key="chat_history")
        
        self.chain = RunnablePassthrough.assign(
            agent_scratchpad = lambda x: format_to_openai_functions(x["intermediate_steps"])
        ) | self.prompt | self.model | OpenAIFunctionsAgentOutputParser()
        self.qa = AgentExecutor(agent=self.chain, tools=tools, verbose=True, memory=self.memory)
        
    
    def chat(self,question,memory):
        self.qa.memory = memory
        result = self.qa.invoke({"input": question})
        print(self.qa.memory)
        self.answer = result['output'] 
        return self.answer
        #for response in self.qa({"question": question})['answer']:
        #    yield response
