import streamlit as st

pages = {
    "Your account": [
        st.Page("chat.py", title="Chat with agent"),
        st.Page("jira_list.py", title="View your projects"),
    ],
    "Resources": [
        #st.Page("learn.py", title="Learn about us"),
        #st.Page("trial.py", title="Try it out"),
    ],
}

pg = st.navigation(pages)
pg.run()