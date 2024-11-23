import streamlit as st
from scripts.jira import config_jira

st.title("Seus projetos no Jira")

def project_bloc(proj):
    with st.container(height=200):
        with st.container():
            col1, col2 = st.columns(2)  
            with col1:
                st.write(f"**ID:** {proj['id']}")
            with col2:
                st.write(f"**Key:** {proj['key']}")
        with st.container():
            col1x , col2x = st.columns([0.2,0.6])
            with col1x:
                st.image(proj['avatarUrls']['16x16'],use_container_width=True)
            with col2x:
                st.write(f"**Título:** {proj['name']}")
        st.write(f"Issues: {jira.get_project_issues_count(proj['key'])}")
        st.link_button("Abrir projeto", f"{st.session_state.credenciais['url']}/jira/software/projects/{proj['key']}/issues", use_container_width=True)

        
        #'avatarUrls' '24x24'
    

if "credenciais" not in st.session_state:
    st.info("Entre com suas credenciais do Jira para visualizar seus projetos")
    with st.form("my_form"):
        st.write(f"Entre com as suas credenciais do Jira:")
        url = st.text_input("Jira URL")
        email = st.text_input("Email")
        api_key = st.text_input("API Key")

        # Every form must have a submit button.
        submitted = st.form_submit_button("Submit")
        if submitted:
            st.session_state.credenciais = {"url": url, "email": email,"api_key": api_key}       
else:
    st.title("Seus projetos no Jira:")
    jira = config_jira()
    projects = jira.get_all_projects(included_archived=None, expand=None)
    cols = st.columns(3)
    i=0
    for proj in projects:
        with cols[i]:
            project_bloc(proj)
            i= i + 1
        if i > 2:
            i=0
