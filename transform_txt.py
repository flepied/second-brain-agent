#!/usr/bin/env python

"""
Transform txt files into chunks of text then transform the chunks
into vector embeddings and store the vectors in a vector database.
"""

import os
import sys

from dotenv import load_dotenv
from langchain.text_splitter import TokenTextSplitter

from lib import cleanup_text, get_vectorstore

# limit chunk size to 1000 as we retrieve 4 documents by default and
# the token limit is 4096
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 50


def get_splitter():
    splitter = TokenTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    return splitter


def process_file(fname: str, out_dir: str, indexer, splitter):
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
    full_content = open(fname).read(-1)
    first_line, content = full_content.split("\n", 1)
    header = first_line.split("=")
    content = cleanup_text(content)
    if len(header) == 2 and header[0] == "url":
        url = header[1]
    else:
        url = f"file://{fname}"
        content = cleanup_text(full_content)
    metadatas = []
    texts = []
    ids = []
    n = 0
    for chunk in splitter.split_text(content):
        n = n + 1
        id = f"{basename}-{n:04d}.txt"
        oname = os.path.join(out_dir, "Chunk", id)
        metadata = {
            "url": url,
            "source": oname,
            "part": n,
            "main_source": fname,
        }
        metadatas.append(metadata)
        ids.append(id)
        texts.append(chunk)
        with open(oname, "w") as out_f:
            print(chunk, file=out_f)
        # set the timestamp to be the same
        stat = os.stat(fname)
        os.utime(oname, (stat.st_atime, stat.st_mtime))

    if len(texts) == 0:
        print(f"Unable to split doc {fname}", file=sys.stderr)
    else:
        print(f"Storing {len(texts)} chunks to the db for {url}", file=sys.stderr)
        res_ids = indexer.add_texts(texts, metadatas, ids=ids)
        print(f"ids={res_ids}", file=sys.stderr)


def main(in_dir: str, out_dir: str):
    print(f"Storing files under {out_dir}")
    splitter = get_splitter()
    indexer = get_vectorstore(out_dir)
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
