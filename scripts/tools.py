from pydantic import BaseModel, Field
from typing import List, Literal, Optional
from atlassian import Jira
from dotenv import dotenv_values
from langchain.agents import tool
import inspect
from langchain_core.tools import StructuredTool,BaseTool


class IssueJira(BaseModel):
    project: str = Field(description="nome do projeto onde será criado o issue")
    title: str = Field(description="Nome do issue, em frase resumida com até 4 palavras")
    description: str = Field(description="descrição do issue.")
    issuetype: Literal['Task', 'Story', 'Epic'] =  Field(description="Tipo do issue a ser criado")
    priority: Literal['Highest', 'High', 'Medium','Low','Lowest'] = Field(description="An issue's priority indicates its relative importance. ")


class Toolkit_Jira:
    
    def __init__(self,**kwargs):

        if kwargs:
            self.url= kwargs["jira_url"],
            self.username= kwargs["email"],
            self.password= kwargs["password"],
        else:
            self.config = dotenv_values(".env") # modificar isso aqui para que as pessoas possa entrar com seus proprios logins
            self.url= self.config["JIRA_INSTANCE_URL"],
            self.username= self.config["USER_NAME"],
            self.password= self.config["PASSWORD"],
        
        self.jira = Jira(
        url= self.url,
        username= self.username,
        password= self.password,
        cloud=True)
    
    def listar_tools(self):
        funcoes_structuredtool = []
        funcoes = []
        for nome, membro in inspect.getmembers(self.__class__):
            if isinstance(membro, StructuredTool):
                funcoes_structuredtool.append(nome)
                funcoes.append(membro)
        return funcoes

    @tool(args_schema=IssueJira)
    def criar_issue_Jira(self,**dict_info:IssueJira) -> dict:
        """Chame essa função para criar issues no Jira"""
        fields = {
            "project":
            {
                "key": dict_info["project"]
            },
            "summary": dict_info["title"],
            "description": dict_info["description"],
            "issuetype": {
                "name": dict_info["issuetype"]
            },
                'priority': {
                    'name': dict_info["priority"] # Substitua pelo nível de prioridade desejado (por exemplo, 'High', 'Medium', 'Low')
                }
            }

        # Create issue
        result = self.jira.issue_create(fields)
        return result
     

if __name__ == "__main__":
    teste = Toolkit_Jira()
    print(teste.listar_tools())


# Get all projects
# Returns all projects which are visible for the currently logged in user.
#jira.projects(included_archived=None, expand=None)

# Get project
#jira.project(key, expand=None)

# Get issue by key
#jira.issue(key)

# Update issue field
#fields = {'summary': 'New summary'}
#jira.update_issue_field(key, fields, notify_users=True)

# Create issue
#jira.issue_create(fields) #{{"summary": "test issue", "description": "test description", "issuetype": {{"name": "Task"}}, "priority": {{"name": "Low"}}}}

# Issues within an Epic
#jira.epic_issues(epic_key)

# Returns all epics from the board, for the given board Id.
# This only includes epics that the user has permission to view.
# Note, if the user does not have permission to view the board, no epics will be returned at all.
#jira.get_epics(board_id, done=False, start=0, limit=50, )