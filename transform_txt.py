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
from langchain.docstore.document import Document

CHUNK_SIZE = 500
CHUNK_OVERLAP = 50


def create_indexer(out_dir):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP
    )
    embedding = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    vectorstore = Chroma(
        embedding_function=embedding,
        persist_directory=os.path.join(out_dir, "Db"),
    )
    return vectorstore, text_splitter


def process_file(fname, out_dir, indexer, splitter):
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
    metadatas = []
    texts = []
    n = 0
    for chunk in splitter.split_text(content):
        n = n + 1
        id = f"{basename}-{n:04d}.txt"
        oname = os.path.join(out_dir, "Chunk", id)
        texts.append(chunk)
        metadatas.append({"url": f"file://{fname}", "source": oname})
        with open(oname, "w") as out_f:
            print(chunk, file=out_f)
        # set the timestamp to be the same
        stat = os.stat(fname)
        os.utime(oname, (stat.st_atime, stat.st_mtime))

    if len(texts) == 0:
        print(f"Unable to split doc {fname}", file=sys.stderr)
    else:
        print(f"Storing {len(texts)} chunks to the db for {fname}", file=sys.stderr)
        indexer.add_texts(texts, metadatas)


def main(in_dir, out_dir):
    print(f"Storing files under {out_dir}")
    indexer, splitter = create_indexer(out_dir)
    # read filenames from stdin
    if in_dir == "-":
        print("Reading filenames from stdin", file=sys.stderr)
        for fname in sys.stdin:
            process_file(fname.rstrip(), out_dir, indexer, splitter)
    else:
        # scan input dir
        print(f"Looking up files in {in_dir}", file=sys.stderr)
        for entry in os.scandir(in_dir):
            process_file(os.path.join(in_dir, entry.name), out_dir, indexer, splitter)


if __name__ == "__main__":
    load_dotenv()
    main(sys.argv[1], sys.argv[2])

# transform_txt.py ends here
