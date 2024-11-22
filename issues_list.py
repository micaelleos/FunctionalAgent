# lista issues criados na sessão
import streamlit as st

with st.container():

    for issue in st.session_state.issues:
        with st.container(height=400, border=True):
            st.write(f"**Key:** {issue['key']}")
            st.write(f"**Título: {issue['summary']}**")
            st.write(f"**Descrição**:{issue['description']}")
            st.write("Mais informações:")
            st.write(issue)

    