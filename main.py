import streamlit as st

pages = {
    "Menu": [
        st.Page("chat.py", title="Chat"),
        st.Page("jira_list.py", title="Seus projetos Jira"),
        st.Page("issues_list.py", title="Issues criados"),
    ],
    "Recursos": [
         st.Page("learn.py", title="Sobre"),
     ]
}

st.logo("logo.png", icon_image="jira_logo.png", size="large")
pg = st.navigation(pages)
pg.run()