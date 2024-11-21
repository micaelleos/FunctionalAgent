import streamlit as st

pages = {
    "Menu": [
        st.Page("chat.py", title="Chat with agent"),
        st.Page("jira_list.py", title="View your projects"),
    ],
    "Resources": [
        #st.Page("learn.py", title="Learn about us"),
        #st.Page("trial.py", title="Try it out"),
    ],
}

st.logo("logo.png", icon_image="jira_logo.png", size="large")
pg = st.navigation(pages)
pg.run()