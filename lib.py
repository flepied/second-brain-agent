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
from langchain.chains import VectorDBQAWithSourcesChain
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.indexes.vectorstore import VectorStoreIndexWrapper

# pylint: disable=no-name-in-module
from langchain.llms import OpenAI

# pylint: disable=no-name-in-module
from langchain.vectorstores import Chroma

from extractors import (  # extract_sentence_no_time,
    extract_documents,
    extract_intent,
    extract_period,
    extract_step_back,
)


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
        self.llm = OpenAI(temperature=0)
        self.chain = VectorDBQAWithSourcesChain.from_llm(
            llm=self.llm,
            vectorstore=self.vectorstore,
            return_source_documents=True,
        )
        try:
            with open("documents-desc.txt", "r", encoding="UTF-8") as desc_file:
                self.documents_desc = desc_file.read()
        except FileNotFoundError:
            self.documents_desc = ""

    def question(self, user_question):
        "Ask a question and format the answer for text"
        response = self._get_response(user_question)
        if (
            response["sources"] not in ("None.", "N/A", "I don't know.")
            and len(response["source_documents"]) > 0
        ):
            sources = "- " + "\n- ".join(self._filter_file(self._get_sources(response)))
            return f"{response['answer']}\nSources:\n{sources}"
        return response["answer"]

    def html_question(self, user_question):
        "Ask a question and format the answer for html"
        response = self._get_response(user_question)
        if (
            response["sources"] not in ("None.", "N/A", "I don't know.")
            and len(response["source_documents"]) > 0
        ):
            sources = "- " + "\n- ".join(
                [
                    f'<a href="{local_link(src)}">{src}</a>'
                    for src in self._get_sources(response)
                ]
            )
            return f"{response['answer']}\nSources:\n{sources}"
        return response["answer"]

    def _filter_file(self, sources):
        "filter our file:// at the beginning of the strings"
        return [src[7:] if src.startswith("file://") else src for src in sources]

    def _get_response(self, user_question):
        "Get the response from the LLM and vector store"
        res_intent = extract_intent(user_question, model=self.llm)
        if res_intent is None or res_intent.intent.lower() == "regular question":
            return self._regular_question(user_question)
        if res_intent.intent.lower() == "activity report request":
            return self._activity_report(user_question)
        return self._regular_question(user_question)

    def _activity_report(self, user_question):
        "Answer an activity report request"
        and_clause = []
        and_clause.append({"type": {"$eq": "history"}})
        subject = "Highlight the main events and activities."

        res_dates = extract_period(user_question, model=self.llm)
        print(res_dates)
        print()

        if res_dates is not None:
            start_date = datetime.datetime.combine(
                res_dates.start_date, datetime.datetime.min.time()
            ).timestamp()
            and_clause.append({"last_accessed_at": {"$gte": start_date}})

            end_date = datetime.datetime.combine(
                res_dates.end_date, datetime.time(23, 59, 59)
            ).timestamp()
            and_clause.append({"last_accessed_at": {"$lte": end_date}})
        else:
            print(f"No period in the sentence: {user_question}", file=sys.stderr)

        res_doc = extract_documents(user_question, self.documents_desc, model=self.llm)

        # we can have multiple documents so add them with a logical OR
        or_clause = []
        for doc in res_doc.document_names:
            or_clause.append({"referer": {"$eq": doc}})
        if len(or_clause) > 1:
            or_clause = {"$or": or_clause}
        elif len(or_clause) == 1:
            or_clause = or_clause[0]
        if or_clause != []:
            and_clause.append(or_clause)

        if len(and_clause) > 1:
            where_clause = {"$and": and_clause}
        else:
            where_clause = and_clause[0]

        print(f"{subject=} {where_clause=}", file=sys.stderr)
        self.chain.search_kwargs = {"filter": where_clause}
        res = self.chain({"question": subject})
        print(f"{res=}", file=sys.stderr)
        return res

    def _regular_question(self, user_question):
        "Answer a regular question"
        res_step_back = extract_step_back(user_question)
        if res_step_back is not None:
            print(f"Step back {res_step_back}", file=sys.stderr)
        res = self.chain({"question": user_question})
        return res

    def _get_sources(self, resp):
        "Get the url instead of the chunk sources"
        ret = []
        for doc in resp["source_documents"]:
            if doc.metadata["url"] not in ret:
                ret.append(doc.metadata["url"])
        return ret

    def _build_filter(self, metadata):
        "Build the filter for the vector store from the metadata"
        if metadata is None or len(metadata) == 0:
            return {}
        if len(metadata) == 1:
            return {"filter": metadata}
        return {"filter": {"$and": [{key: metadata[key]} for key in metadata]}}


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
