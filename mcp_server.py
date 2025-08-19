#!/usr/bin/env python3
"""
MCP Server for Second Brain Agent

This server provides tools to interact with the vector database and document retrieval
system without interfacing at the reasoning level.
"""

from datetime import datetime, timedelta
from typing import Annotated, Any, Dict, Optional

from dotenv import load_dotenv
from fastmcp import FastMCP

from lib import Agent, get_vectorstore

# Load environment variables
load_dotenv()

# Initialize the server
server = FastMCP("second-brain-agent")


@server.tool()
async def query_vector_database(
    query: Annotated[str, "The question to ask about your documents"],
    include_sources: Annotated[
        bool, "Whether to include source documents in the response"
    ] = False,
) -> Dict[str, Any]:
    """
    Query the vector database with a question and return the answer.

    Returns:
        Dictionary containing the answer and optionally sources
    """
    try:
        # Use the Agent class which properly handles the LLM
        agent = Agent()

        result = agent.question(f"From the document, {query}")
        response = {
            "answer": result,
            "query": query,
            "timestamp": datetime.now().isoformat(),
        }

        if include_sources:
            # Add sources information if requested
            response["include_sources"] = True
            # Note: The Agent.question method already includes sources in the result

        return response
    except Exception as e:  # pylint: disable=broad-exception-caught
        return {
            "error": str(e),
            "query": query,
            "timestamp": datetime.now().isoformat(),
        }


@server.tool()
async def search_documents(
    query: Annotated[str, "The search query to find relevant documents"],
    limit: Annotated[int, "Maximum number of results to return (default: 10)"] = 10,
    filter_metadata: Annotated[
        Optional[Dict[str, Any]],
        "Optional metadata filters (e.g., {'type': 'history', 'domain': 'work'})",
    ] = None,
) -> Dict[str, Any]:
    """
    Search for documents in the vector database using semantic similarity.

    Returns:
        Dictionary containing search results with documents and metadata
    """
    try:
        vectorstore = get_vectorstore()

        # Build search kwargs
        search_kwargs = {"k": limit}
        if filter_metadata:
            search_kwargs["filter"] = filter_metadata

        # Perform similarity search
        results = vectorstore.similarity_search_with_relevance_scores(
            query, **search_kwargs
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
            "query": query,
            "documents": documents,
            "total_results": len(documents),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:  # pylint: disable=broad-exception-caught
        return {
            "error": str(e),
            "query": query,
            "timestamp": datetime.now().isoformat(),
        }


@server.tool()
async def get_document_count() -> Dict[str, Any]:
    """
    Get the total number of documents in the vector database.

    Returns:
        Dictionary containing the document count
    """
    try:
        vectorstore = get_vectorstore()
        # Get all documents to count them
        all_docs = vectorstore.get()
        count = len(all_docs["documents"])

        return {"document_count": count, "timestamp": datetime.now().isoformat()}
    except Exception as e:  # pylint: disable=broad-exception-caught
        return {"error": str(e), "timestamp": datetime.now().isoformat()}


@server.tool()
async def get_document_metadata(
    document_id: Annotated[
        str, "The unique identifier of the document to retrieve metadata for"
    ]
) -> Dict[str, Any]:
    """
    Get metadata for a specific document by ID.

    Returns:
        Dictionary containing document metadata
    """
    try:
        vectorstore = get_vectorstore()

        # Get document by ID
        result = vectorstore.get(ids=[document_id])

        if not result["documents"]:
            return {
                "error": f"Document with ID {document_id} not found",
                "document_id": document_id,
                "timestamp": datetime.now().isoformat(),
            }

        return {
            "document_id": document_id,
            "metadata": result["metadatas"][0],
            "content": result["documents"][0],
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:  # pylint: disable=broad-exception-caught
        return {
            "error": str(e),
            "document_id": document_id,
            "timestamp": datetime.now().isoformat(),
        }


@server.tool()
async def list_domains() -> Dict[str, Any]:
    """
    List all available domains in the vector database.

    Returns:
        Dictionary containing list of domains
    """
    try:
        vectorstore = get_vectorstore()

        # Get all documents to extract unique domains
        all_docs = vectorstore.get()
        domains = set()

        for metadata in all_docs["metadatas"]:
            if "domain" in metadata:
                domains.add(metadata["domain"])

        return {
            "domains": sorted(list(domains)),
            "total_domains": len(domains),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:  # pylint: disable=broad-exception-caught
        return {"error": str(e), "timestamp": datetime.now().isoformat()}


@server.tool()
async def search_by_domain(
    domain: Annotated[
        str,
        "The domain to search in (e.g., 'work', 'personal', 'ArtificialIntelligence')",
    ],
    query: Annotated[
        str, "Optional search query (if empty, returns all documents in domain)"
    ] = "",
    limit: Annotated[int, "Maximum number of results to return (default: 10)"] = 10,
) -> Dict[str, Any]:
    """
    Search for documents within a specific domain.

    Returns:
        Dictionary containing search results for the domain
    """
    try:
        vectorstore = get_vectorstore()

        if query:
            # Search with query in specific domain
            results = vectorstore.similarity_search_with_relevance_scores(
                query, k=limit, filter={"domain": domain}
            )

            # Format results for similarity search
            documents = []
            for doc, score in results:
                documents.append(
                    {
                        "content": doc.page_content,
                        "metadata": doc.metadata,
                        "similarity_score": score,
                    }
                )
        else:
            # Get all documents in domain
            all_docs = vectorstore.get(where={"domain": domain})

            # Format results for direct retrieval
            documents = []
            for i, doc in enumerate(all_docs["documents"][:limit]):
                documents.append(
                    {
                        "content": doc,
                        "metadata": all_docs["metadatas"][i],
                        "similarity_score": 1.0,  # No relevance score for direct retrieval
                    }
                )

        return {
            "domain": domain,
            "query": query,
            "documents": documents,
            "total_results": len(documents),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:  # pylint: disable=broad-exception-caught
        return {
            "error": str(e),
            "domain": domain,
            "query": query,
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

        # Get recent documents
        all_docs = vectorstore.get()
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
    # Run the server
    server.run()
