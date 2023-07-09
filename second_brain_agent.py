"""Second brain web interface

Take a question from the user and call the LLM for an answer using the
closest documents stored in the vector database as context.
"""

import os

import streamlit as st
from dotenv import load_dotenv
from langchain.chains import ConversationalRetrievalChain
from langchain.chat_models import ChatOpenAI
from langchain.memory import ConversationBufferMemory

from htmlTemplates import bot_template, css, user_template
from lib import get_vectorstore


def handle_userinput(user_question):
    "Handle the input from the user as a question to the LLM"
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


def clear_input_box():
    "Empty the input box"
    handle_userinput(st.session_state["question"])
    st.session_state["question"] = ""


def main():
    "Entry point"
    load_dotenv()
    st.set_page_config(page_title="Chat with your Second Brain", page_icon=":brain:")
    st.write(css, unsafe_allow_html=True)
    st.header("Chat with your Second Brain :brain:")

    if "conversation" not in st.session_state:
        memory = ConversationBufferMemory(
            memory_key="chat_history", return_messages=True
        )
        st.session_state.conversation = ConversationalRetrievalChain.from_llm(
            ChatOpenAI(temperature=0),
            get_vectorstore(os.environ["DSTDIR"]).as_retriever(),
            memory=memory,
        )

    st.text_input(
        "Ask a question to your second brain:",
        key="question",
        on_change=clear_input_box,
    )

    st.components.v1.html(
        """
<script>
var input = window.parent.document.querySelectorAll("input[type=text]");

        for (var i = 0; i < input.length; ++i) {{
            input[i].focus();
        }}
</script>
""",
        height=150,
    )
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = None


if __name__ == "__main__":
    main()
