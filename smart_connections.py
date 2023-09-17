#!/usr/bin/env python

"""
Find similar notes in the vectorstore.
"""

import os
import sys

from dotenv import load_dotenv

from lib import get_vectorstore, is_history_filename


def basename(fname):
    "Get the basename of a filename with its extension."
    return os.path.basename(fname).split(".")[0]


def url_to_fname(url):
    "Convert a URL to a filename."
    return url.replace("file://", "")


def has_reference(fname1, fname2):
    "Check if two files have a reference to each other."
    try:
        with open(url_to_fname(fname1), encoding="UTF-8") as fptr:
            content1 = fptr.read()
        with open(url_to_fname(fname2), encoding="UTF-8") as fptr:
            content2 = fptr.read()
        return basename(fname1) in content2 or basename(fname2) in content1
    except UnicodeDecodeError as exc:
        print(f"UnicodeDecodeError: {exc}", file=sys.stderr)
        return False


def find_similar_docs(results, metadatas, idx, base_doc_id):
    "Find similar documents."
    doc_name = os.path.basename(metadatas[idx]["url"])
    similar_ids = results["ids"][0]
    similar_metadatas = results["metadatas"][0]
    similar_distances = results["distances"][0]
    similar_docs = []
    for doc_idx, doc_id in enumerate(similar_ids):
        if base_doc_id != doc_id and similar_distances[doc_idx] < 0.8:
            simillar_doc_name = os.path.basename(similar_metadatas[doc_idx]["url"])
            try:
                if simillar_doc_name != doc_name and not has_reference(
                    similar_metadatas[doc_idx]["url"], metadatas[idx]["url"]
                ):
                    similar_docs.append(simillar_doc_name)
            except FileNotFoundError:
                print(
                    f"File not found: {similar_metadatas[doc_idx]['source']} "
                    f"{metadatas[idx]['source']}",
                    file=sys.stderr,
                )
    nb_connections = len(similar_docs)
    if nb_connections > 0:
        docs_str = ", ".join(similar_docs)
        print(f"Found {nb_connections} similar documents for {doc_name}: {docs_str}")


def main():
    "Entry point"
    vector_store = get_vectorstore()._collection  # pylint: disable=protected-access
    results = vector_store.get(
        where={"type": {"$eq": "notes"}}, include=["embeddings", "metadatas"]
    )
    embeddings = results["embeddings"]
    metadatas = results["metadatas"]
    nb_embeddings = len(embeddings)
    ids = results["ids"]
    nb_ids = len(ids)
    print(f"Found {nb_ids} {nb_embeddings} documents.")
    assert nb_ids == nb_embeddings
    for idx in range(nb_embeddings):
        embed = embeddings[idx]
        doc_id = ids[idx]
        if is_history_filename(doc_id):
            continue
        results = vector_store.query(
            query_embeddings=embed,
            include=["metadatas", "distances"],
            where={"type": {"$eq": "notes"}},
        )
        if len(results) > 1:
            find_similar_docs(results, metadatas, idx, doc_id)
        else:
            print(f"Found no similar documents for {doc_id}.")


if __name__ == "__main__":
    load_dotenv()
    main()

# smart-connections.py ends here
