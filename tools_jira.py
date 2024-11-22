from scripts.jira import config_jira
from typing import List, Literal, Optional
from langchain.agents import tool
from langchain_core.tools import StructuredTool,BaseTool
from pydantic import BaseModel, Field


class IssueJira(BaseModel):
    project: str = Field(description="nome do projeto onde será criado o issue")
    title: str = Field(description="Nome do issue, em frase resumida com até 4 palavras")
    description: str = Field(description="descrição do issue, em formato markdown")
    issuetype: Literal['Task', 'Story', 'Epic'] =  Field(description="Tipo do issue a ser criado")
    priority: Literal['Highest', 'High', 'Medium','Low','Lowest'] = Field(description="An issue's priority indicates its relative importance. ")


@tool(args_schema=IssueJira)
def criar_issue_jira(**dict_info:IssueJira) -> dict:
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
        }
        }
    
    try:    # Create issue
        jira = config_jira()
        result = jira.issue_create(fields)
        print(result)
    except Exception as e:
        print(e)
        if type(e).__name__ in ['MissingSchema','NameError']:
            return "Aconteceu um erro ao enviar o issue ao Jira. O usuário não configurou as credenciais da sua conta do Jira"
        else:
            return f"Aconteceu o erro {type(e).__name__} ao enviar o issue ao Jira"
    
    return result


@tool
def get_all_projects() -> dict:
    """Chame essa ferramenta para consultar os projeotos no Jira"""    
    try:   
        jira = config_jira()
        result = jira.get_all_projects(included_archived=None, expand=None)
        print(result)
    except Exception as e:
        print(e)
        if type(e).__name__ in ['MissingSchema','NameError']:
            return "Aconteceu um erro consultar os projetos no Jira. O usuário não configurou as credenciais da sua conta do Jira"
        else:
            return f"Aconteceu o erro {type(e).__name__} ao consultar o projeto no Jira"
    
    return result


class ConsultaIssue(BaseModel):
    issue_key: str = Field(description="chave do issue no Jira")

@tool(args_schema=ConsultaIssue)
def consultar_issue(**dict_info:ConsultaIssue) -> dict:
    """Chame essa ferramenta para consultar issues no Jira"""    
    key = dict_info["issue_key"]
    
    try:    
        jira = config_jira()
        result = jira.issue(key)
        print("resultado 2 ------------------",result)
    except Exception as e:
        print(e)
        if type(e).__name__ in ['MissingSchema','NameError']:
            return "Aconteceu um erro ao consultar o issue ao Jira. O usuário não configurou as credenciais da sua conta do Jira"
        else:
            return f"Aconteceu o erro {type(e).__name__} ao consultar o issue ao Jira"
    
    return result

class AtualizarIssueJira(BaseModel):
    project: str = Field(description="nome do projeto onde será criado o issue")
    title: str = Field(description="Nome do issue, em frase resumida com até 4 palavras")
    description: str = Field(description="descrição do issue, em formato markdown")
    issuetype: Literal['Task', 'Story', 'Epic'] =  Field(description="Tipo do issue a ser criado")
    priority: Literal['Highest', 'High', 'Medium','Low','Lowest'] = Field(description="An issue's priority indicates its relative importance. ")
    issue_key: str = Field(description="chave do issue no Jira")

@tool(args_schema=AtualizarIssueJira)
def atualizar_issue_jira(**dict_info:AtualizarIssueJira) -> dict:
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
        }
        }
    
    key = dict_info["issue_key"]

    try: 
        jira = config_jira()
        result = jira.update_issue_field(key, fields)
        print(result)
    except Exception as e:
        print(e)
        if type(e).__name__ in ['MissingSchema','NameError']:
            return "Aconteceu um erro ao atualizar o issue ao Jira. O usuário não configurou as credenciais da sua conta do Jira"
        else:
            return f"Aconteceu o erro {type(e).__name__} ao atualizar o issue ao Jira"
    
    return result


class ConsultaEpic(BaseModel):
    epic_key: str = Field(description="chave do issue do tipo epic, no Jira")

@tool(args_schema=ConsultaEpic)
def consultar_epic(**dict_info:ConsultaEpic) -> dict:
    """Chame essa ferramenta para consultar issues dentro de um Epic no Jira"""    
    key = dict_info["epic_key"]
    
    try:    
        jira = config_jira()
        result = jira.epic_issues(key)
        print("Resultado -------------------",result)
    except Exception as e:
        print(e)
        if type(e).__name__ in ['MissingSchema','NameError']:
            return "Aconteceu um erro ao consultar os issue do Épico ao Jira. O usuário não configurou as credenciais da sua conta do Jira"
        else:
            return f"Aconteceu o erro {type(e).__name__} ao consultar os issue do Épico no Jira"
    
    return result


# # Move issues to backlog
# jira.move_issues_to_backlog(issue_keys)

# # Add issues to backlog
# jira.add_issues_to_backlog(issue_keys)

# # Get agile board by filter id
# jira.get_agile_board_by_filter_id(filter_id)

# # Issues within an Epic
# jira.epic_issues(epic_key)

# # Returns all epics from the board, for the given board Id.
# # This only includes epics that the user has permission to view.
# # Note, if the user does not have permission to view the board, no epics will be returned at all.
# jira.get_epics(board_id, done=False, start=0, limit=50, )

tools = [criar_issue_jira,get_all_projects,consultar_issue,atualizar_issue_jira,consultar_epic]