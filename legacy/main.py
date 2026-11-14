import streamlit as st

pages = {
    "Menu": [
        st.Page("./pages/chat_page.py", title="Chat"),
        st.Page("./pages/projects_list_page.py", title="Seus projetos Jira"),
        st.Page("./pages/issues_list_page.py", title="Issues criados"),
    ],
    "Recursos": [
         st.Page("./pages/sobre_page.py", title="Sobre"),
     ]
}

st.logo("./src/img/logo.png", icon_image="./src/img/jira_logo.png", size="large")
pg = st.navigation(pages)
pg.run()