import os

from langchain.vectorstores import Chroma
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.indexes.vectorstore import VectorStoreIndexWrapper

from chromadb.config import Settings


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
