#!/usr/bin/env python

"""
Do a simple query through the vector database for a similarity search
"""

import sys

from dotenv import load_dotenv

from lib import get_vectorstore


def split_filter(args):
    "Split the filter arguments into an and query for chromadb"
    if len(args) == 0:
        return {}
    if len(args) == 1:
        return dict([args[0].split("=", 1)])
    return {"$and": [{arg.split("=", 1)[0]: arg.split("=", 1)[1]} for arg in args]}


def main(query, **kwargs):
    "Entry point"
    vector_store = get_vectorstore()
    results = vector_store.similarity_search_with_relevance_scores(query, **kwargs)
    for result in results:
        print(f"{result[0].metadata['source']}: {result[1]} ({result[0].metadata})")


if __name__ == "__main__":
    load_dotenv()
    filters = split_filter(sys.argv[2:])
    print(f"Searching for {sys.argv[1]} with filters {filters}", file=sys.stderr)
    main(sys.argv[1], filter=filters)

# similarity.py ends here
