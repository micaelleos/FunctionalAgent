import streamlit as st
from atlassian import Jira

def config_jira():
    JIRA_INSTANCE_URL = st.session_state.credenciais["url"]
    USER_NAME = st.session_state.credenciais["email"]
    PASSWORD = st.session_state.credenciais["api_key"]
    jira = Jira(
    url= JIRA_INSTANCE_URL,
    username= USER_NAME,
    password= PASSWORD,
    cloud=True)
    return jira