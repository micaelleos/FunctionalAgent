import streamlit as st

st.markdown("""
# Sobre o App  

Bem-vindo ao **Agente Funcional**! Este aplicativo foi desenvolvido para simplificar o processo de criação de documentações funcionais e integração com o Jira, economizando seu tempo e otimizando sua produtividade.  

Com tecnologia de IA avançada, nosso agente ajuda você a:  
- **Criar User Stories e Documentações Funcionais**: A partir de descrições simples, o app gera histórias de usuário e critérios de aceitação claros e bem estruturados.  
- **Refinar Suas Ideias**: Receba sugestões contextuais para melhorar a qualidade e a clareza do conteúdo.  
- **Exportar para o Jira**: Transforme suas User Stories em issues no Jira com apenas um clique.  

---

## Como Utilizar  

1. **Crie ou Refine User Stories**  
   - Comece descrevendo uma funcionalidade ou requisito no campo de entrada do app.  
   - A IA irá gerar automaticamente User Stories e critérios de aceitação.  

2. **Ajuste Detalhes**  
   - Edite ou complemente os textos gerados para adequá-los perfeitamente às suas necessidades.  

3. **Exporte para o Jira**  
   - Peça para a AI exportar ao Jira a documentação. Antes, entre com as suas credenciais do Jira no íncone de engrenagem. Obs.: Você vai precisar de uma **Chave API do Jira**.

---

## Como Conseguir uma Chave de API do Jira  

Para que o app possa enviar suas User Stories diretamente para o Jira, é necessário configurar uma **Chave de API**. Veja como:  

1. **Acesse sua conta no Jira**  
   - Vá para o endereço do seu Jira (ex.: `https://seu-dominio.atlassian.net`).  

2. **Gerar Chave API**  
   - Clique no seu perfil (canto superior direito) e selecione **Gerenciar Conta**.  
   - Na aba de segurança, clique em **Criar e Gerenciar Chaves de API**.  
   - Nomeie a chave, gere e copie o valor. Essa será a senha que será usada no Agente Funcional.

3. **Salve sua Chave com Segurança**  
   - Guarde sua chave em um local seguro. Você precisará dela para integrar o app ao Jira.  

4. **Use a Chave no App**  
   - Insira sua chave na configuração do app.  

Agora, com tudo configurado, basta começar a criar e enviar suas histórias diretamente para o seu projeto no Jira!  

Se precisar de ajuda, entre em contato pela seção de suporte ou consulte nosso guia de usuário. 🚀  

""")