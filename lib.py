"""Misc functions used in other scripts
"""
import os
import re
import sys
import time

import chromadb
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.indexes.vectorstore import VectorStoreIndexWrapper
from langchain.vectorstores import Chroma


def cleanup_text(text):
    """Clean up tetextt.

    - remove urls
    - remove hashtag
    - remove consecutive spaces
    - remove consecutive newlines
    """
    text = re.sub(r"https?://\S+", "", text)
    text = text.replace("#", "")
    text = re.sub(r"^[ \t]+$", "", text, flags=re.M)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def get_embeddings():
    "Get the vector embeddings for text"
    return HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")


def get_vectorstore():
    "Get the vector store configured with an http server"
    client = chromadb.HttpClient(settings=chromadb.config.Settings(allow_reset=True))
    tries = 0
    while tries < 12:
        tries += 1
        try:
            vectorstore = Chroma(
                embedding_function=get_embeddings(),
                client=client,
            )
            print(
                f"Number of documents in the vector store: {vectorstore._collection.count()}",  # pylint: disable=protected-access
                file=sys.stderr,
            )
            break
        except Exception as excpt:  # pylint: disable=broad-except
            print(excpt, file=sys.stderr)
            print(
                f"Could not connect to the vector store, retrying in 5 seconds ({tries})",
                file=sys.stderr,
            )
            time.sleep(5)
            continue
    else:
        print("Could not connect to the vector store, giving up.", file=sys.stderr)
        sys.exit(1)
    return vectorstore


def get_indexer():
    "Get the indexer associated with the vector store"
    return VectorStoreIndexWrapper(vectorstore=get_vectorstore())


def is_same_time(fname, oname):
    "compare if {fname} and {oname} have the same timestamp"
    ftime = os.stat(fname).st_mtime
    # do not write if the timestamps are the same
    try:
        otime = os.stat(oname).st_mtime
        if otime == ftime:
            return True
    except FileNotFoundError:
        pass
    return False


# lib.py ends here
