#!/usr/bin/env python3

"""CLI helper to query the Second Brain MCP server."""

from __future__ import annotations

import argparse
import asyncio
import json
from typing import Any, Dict, Optional, Sequence

from dotenv import load_dotenv
from fastmcp import Client

from mcp_server import server


def parse_tool_payload(result: Any) -> Dict[str, Any]:
    """Extract the JSON payload from a FastMCP tool result."""
    if hasattr(result, "is_error"):
        if result.is_error:  # type: ignore[unreachable]
            raise RuntimeError(getattr(result, "error", "MCP tool returned an error"))
        content = getattr(result, "content", [])
        if content:
            return json.loads(content[0].text)
        return {}
    if isinstance(result, list) and result:
        return json.loads(result[0].text)
    if isinstance(result, dict):
        return result
    raise ValueError("Unexpected MCP response format")


def format_documents(documents: Sequence[Dict[str, Any]]) -> str:
    """Format a list of MCP documents for terminal display."""
    if not documents:
        return "No documents found."
    lines = []
    for idx, doc in enumerate(documents, start=1):
        content = doc.get("content", "").strip().replace("\n", " ")
        snippet = content[:200] + ("..." if len(content) > 200 else "")
        metadata = doc.get("metadata", {})
        source = metadata.get("source") or metadata.get("url") or "unknown"
        lines.append(f"{idx}. {snippet}\n   Source: {source}")
    return "\n".join(lines)


def parse_filter(filter_str: Optional[str]) -> Optional[Dict[str, Any]]:
    """Parse a metadata filter provided as JSON on the CLI."""
    if filter_str is None:
        return None
    try:
        decoded = json.loads(filter_str)
    except json.JSONDecodeError as exc:
        msg = f"Invalid filter JSON: {exc}"
        raise ValueError(msg) from exc
    if not isinstance(decoded, dict):
        msg = "Filter must decode to a JSON object"
        raise ValueError(msg)
    return decoded


async def fetch_documents(
    question: str, limit: int, filter_metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Call the MCP `search_documents` tool and return the parsed payload."""
    async with Client(server) as client:
        payload: Dict[str, Any] = {"text": question, "limit": limit}
        if filter_metadata:
            payload["filter_metadata"] = filter_metadata
        result = await client.call_tool("search_documents", payload)
        return parse_tool_payload(result)


def main() -> None:
    """Entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description="Query the Second Brain MCP server for relevant documents."
    )
    parser.add_argument(
        "question",
        help="Free-form question to search your second brain.",
    )
    parser.add_argument(
        "-k",
        "--limit",
        type=int,
        default=5,
        help="Maximum number of documents to return (default: 5).",
    )
    parser.add_argument(
        "-f",
        "--filter",
        dest="filter_metadata",
        help=(
            "Optional JSON metadata filter passed to the MCP search_documents tool. "
            'Example: \'{"type": {"$eq": "history"}}\''
        ),
    )
    args = parser.parse_args()
    load_dotenv()
    metadata_filter = parse_filter(args.filter_metadata)
    payload = asyncio.run(fetch_documents(args.question, args.limit, metadata_filter))
    print(format_documents(payload.get("documents", [])))


if __name__ == "__main__":
    main()
