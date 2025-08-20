#!/usr/bin/env python3
"""
MCP Server using official MCP FastMCP implementation
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta
from typing import Annotated, Any, Dict, Optional

from dotenv import load_dotenv
from fastmcp import FastMCP

from lib import get_vectorstore

# Load environment variables
load_dotenv()

SRCDIR = os.getenv("SRCDIR", ".")
DSTDIR = os.getenv("DSTDIR", ".")
SBA_ORG_DOC = os.getenv("SBA_ORG_DOC", "SecondBrainOrganization.md")

# Initialize the server using official MCP FastMCP
server = FastMCP(
    name="Second Brain",
    instructions="""This server provides tools for interacting with personal notes and their associated documents and URLs.
                 """,
)


@server.tool()
async def search_documents(
    text: Annotated[
        str,
        "The text to find similar documents to. If the text is empty, the search is performed on the metadata only.",
    ] = "",
    limit: Annotated[int, "Maximum number of results to return (default: 10)"] = 10,
    filter_metadata: Annotated[
        Optional[Dict[str, Any]],
        """Optional metadata filters (e.g., {'type': 'history', 'domain': 'work'}).
Complex filers can be used on metadata fields:

        {"$and": [ { "type": { "$eq": "notes" } },
                   { "created_at": { $gt: 1685469600.0 } }
                 ]
        }
        """,
    ] = None,
) -> Dict[str, Any]:
    """
    Search for documents in the vector database using semantic similarity. The documents are split pieces if they contained an history and then each piece is split into chunks, and the search is performed on these chunks.

    Returns:
        Dictionary containing search results like: {"documents": [{"content": "...", "metadata": {...}, "similarity_score": 0.95}], "total_results": 5, "timestamp": "2023-10-01T12:00:00Z"}

        Example metadata: {'created_at': 1685469900.0, 'source': '~/.second-brain/Chunk/DciNotes20240406-0001.txt', 'last_accessed_at': 1712397600.0, 'part': 1, 'referer': 'DciNotes', 'url': 'file:///home/flepied/Wiki/DciNotes', 'type': 'history', 'main_source': '~/.second-brain//Text/DciNotes20240406.json'}

        similarity_score: float representing the similarity score of the document to the search text. Lower score represents more similarity.

        total_results: Total number of documents found matching the search criteria.

        Details of the metadata:
        - `created_at`: Timestamp when the document was created.
        - `source`: Path to the source chunk.
        - `last_accessed_at`: Timestamp when the document was last accessed.
        - `part`: Part number of the chunk.
        - `referer`: The referer document basename.
        - `url`: URL or file path to the document that was split into chunks.
        - `main_source`: Main piece of the document if there was an history.
        - `domain`: Domain of the document, e.g., 'work', 'personal', 'project'. the domains are described in the `SecondBrainOrganization.md` document.
        - `type`: Type of the document:
            - 'youtube' for YouTube videos transcripts
            - 'pdf' for PDF documents
            - 'audio' for audio files like podcast transcripts
            - 'history' for historical notes for projects
            - 'notes' for personal notes. That is the **main type** of document.
    """
    try:
        vectorstore = get_vectorstore()

        # Build search kwargs
        search_kwargs = {"k": limit}
        if filter_metadata:
            search_kwargs["filter"] = filter_metadata

        # Perform similarity search (using async method)
        results = await vectorstore.asimilarity_search_with_relevance_scores(
            text, **search_kwargs
        )

        # Format results
        documents = []
        for doc, score in results:
            documents.append(
                {
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "similarity_score": score,
                }
            )

        return {
            "results": results,
            "documents": documents,
            "total_results": len(documents),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:  # pylint: disable=broad-exception-caught
        return {
            "error": str(e),
            "query": text,
            "timestamp": datetime.now().isoformat(),
        }


@server.tool()
async def get_document_count(
    filter_metadata: Annotated[
        Optional[Dict[str, Any]],
        """Optional metadata filters (e.g., {'type': 'history', 'domain': 'work'}).
Complex filers can be used on metadata fields:

        {"$and": [ { "type": { "$eq": "notes" } },
                   { "created_at": { $gt: 1685469600.0 } }
                 ]
        }
        """,
    ] = None,
) -> Dict[str, Any]:
    """
    Get the total number of documents in the vector database.

    Returns:
        Dictionary containing the document count
    """
    vectorstore = get_vectorstore()
    res = vectorstore.get(where=filter_metadata, include=[])["ids"]
    return {
        "document_count": (len(res)),
        "timestamp": datetime.now().isoformat(),
    }


@server.tool()
async def get_domains() -> Dict[str, Any]:
    """
    Retrieve all the domains used in the documents

    Returns:
        a dictionary like: {"domains": ["Work", "Home", "Pkm"]}
    """
    try:
        vectorstore = get_vectorstore()

        results = await asyncio.to_thread(
            vectorstore.get,
            include=["metadatas"],
        )

        # Format results for similarity search
        domains = set()
        for metadata in results["metadatas"]:
            domain = metadata.get("domain")
            if domain:
                domains.add(domain)
        return {"domains": list(domains)}
    except Exception as e:  # pylint: disable=broad-exception-caught
        return {
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


@server.tool()
async def get_recent_documents(
    limit: Annotated[int, "Maximum number of results to return (default: 10)"] = 10,
    days: Annotated[
        int, "Number of days to look back for recent documents (default: 7)"
    ] = 7,
) -> Dict[str, Any]:
    """
    Get recently accessed documents from the vector database.

    Returns:
        Dictionary containing recent documents
    """
    try:
        vectorstore = get_vectorstore()

        # Calculate timestamp for filtering
        cutoff_time = datetime.now() - timedelta(days=days)
        cutoff_timestamp = cutoff_time.timestamp()

        # Get recent documents (using async method)
        all_docs = await vectorstore.aget_by_ids([])
        recent_docs = []

        for i, metadata in enumerate(all_docs["metadatas"]):
            if "last_accessed_at" in metadata:
                last_accessed = metadata["last_accessed_at"]
                if isinstance(last_accessed, str):
                    last_accessed = datetime.fromisoformat(last_accessed).timestamp()

                if last_accessed >= cutoff_timestamp:
                    recent_docs.append(
                        {
                            "content": all_docs["documents"][i],
                            "metadata": metadata,
                            "last_accessed": last_accessed,
                        }
                    )

        # Sort by last accessed time and limit results
        recent_docs.sort(key=lambda x: x["last_accessed"], reverse=True)
        recent_docs = recent_docs[:limit]

        return {
            "recent_documents": recent_docs,
            "total_results": len(recent_docs),
            "days_back": days,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:  # pylint: disable=broad-exception-caught
        return {
            "error": str(e),
            "days_back": days,
            "timestamp": datetime.now().isoformat(),
        }


if __name__ == "__main__":
    # Add some debugging
    print("Starting MCP server...", file=sys.stderr)
    print(f"Current working directory: {os.getcwd()}", file=sys.stderr)
    print(
        f"Environment variables: SRCDIR={os.getenv('SRCDIR', 'NOT SET')}, "
        f"DSTDIR={os.getenv('DSTDIR', 'NOT SET')}",
        file=sys.stderr,
    )

    # Run the server
    server.run()
