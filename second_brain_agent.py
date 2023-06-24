import os

import streamlit as st
from dotenv import load_dotenv
from langchain.chat_models import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain
from htmlTemplates import css, bot_template, user_template

from lib import get_vectorstore


def handle_userinput(user_question):
    response = st.session_state.conversation({"question": user_question})
    st.session_state.chat_history = response["chat_history"]

    for i, message in enumerate(st.session_state.chat_history):
        if i % 2 == 0:
            st.write(
                user_template.replace("{{MSG}}", message.content),
                unsafe_allow_html=True,
            )
        else:
            st.write(
                bot_template.replace("{{MSG}}", message.content), unsafe_allow_html=True
            )


def main():
    load_dotenv()
    st.set_page_config(page_title="Chat with your Second Brain", page_icon=":books:")
    st.write(css, unsafe_allow_html=True)

    if "conversation" not in st.session_state:
        memory = ConversationBufferMemory(
            memory_key="chat_history", return_messages=True
        )
        st.session_state.conversation = ConversationalRetrievalChain.from_llm(
            ChatOpenAI(temperature=0),
            get_vectorstore(os.environ["DSTDIR"]).as_retriever(),
            memory=memory,
        )

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = None

    st.header("Chat with your Second Brain :brain:")
    user_question = st.text_input("Ask a question to your second brain:")
    if user_question:
        handle_userinput(user_question)


if __name__ == "__main__":
    main()
