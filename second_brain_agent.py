#!/usr/bin/env python

"""
Web UI to interact with the second brain data
"""

import os
import sys

from dotenv import load_dotenv

from langchain.chains import ConversationalRetrievalChain
from langchain.chat_models import ChatOpenAI

# Front end web app
import gradio as gr

from lib import get_vectorstore


def main(out_dir):
    db = get_vectorstore(out_dir)
    # Initialise Langchain - Conversation Retrieval Chain
    qa = ConversationalRetrievalChain.from_llm(
        ChatOpenAI(temperature=0), db.as_retriever()
    )

    with gr.Blocks() as demo:
        chatbot = gr.Chatbot()
        msg = gr.Textbox()
        clear = gr.Button("Clear")
        chat_history = []

        def user(user_message, history):
            print(f"{user_message=}", file=sys.stderr)
            # Get response from QA chain
            response = qa({"question": user_message, "chat_history": history})
            # Append user message and response to chat history
            history.append((user_message, response["answer"]))
            return gr.update(value=""), history

        msg.submit(user, [msg, chatbot], [msg, chatbot], queue=False)
        clear.click(lambda: None, None, chatbot, queue=False)

    demo.launch(debug=True)


if __name__ == "__main__":
    load_dotenv()
    main(os.environ["DSTDIR"])

# second_brain_agent.py ends here
