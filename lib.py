import os
import re
import string
import sys

from chromadb.config import Settings
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.indexes.vectorstore import VectorStoreIndexWrapper
from langchain.vectorstores import Chroma


def cleanup_text(x):
    """Clean up text.

    - remove urls
    - remove hashtag
    - remove consecutive spaces
    - remove consecutive newlines
    """
    x = re.sub(r"https?://\S+", "", x)
    x = x.replace("#", "")
    x = re.sub(r"^[ \t]+$", "", x, flags=re.M)
    x = re.sub(r"[ \t]{2,}", " ", x)
    x = re.sub(r"\n{3,}", "\n\n", x)
    return x


def get_embeddings():
    return HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")


def get_vectorstore(out_dir):
    db_dir = os.path.join(out_dir, "Db")
    # Define the Chroma settings
    CHROMA_SETTINGS = Settings(
        chroma_db_impl="duckdb+parquet",
        persist_directory=db_dir,
        anonymized_telemetry=False,
    )
    vectorstore = Chroma(
        embedding_function=get_embeddings(),
        persist_directory=db_dir,
        client_settings=CHROMA_SETTINGS,
    )
    return vectorstore


def get_indexer(out_dir):
    return VectorStoreIndexWrapper(vectorstore=get_vectorstore(out_dir))


# lib.py ends here
