#!/usr/bin/env python

"""
Do a simple query through the vector database for a similarity search
"""

import sys

from dotenv import load_dotenv

from lib import get_vectorstore


def main(query, **kwargs):
    "Entry point"
    vector_store = get_vectorstore()
    results = vector_store.similarity_search_with_relevance_scores(query, **kwargs)
    for result in results:
        print(f"{result[0].metadata['source']}: {result[1]} ({result[0].metadata})")


if __name__ == "__main__":
    load_dotenv()
    args = [arg.split("=", 1) for arg in sys.argv[2:]]
    main(sys.argv[1], filter=dict(args))

# similarity.py ends here
