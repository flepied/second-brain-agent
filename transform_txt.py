#!/usr/bin/env python

"""
Transform txt files into chunks of text then transform the chunks
into vector embeddings and store the vectors in a vector database.
"""

import datetime
import json
import os
import sys

from dotenv import load_dotenv
from langchain.text_splitter import TokenTextSplitter

from lib import datetime_decoder, get_vectorstore, is_same_time

# limit chunk size to 1000 as we retrieve 4 documents by default and
# the token limit is 4096
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 50


def get_splitter():
    "Return text splitter"
    splitter = TokenTextSplitter(
        chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP, disallowed_special=()
    )
    return splitter


# pylint: disable=too-many-arguments
def process_chunk(chunk, metadata, fname, basename, number, out_dir):
    "Process a chunk of text"
    chunk_id = f"{basename}-{number:04d}.txt"
    oname = os.path.join(out_dir, "Chunk", chunk_id)
    chunk_metadata = metadata.copy()
    chunk_metadata["part"] = number
    chunk_metadata["source"] = oname
    chunk_metadata["main_source"] = fname
    if "referer" not in chunk_metadata:
        chunk_metadata["referer"] = basename
    with open(oname, "w", encoding="utf-8") as out_f:
        print(chunk, file=out_f)
    # set the timestamp to be the same
    stat = os.stat(fname)
    os.utime(oname, (stat.st_atime, stat.st_mtime))
    return chunk_metadata, chunk_id


def validate_and_extract_url(fname, basename, out_dir):
    "Validate that the file name is ending in .json and is not the same date as the first chunk"
    if not fname.endswith(".json"):
        print(f"Ignoring non json file {fname}", file=sys.stderr)
        return False, None
    oname = os.path.join(out_dir, "Chunk", basename + "-0001.txt")
    if is_same_time(fname, oname):
        return False, None
    with open(fname, encoding="utf-8") as in_stream:
        try:
            data = json.load(in_stream, object_hook=datetime_decoder)
        except json.JSONDecodeError as exc:
            print(f"Could not parse {fname}: {exc}", file=sys.stderr)
            return False, None
    if "metadata" not in data:
        print(f"Could not find metadata in {fname}", file=sys.stderr)
        return False, None
    metadata = data["metadata"]
    # convert the datetime to timestamp because chromadb does not
    # support datetime
    for key, val in metadata.items():
        # check if the value is a datetime
        if isinstance(val, datetime.datetime):
            metadata[key] = val.timestamp()
    return metadata, data["text"]


def remove_related_files(fname, indexer, out_dir):
    "Remove related files"
    basename = os.path.basename(fname).split(".")[0].split("-")[0]
    results = indexer.get(
        where={"$or": [{"main_source": {"$eq": fname}}, {"referer": {"$eq": basename}}]}
    )
    print(
        f"Removing {len(results['ids'])} related files to {fname}: {' '.join(results['ids'])}",
        file=sys.stderr,
    )
    if len(results["ids"]) > 0:
        indexer.delete(results["ids"])
        for chunk_id in results["ids"]:
            os.remove(os.path.join(out_dir, "Chunk", chunk_id))


def process_file(fname: str, out_dir: str, indexer, splitter):
    "Cut a text file in multiple chunks"
    basename = os.path.basename(fname[:-5])
    print(f"Processing '{fname}' '{basename}'", file=sys.stderr)
    if not os.path.exists(fname):
        print(f"File {fname} does not exist anymore", file=sys.stderr)
        remove_related_files(fname, indexer, out_dir)
        return
    metadata, content = validate_and_extract_url(fname, basename, out_dir)
    if metadata is False:
        return
    metadatas = []
    texts = []
    ids = []
    number = 0
    for chunk in splitter.split_text(content):
        number = number + 1
        chunk_metadata, chunck_id = process_chunk(
            chunk, metadata, fname, basename, number, out_dir
        )
        metadatas.append(chunk_metadata)
        ids.append(chunck_id)
        texts.append(chunk)

    if len(texts) == 0:
        print(f"Unable to split doc {fname}", file=sys.stderr)
    else:
        print(f"Storing {len(texts)} chunks to the db for {metadata=}", file=sys.stderr)
        res_ids = indexer.add_texts(texts, metadatas, ids=ids)
        print(f"ids={res_ids}", file=sys.stderr)


def main(in_dir: str, out_dir: str):
    "Entry point"
    print(f"Storing files under {out_dir}")
    splitter = get_splitter()
    indexer = get_vectorstore()
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
