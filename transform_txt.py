#!/usr/bin/env python

"""
Transform txt files into chunks of text then transform the chunks
into vector embeddings and store the vectors in a vector database.
"""

import os
import sys

from dotenv import load_dotenv

from langchain.vectorstores import Chroma
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter

from chromadb.config import Settings


REPO_ID = "sentence-transformers/all-mpnet-base-v2"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50


def process_file(fname, out_dir):
    print(f"Processing '{fname}'", file=sys.stderr)
    if not fname.endswith(".txt"):
        print(f"Ignoring non txt file {fname}", file=sys.stderr)
        return
    ftime = os.stat(fname).st_mtime
    basename = os.path.basename(fname[:-4])
    oname = os.path.join(out_dir, "Chunk", basename + "-0001.txt")
    # do not write if the timestamps are the same
    try:
        otime = os.stat(oname).st_mtime
        if otime == ftime:
            return
    except FileNotFoundError:
        pass
    content = open(fname).read(-1)
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP
    )
    # Define the Chroma settings
    CHROMA_SETTINGS = Settings(
        chroma_db_impl="duckdb+parquet",
        persist_directory=os.path.join(out_dir, "Db"),
        anonymized_telemetry=False,
    )
    hf = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    db = Chroma(
        persist_directory=os.path.join(out_dir, "Db"),
        embedding_function=hf,
        client_settings=CHROMA_SETTINGS,
    )
    n = 0
    for chunk in text_splitter.split_text(content):
        n = n + 1
        id = f"{basename}-{n:04d}.txt"
        print(f"adding chunk {id} to the db", file=sys.stderr)
        db.add_texts(texts=[chunk], ids=[id])
        oname = os.path.join(out_dir, "Chunk", id)
        print(f"writing {oname}", file=sys.stderr)
        with open(oname, "w") as out_f:
            print(chunk, file=out_f)
        # set the timestamp to be the same
        stat = os.stat(fname)
        os.utime(oname, (stat.st_atime, stat.st_mtime))
    db.persist()


def main(in_dir, out_dir):
    print(f"Storing files under {out_dir}")
    # read filenames from stdin
    if in_dir == "-":
        print("Reading filenames from stdin", file=sys.stderr)
        for fname in sys.stdin:
            process_file(fname.rstrip(), out_dir)
    else:
        # scan input dir
        print(f"Looking up files in {in_dir}", file=sys.stderr)
        for entry in os.scandir(in_dir):
            process_file(os.path.join(in_dir, entry.name), out_dir)


if __name__ == "__main__":
    load_dotenv()
    main(sys.argv[1], sys.argv[2])

# transform_txt.py ends here
