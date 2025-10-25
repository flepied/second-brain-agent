"""Misc functions used in other scripts"""

import datetime
import hashlib
import json
import os
import re
import sys
import time

import chromadb
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings


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
            break
        except Exception as expt:  # pylint: disable=broad-except
            print(expt, file=sys.stderr)
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
        modified = False
        for key in list(self.checksums.keys()):
            if not os.path.exists(key):
                print(
                    f"Removing checksum for {key} as the file does not exist",
                    file=sys.stderr,
                )
                del self.checksums[key]
                modified = True
        if modified:
            print("Saving modified checksums", file=sys.stderr)
            self.save_checksums()

    def store_checksum(self, filename, checksum):
        "Store the checksum of a file"
        self.checksums[filename] = checksum
        self.save_checksums()

    def save_checksums(self):
        "Save the checksums to the checksum file"
        with open(self.checksum_file, "w", encoding="utf-8") as out_f:
            json.dump(self.checksums, out_f)

    def has_file_changed(self, filename):
        "Check if a file has changed"
        checksum = self.compute_checksum(filename)
        print(f"Computed checksum for {filename}: {checksum}", file=sys.stderr)
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
