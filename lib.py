import os

from langchain.vectorstores import Chroma
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.indexes.vectorstore import VectorStoreIndexWrapper


def get_embeddings():
    return HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")


def get_vectorstore(out_dir):
    vectorstore = Chroma(
        embedding_function=get_embeddings(),
        persist_directory=os.path.join(out_dir, "Db"),
    )
    return vectorstore


def get_indexer(out_dir):
    return VectorStoreIndexWrapper(vectorstore=get_vectorstore(out_dir))


# lib.py ends here
