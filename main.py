import streamlit as st

pages = {
    "Menu": [
        st.Page("chat.py", title="Chat"),
        st.Page("jira_list.py", title="Seus projetos Jira"),
        st.Page("issues_list.py", title="Issues criados"),
    ],
    # "Resources": [
    #     #st.Page("learn.py", title="Learn about us"),
    #     #st.Page("trial.py", title="Try it out"),
    # ],
}

st.logo("logo.png", icon_image="jira_logo.png", size="large")
pg = st.navigation(pages)
pg.run()