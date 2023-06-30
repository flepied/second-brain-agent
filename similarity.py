#!/usr/bin/env python

"""
Do a simple query through the vector database for a similarity search
"""

import os
import sys

from dotenv import load_dotenv

from lib import get_vectorstore


def main(out_dir, query):
    print(f"Getting data from {out_dir}", file=sys.stderr)
    vs = get_vectorstore(out_dir)
    results = vs.similarity_search_with_relevance_scores(query)
    for result in results:
        print(
            f"{result[0].metadata['source']}: {result[1]} ({result[0].metadata['url']})"
        )


if __name__ == "__main__":
    load_dotenv()
    main(os.environ["DSTDIR"], sys.argv[1])

# similarity.py ends here
