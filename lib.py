"""Misc functions used in other scripts
"""
import os
import re

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


def get_vectorstore(out_dir):
    "Get the vector store configured with persistence in {out_dir}/Db"
    db_dir = os.path.join(out_dir, "Db")
    vectorstore = Chroma(
        embedding_function=get_embeddings(),
        persist_directory=db_dir,
    )
    return vectorstore


def get_indexer(out_dir):
    "Get the indexer associated with the vector store"
    return VectorStoreIndexWrapper(vectorstore=get_vectorstore(out_dir))


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
