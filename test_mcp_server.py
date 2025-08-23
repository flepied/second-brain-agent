#!/usr/bin/env python3
"""
Test script for the MCP server

This script tests the MCP server functionality using the proper MCP client pattern.
"""

import asyncio
import json
import os
import sys

import pytest
from dotenv import load_dotenv
from fastmcp import Client

# Add the current directory to the path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp_server import server


def parse_tool_result(result):
    """Parse the result from call_tool which returns a list of TextContent objects"""
    if result.content and len(result.content) > 0:
        content_text = result.content[0].text
        return json.loads(content_text)
    pytest.fail("No content returned from tool")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mcp_server():
    """Test the MCP server functions using the proper client pattern.

    This test requires a running vector database and is marked as an integration test.
    It will be skipped during unit test runs (e.g., pre-commit) but can be run
    explicitly with: pytest -m integration

    To run only unit tests (excluding integration tests):
        pytest -m "not integration"

    To run only integration tests:
        pytest -m integration

    To run all tests:
        pytest
    """

    print("Testing MCP Server for Second Brain Agent")
    print("=" * 50)

    # Load environment variables
    load_dotenv()

    print("4. Testing get_domains...", end="")
    async with Client(server) as client:
        result = await client.call_tool("get_domains", {})
        assert not result.is_error

        parsed_result = parse_tool_result(result)
        print(f"{parsed_result=}")
        assert "domains" in parsed_result
        print(f" {len(parsed_result['domains'])} domains found. ✅")

    print("1. Testing search_documents...", end="")
    async with Client(server) as client:
        result = await client.call_tool("search_documents", {"text": "DCI", "limit": 3})
        assert not result.is_error

        parsed_result = parse_tool_result(result)
        assert "documents" in parsed_result
        print(f" {len(parsed_result['documents'])} documents found. ✅")

    print("2. Testing get_document_count...", end="")
    async with Client(server) as client:
        result = await client.call_tool("get_document_count", {})
        assert not result.is_error

        parsed_result = parse_tool_result(result)
        assert "document_count" in parsed_result
        print(f" {parsed_result['document_count']} documents found. ✅")

    print("3. Testing get_document_count with filter...", end="")
    async with Client(server) as client:
        result = await client.call_tool(
            "get_document_count", {"filter_metadata": {"domain": "Work"}}
        )
        assert not result.is_error

        parsed_result = parse_tool_result(result)
        assert "document_count" in parsed_result
        print(f" {parsed_result['document_count']} documents found. ✅")


if __name__ == "__main__":
    asyncio.run(test_mcp_server())
