"""Misc functions used in other scripts
"""

import datetime
import hashlib
import json
import os
import re
import sys
import time

import chromadb
from langchain.chains import RetrievalQAWithSourcesChain
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.indexes.vectorstore import VectorStoreIndexWrapper

# pylint: disable=no-name-in-module
from langchain.llms import OpenAI

# pylint: disable=no-name-in-module
from langchain.vectorstores import Chroma


def cleanup_text(text):
    """Clean up text

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
    "Compare if {fname} and {oname} have the same timestamp"
    ftime = os.stat(fname).st_mtime
    # do not write if the timestamps are the same
    try:
        otime = os.stat(oname).st_mtime
        if otime == ftime:
            return True
    except FileNotFoundError:
        pass
    return False


def is_history_filename(fname):
    "Check if the filename is an history filename"
    return (
        fname.find("History") != -1
        or fname.find("Journal") != -1
        or fname.find("StatusReport") != -1
    )


def local_link(path):
    "Create a local link to a file"
    if path.startswith("/"):
        return f"file://{path}"
    return path


class Agent:
    "Agent to answer questions"

    def __init__(self):
        "Initialize the agent"
        self.vectorstore = get_vectorstore()
        self.chain = RetrievalQAWithSourcesChain.from_llm(
            llm=OpenAI(temperature=0),
            retriever=self.vectorstore.as_retriever(),
        )

    def question(self, user_question):
        "Ask a question and format the answer for text"
        response = self._get_response(user_question)
        if response["sources"] != "None.":
            sources = "- " + "\n- ".join(self._get_real_sources(response["sources"]))
            return f"{response['answer']}\nSources:\n{sources}"
        return response["answer"]

    def html_question(self, user_question):
        "Ask a question and format the answer for html"
        response = self._get_response(user_question)
        if response["sources"] != "None.":
            sources = "- " + "\n- ".join(
                [
                    f'<a href="{local_link(src)}">{src}</a>'
                    for src in self._get_real_sources(response["sources"])
                ]
            )
            return f"{response['answer']}\nSources:\n{sources}"
        return response["answer"]

    def _get_response(self, user_question):
        "Get the response from the LLM and vector store"
        return self.chain({"question": user_question})

    def _get_real_sources(self, sources):
        "Get the url instead of the chunk sources"
        real_sources = []
        for source in sources.split(", "):
            results = self.vectorstore.get(
                include=["metadatas"], where={"source": source}
            )
            if (
                results
                and "metadatas" in results
                and len(results["metadatas"]) > 0
                and "url" in results["metadatas"][0]
            ):
                url = results["metadatas"][0]["url"]
                if url not in real_sources:
                    real_sources.append(url)
            else:
                real_sources.append(source)
        return real_sources


class ChecksumStore:
    "Store checksums of files"

    def __init__(self, checksum_file="checksums.json"):
        "Initialize the checksum store"
        self.checksum_file = checksum_file
        self.checksums = {}
        self._load_checksums()

    def _load_checksums(self):
        "Load the checksums from the checksum file"
        if os.path.exists(self.checksum_file):
            with open(self.checksum_file, encoding="utf-8") as in_f:
                self.checksums = json.load(in_f)

    def store_checksum(self, filename, checksum):
        "Store the checksum of a file"
        self.checksums[filename] = checksum
        with open(self.checksum_file, "w", encoding="utf-8") as out_f:
            json.dump(self.checksums, out_f)

    def has_file_changed(self, filename):
        "Check if a file has changed"
        checksum = self.compute_checksum(filename)
        if filename not in self.checksums:
            self.store_checksum(filename, checksum)
            return None
        if checksum != self.checksums[filename]:
            self.store_checksum(filename, checksum)
            return True
        return False

    def compute_checksum(self, filename, algorithm="md5"):
        """
        Compute the checksum of a file using the given algorithm.
        Default algorithm is MD5.
        """
        hash_function = getattr(hashlib, algorithm)()
        with open(filename, "rb") as in_f:
            for chunk in iter(lambda: in_f.read(4096), b""):
                hash_function.update(chunk)
                return hash_function.hexdigest()


class DateTimeEncoder(json.JSONEncoder):
    "Encode datetime objects to json"

    def default(self, o):
        "Encode datetime objects to json as isoformat strings"
        if isinstance(o, datetime.datetime):
            return o.isoformat()
        return super().default(o)


# Custom deserialization function
def datetime_decoder(dct):
    "Decode datetime objects from json"
    for key, val in dct.items():
        if key.endswith("_at") or key.find("date") != -1:
            try:
                if isinstance(val, str):
                    dct[key] = datetime.datetime.fromisoformat(val)
                elif isinstance(val, float):
                    dct[key] = datetime.datetime.fromtimestamp(val)
            except ValueError:
                pass  # Not a valid datetime string, leave as is
    return dct


# lib.py ends here
