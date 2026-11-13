# lista issues criados na sessão
import streamlit as st

st.title("Issues criados")

#https://micaelleosouza.atlassian.net/rest/api/2/universal_avatar/view/type/issuetype/avatar/10307?size=medium
#st.image(proj['avatarUrls']['16x16'],use_container_width=True)

if "issues" not in st.session_state:
    st.info("Você ainda não criou nenhum issue.")
else:    
    if len(st.session_state.issues)==0:
        st.info("Você ainda não criou nenhum issue.")

    else:

        with st.container():

            for issue in st.session_state.issues:
                with st.container(height=400, border=True):
                    col = st.columns([0.4,0.4,0.2])
                    with col[0]:
                        st.write(f"**Key:** {issue['key']}")
                    with col[1]:
                        st.write(f"**Tipo:** {issue['issuetype']['name']}")
                    with col[2]:
                        st.link_button(":link:",url=f"{st.session_state.credenciais['url']}browse/{issue['key']}",use_container_width=True)
                    st.write(f"**Título: {issue['summary']}**")
                    st.write(f"**Descrição**:{issue['description']}")

    