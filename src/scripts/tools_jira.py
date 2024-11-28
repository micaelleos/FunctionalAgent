from src.scripts.jira import config_jira
from typing import List, Literal, Optional
from langchain.agents import tool
from langchain_core.tools import StructuredTool,BaseTool
from pydantic import BaseModel, Field

import streamlit as st

if "issues" not in st.session_state:
    st.session_state.issues = []

class IssueJira(BaseModel):
    project: str = Field(description="nome do projeto onde será criado o issue")
    title: str = Field(description="Título do issue, em frase resumida com até 4 palavras, demonstrando sua funcionalidade e objetivo")
    description: str = Field(description="descrição do issue")
    issuetype: Literal['Task', 'Story', 'Epic'] =  Field(description="Tipo do issue a ser criado")
    priority: Literal['Highest', 'High', 'Medium','Low','Lowest'] = Field(description="An issue's priority indicates its relative importance. ")
    parentKey: Optional[str] = Field(description="chave do issue pai")

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
        },
        "parent": {
            "key": dict_info.get("parentKey") # Chave da issue pai
        }
        }
    
    try:    # Create issue
        jira = config_jira()
        result = jira.issue_create(fields)
        issue = result | fields
        st.session_state.issues.append(issue)
    except Exception as e:
        if type(e).__name__ in ['MissingSchema','NameError']:
            return "Aconteceu um erro ao enviar o issue ao Jira. O usuário não configurou as credenciais da sua conta do Jira"
        else:
            return f"Erro: {e}"
    
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
            return f"Erro: {e}"
    
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
            return f"Erro: {e}"
    
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
            return f"Erro: {e}"
    
    return result


class ConsultaEpic(BaseModel):
    epic_key: str = Field(description="chave do issue do tipo epic, no Jira")

@tool(args_schema=ConsultaEpic)
def consultar_issues_within_epic(**dict_info:ConsultaEpic) -> dict:
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
            return f"Erro: {e}"
    
    return result

class JQLjiraQuery(BaseModel):
    jql_query: str = Field(description="query JQL")

@tool(args_schema=JQLjiraQuery)
def consultar_jql_query(jql_query:ConsultaEpic) -> dict:
    """Chame essa ferramenta para fazer consultas no Jira com query jql"""  
    try:    
        jira = config_jira()
        
        # JQL para buscar as user stories dentro do projeto sem parent
        

        start_at = 0
        max_results = 50  # Número máximo de issues por página
        result = {}
        while True:
            response = jira.jql(jql_query, start=start_at, limit=max_results)
            issues = response.get("issues", [])
            if not issues:
                break

            for i in range(len(issues)):
                issue = issues[i]
                key = issue["key"]  # Chave da user story (ex.: PROJ-123)
                result[key]={ "issuetype": issue["fields"]["issuetype"],"description": issue["fields"]["description"],"title": issue["fields"]['summary']} # 'description''summary'
            start_at += max_results
        
    except Exception as e:
        print(e)
        if type(e).__name__ in ['MissingSchema','NameError']:
            return "Aconteceu um erro ao consultar os issue do Épico ao Jira. O usuário não configurou as credenciais da sua conta do Jira"
        else:
            return f"Erro: {e}"
    
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

tools = [criar_issue_jira,get_all_projects,consultar_issue,atualizar_issue_jira,consultar_jql_query]#consultar_issues_within_epic,