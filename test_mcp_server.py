#!/usr/bin/env python3
"""
Test script for the MCP server

This script tests the MCP server functionality using the proper MCP client pattern.
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timedelta

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


@pytest.mark.integration
@pytest.mark.asyncio
async def test_basic_queries():
    """Test basic query examples from the docstring."""
    print("\nTesting Basic Queries...")
    print("=" * 30)

    async with Client(server) as client:
        # Test basic type filter
        print("1. Testing basic type filter...", end="")
        result = await client.call_tool(
            "search_documents",
            {"text": "", "limit": 5, "filter_metadata": {"type": "notes"}},
        )
        assert not result.is_error
        parsed_result = parse_tool_result(result)
        assert "documents" in parsed_result
        print(f" {len(parsed_result['documents'])} documents found. ✅")

        # Test basic domain filter
        print("2. Testing basic domain filter...", end="")
        result = await client.call_tool(
            "search_documents",
            {"text": "", "limit": 5, "filter_metadata": {"domain": "work"}},
        )
        assert not result.is_error
        parsed_result = parse_tool_result(result)
        assert "documents" in parsed_result
        print(f" {len(parsed_result['documents'])} documents found. ✅")

        # Test combined filters
        print("3. Testing combined filters...", end="")
        result = await client.call_tool(
            "search_documents",
            {
                "text": "",
                "limit": 5,
                "filter_metadata": {
                    "$and": [
                        {"type": {"$eq": "youtube"}},
                        {"domain": {"$eq": "personal"}},
                    ]
                },
            },
        )
        assert not result.is_error
        parsed_result = parse_tool_result(result)
        assert "documents" in parsed_result
        print(f" {len(parsed_result['documents'])} documents found. ✅")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_date_range_queries():
    """Test date range query examples from the docstring."""
    print("\nTesting Date Range Queries...")
    print("=" * 30)

    async with Client(server) as client:
        # Test documents created after specific timestamp
        print("1. Testing created_after filter...", end="")
        result = await client.call_tool(
            "search_documents",
            {
                "text": "",
                "limit": 5,
                "filter_metadata": {"created_at": {"$gt": 1685469600.0}},
            },
        )
        assert not result.is_error
        parsed_result = parse_tool_result(result)
        assert "documents" in parsed_result
        print(f" {len(parsed_result['documents'])} documents found. ✅")

        # Test documents created in last 30 days
        print("2. Testing last 30 days filter...", end="")
        thirty_days_ago = (datetime.now() - timedelta(days=30)).timestamp()
        result = await client.call_tool(
            "search_documents",
            {
                "text": "",
                "limit": 5,
                "filter_metadata": {"created_at": {"$gte": thirty_days_ago}},
            },
        )
        assert not result.is_error
        parsed_result = parse_tool_result(result)
        assert "documents" in parsed_result
        print(f" {len(parsed_result['documents'])} documents found. ✅")

        # Test date range with $and
        print("3. Testing date range with $and...", end="")
        result = await client.call_tool(
            "search_documents",
            {
                "text": "",
                "limit": 5,
                "filter_metadata": {
                    "$and": [
                        {"created_at": {"$gte": 1685469600.0}},
                        {"created_at": {"$lte": 1693152000.0}},
                    ]
                },
            },
        )
        assert not result.is_error
        parsed_result = parse_tool_result(result)
        assert "documents" in parsed_result
        print(f" {len(parsed_result['documents'])} documents found. ✅")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_multiple_type_filtering():
    """Test multiple type filtering examples from the docstring."""
    print("\nTesting Multiple Type Filtering...")
    print("=" * 30)

    async with Client(server) as client:
        # Test $or with multiple types
        print("1. Testing $or with multiple types...", end="")
        result = await client.call_tool(
            "search_documents",
            {
                "text": "",
                "limit": 5,
                "filter_metadata": {
                    "$or": [{"type": {"$eq": "notes"}}, {"type": {"$eq": "history"}}]
                },
            },
        )
        assert not result.is_error
        parsed_result = parse_tool_result(result)
        assert "documents" in parsed_result
        print(f" {len(parsed_result['documents'])} documents found. ✅")

        # Test $ne (not equal)
        print("2. Testing $ne (not equal)...", end="")
        result = await client.call_tool(
            "search_documents",
            {"text": "", "limit": 5, "filter_metadata": {"type": {"$ne": "audio"}}},
        )
        assert not result.is_error
        parsed_result = parse_tool_result(result)
        assert "documents" in parsed_result
        print(f" {len(parsed_result['documents'])} documents found. ✅")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_domain_and_type_combinations():
    """Test domain and type combination examples from the docstring."""
    print("\nTesting Domain and Type Combinations...")
    print("=" * 30)

    async with Client(server) as client:
        # Test work-related notes created recently
        print("1. Testing work notes created recently...", end="")
        result = await client.call_tool(
            "search_documents",
            {
                "text": "",
                "limit": 5,
                "filter_metadata": {
                    "$and": [
                        {"domain": {"$eq": "work"}},
                        {"type": {"$eq": "notes"}},
                        {"created_at": {"$gt": 1685469600.0}},
                    ]
                },
            },
        )
        assert not result.is_error
        parsed_result = parse_tool_result(result)
        assert "documents" in parsed_result
        print(f" {len(parsed_result['documents'])} documents found. ✅")

        # Test personal YouTube videos or PDFs
        print("2. Testing personal YouTube videos or PDFs...", end="")
        result = await client.call_tool(
            "search_documents",
            {
                "text": "",
                "limit": 5,
                "filter_metadata": {
                    "$and": [
                        {"domain": {"$eq": "personal"}},
                        {
                            "$or": [
                                {"type": {"$eq": "youtube"}},
                                {"type": {"$eq": "pdf"}},
                            ]
                        },
                    ]
                },
            },
        )
        assert not result.is_error
        parsed_result = parse_tool_result(result)
        assert "documents" in parsed_result
        print(f" {len(parsed_result['documents'])} documents found. ✅")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_referer_and_source_filtering():
    """Test referer and source filtering examples from the docstring."""
    print("\nTesting Referer and Source Filtering...")
    print("=" * 30)

    async with Client(server) as client:
        # Test specific referer
        print("1. Testing specific referer...", end="")
        result = await client.call_tool(
            "search_documents",
            {
                "text": "",
                "limit": 5,
                "filter_metadata": {"referer": {"$eq": "DciNotes"}},
            },
        )
        assert not result.is_error
        parsed_result = parse_tool_result(result)
        assert "documents" in parsed_result
        print(f" {len(parsed_result['documents'])} documents found. ✅")

        # Test multiple referers with $in
        print("2. Testing multiple referers with $in...", end="")
        result = await client.call_tool(
            "search_documents",
            {
                "text": "",
                "limit": 5,
                "filter_metadata": {
                    "referer": {"$in": ["DciNotes", "ProjectNotes", "MeetingNotes"]}
                },
            },
        )
        assert not result.is_error
        parsed_result = parse_tool_result(result)
        assert "documents" in parsed_result
        print(f" {len(parsed_result['documents'])} documents found. ✅")

        # Test source pattern with exact match (regex not supported)
        print("3. Testing source pattern with exact match...", end="")
        result = await client.call_tool(
            "search_documents",
            {
                "text": "",
                "limit": 5,
                "filter_metadata": {
                    "source": {
                        "$eq": "/home/flepied/.second-brain/Chunk/DciNotes20240406-0001.txt"
                    }
                },
            },
        )
        assert not result.is_error
        parsed_result = parse_tool_result(result)
        assert "documents" in parsed_result
        print(f" {len(parsed_result['documents'])} documents found. ✅")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_part_and_chunk_filtering():
    """Test part and chunk filtering examples from the docstring."""
    print("\nTesting Part and Chunk Filtering...")
    print("=" * 30)

    async with Client(server) as client:
        # Test first part of multi-part documents
        print("1. Testing first part filter...", end="")
        result = await client.call_tool(
            "search_documents",
            {"text": "", "limit": 5, "filter_metadata": {"part": {"$eq": 1}}},
        )
        assert not result.is_error
        parsed_result = parse_tool_result(result)
        assert "documents" in parsed_result
        print(f" {len(parsed_result['documents'])} documents found. ✅")

        # Test documents with multiple parts (not first part)
        print("2. Testing multiple parts filter...", end="")
        result = await client.call_tool(
            "search_documents",
            {"text": "", "limit": 5, "filter_metadata": {"part": {"$gt": 1}}},
        )
        assert not result.is_error
        parsed_result = parse_tool_result(result)
        assert "documents" in parsed_result
        print(f" {len(parsed_result['documents'])} documents found. ✅")

        # Test specific part range
        print("3. Testing specific part range...", end="")
        result = await client.call_tool(
            "search_documents",
            {
                "text": "",
                "limit": 5,
                "filter_metadata": {
                    "$and": [{"part": {"$gte": 2}}, {"part": {"$lte": 5}}]
                },
            },
        )
        assert not result.is_error
        parsed_result = parse_tool_result(result)
        assert "documents" in parsed_result
        print(f" {len(parsed_result['documents'])} documents found. ✅")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_last_accessed_time_filtering():
    """Test last accessed time filtering examples from the docstring."""
    print("\nTesting Last Accessed Time Filtering...")
    print("=" * 30)

    async with Client(server) as client:
        # Test recently accessed documents (last 7 days)
        print("1. Testing recently accessed documents...", end="")
        seven_days_ago = (datetime.now() - timedelta(days=7)).timestamp()
        result = await client.call_tool(
            "search_documents",
            {
                "text": "",
                "limit": 5,
                "filter_metadata": {"last_accessed_at": {"$gte": seven_days_ago}},
            },
        )
        assert not result.is_error
        parsed_result = parse_tool_result(result)
        assert "documents" in parsed_result
        print(f" {len(parsed_result['documents'])} documents found. ✅")

        # Test documents accessed more than 30 days ago
        print("2. Testing documents accessed >30 days ago...", end="")
        thirty_days_ago = (datetime.now() - timedelta(days=30)).timestamp()
        result = await client.call_tool(
            "search_documents",
            {
                "text": "",
                "limit": 5,
                "filter_metadata": {"last_accessed_at": {"$lt": thirty_days_ago}},
            },
        )
        assert not result.is_error
        parsed_result = parse_tool_result(result)
        assert "documents" in parsed_result
        print(f" {len(parsed_result['documents'])} documents found. ✅")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_url_and_main_source_filtering():
    """Test URL and main source filtering examples from the docstring."""
    print("\nTesting URL and Main Source Filtering...")
    print("=" * 30)

    async with Client(server) as client:
        # Test URL pattern with exact match (regex not supported)
        print("1. Testing URL pattern with exact match...", end="")
        result = await client.call_tool(
            "search_documents",
            {
                "text": "",
                "limit": 5,
                "filter_metadata": {
                    "url": {"$eq": "https://github.com/hieblmi/go-host-lnaddr"}
                },
            },
        )
        assert not result.is_error
        parsed_result = parse_tool_result(result)
        assert "documents" in parsed_result
        print(f" {len(parsed_result['documents'])} documents found. ✅")

        # Test documents with specific main source (exists not supported)
        print("2. Testing documents with specific main source...", end="")
        result = await client.call_tool(
            "search_documents",
            {
                "text": "",
                "limit": 5,
                "filter_metadata": {
                    "main_source": {
                        "$eq": "/home/flepied/.second-brain/Text/DciNotes20240406.json"
                    }
                },
            },
        )
        assert not result.is_error
        parsed_result = parse_tool_result(result)
        assert "documents" in parsed_result
        print(f" {len(parsed_result['documents'])} documents found. ✅")

        # Test documents with different main source
        print("3. Testing documents with different main source...", end="")
        result = await client.call_tool(
            "search_documents",
            {
                "text": "",
                "limit": 5,
                "filter_metadata": {
                    "main_source": {
                        "$ne": "/home/flepied/.second-brain/Text/DciNotes20240406.json"
                    }
                },
            },
        )
        assert not result.is_error
        parsed_result = parse_tool_result(result)
        assert "documents" in parsed_result
        print(f" {len(parsed_result['documents'])} documents found. ✅")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_complex_nested_queries():
    """Test complex nested query examples from the docstring."""
    print("\nTesting Complex Nested Queries...")
    print("=" * 30)

    async with Client(server) as client:
        # Test work notes created in last 30 days OR personal YouTube videos
        print("1. Testing complex $or with nested $and...", end="")
        thirty_days_ago = (datetime.now() - timedelta(days=30)).timestamp()
        result = await client.call_tool(
            "search_documents",
            {
                "text": "",
                "limit": 5,
                "filter_metadata": {
                    "$or": [
                        {
                            "$and": [
                                {"domain": {"$eq": "work"}},
                                {"type": {"$eq": "notes"}},
                                {"created_at": {"$gte": thirty_days_ago}},
                            ]
                        },
                        {
                            "$and": [
                                {"domain": {"$eq": "personal"}},
                                {"type": {"$eq": "youtube"}},
                            ]
                        },
                    ]
                },
            },
        )
        assert not result.is_error
        parsed_result = parse_tool_result(result)
        assert "documents" in parsed_result
        print(f" {len(parsed_result['documents'])} documents found. ✅")

        # Test documents with specific referer pattern AND created recently
        print("2. Testing complex $and with nested $or...", end="")
        result = await client.call_tool(
            "search_documents",
            {
                "text": "",
                "limit": 5,
                "filter_metadata": {
                    "$and": [
                        {"referer": {"$eq": "OpenSourceStategyProject"}},
                        {"created_at": {"$gte": 1685469600.0}},
                        {
                            "$or": [
                                {"type": {"$eq": "notes"}},
                                {"type": {"$eq": "history"}},
                            ]
                        },
                    ]
                },
            },
        )
        assert not result.is_error
        parsed_result = parse_tool_result(result)
        assert "documents" in parsed_result
        print(f" {len(parsed_result['documents'])} documents found. ✅")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_practical_use_cases():
    """Test practical use case examples from the docstring."""
    print("\nTesting Practical Use Cases...")
    print("=" * 30)

    async with Client(server) as client:
        # Test finding recent work notes
        print("1. Testing recent work notes...", end="")
        seven_days_ago = (datetime.now() - timedelta(days=7)).timestamp()
        result = await client.call_tool(
            "search_documents",
            {
                "text": "",
                "limit": 5,
                "filter_metadata": {
                    "$and": [
                        {"domain": "work"},
                        {"type": "notes"},
                        {"created_at": {"$gte": seven_days_ago}},
                    ]
                },
            },
        )
        assert not result.is_error
        parsed_result = parse_tool_result(result)
        assert "documents" in parsed_result
        print(f" {len(parsed_result['documents'])} documents found. ✅")

        # Test project documentation search
        print("2. Testing project documentation search...", end="")
        result = await client.call_tool(
            "search_documents",
            {
                "text": "",
                "limit": 5,
                "filter_metadata": {
                    "$and": [
                        {"referer": {"$eq": "OpenSourceStategyProject"}},
                        {"$or": [{"type": "notes"}, {"type": "history"}]},
                    ]
                },
            },
        )
        assert not result.is_error
        parsed_result = parse_tool_result(result)
        assert "documents" in parsed_result
        print(f" {len(parsed_result['documents'])} documents found. ✅")

        # Test learning materials search
        print("3. Testing learning materials search...", end="")
        result = await client.call_tool(
            "search_documents",
            {
                "text": "",
                "limit": 5,
                "filter_metadata": {
                    "$or": [{"type": "youtube"}, {"type": "pdf"}, {"type": "audio"}]
                },
            },
        )
        assert not result.is_error
        parsed_result = parse_tool_result(result)
        assert "documents" in parsed_result
        print(f" {len(parsed_result['documents'])} documents found. ✅")

        # Test multi-part documents
        print("4. Testing multi-part documents...", end="")
        result = await client.call_tool(
            "search_documents",
            {"text": "", "limit": 5, "filter_metadata": {"part": {"$gt": 1}}},
        )
        assert not result.is_error
        parsed_result = parse_tool_result(result)
        assert "documents" in parsed_result
        print(f" {len(parsed_result['documents'])} documents found. ✅")

        # Test GitHub-related documents
        print("5. Testing GitHub-related documents...", end="")
        result = await client.call_tool(
            "search_documents",
            {
                "text": "",
                "limit": 5,
                "filter_metadata": {
                    "url": {"$eq": "https://github.com/hieblmi/go-host-lnaddr"}
                },
            },
        )
        assert not result.is_error
        parsed_result = parse_tool_result(result)
        assert "documents" in parsed_result
        print(f" {len(parsed_result['documents'])} documents found. ✅")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_content_filtering():
    """Test content filtering functionality."""
    print("\nTesting Content Filtering...")
    print("=" * 30)

    async with Client(server) as client:
        # Test $contains
        print("1. Testing $contains...", end="")
        result = await client.call_tool(
            "search_documents",
            {"text": "", "limit": 5, "filter_content": {"$contains": "github"}},
        )
        assert not result.is_error
        parsed_result = parse_tool_result(result)
        assert "documents" in parsed_result
        print(f" {len(parsed_result['documents'])} documents found. ✅")

        # Test $not_contains
        print("2. Testing $not_contains...", end="")
        result = await client.call_tool(
            "search_documents",
            {"text": "", "limit": 5, "filter_content": {"$not_contains": "test"}},
        )
        assert not result.is_error
        parsed_result = parse_tool_result(result)
        assert "documents" in parsed_result
        print(f" {len(parsed_result['documents'])} documents found. ✅")

        # Test $regex
        print("3. Testing $regex...", end="")
        result = await client.call_tool(
            "search_documents",
            {"text": "", "limit": 5, "filter_content": {"$regex": "(?i)python"}},
        )
        assert not result.is_error
        parsed_result = parse_tool_result(result)
        assert "documents" in parsed_result
        print(f" {len(parsed_result['documents'])} documents found. ✅")

        # Test combined metadata and content filtering
        print("4. Testing combined filtering...", end="")
        result = await client.call_tool(
            "search_documents",
            {
                "text": "",
                "limit": 5,
                "filter_metadata": {"type": {"$eq": "notes"}},
                "filter_content": {"$contains": "python"},
            },
        )
        assert not result.is_error
        parsed_result = parse_tool_result(result)
        assert "documents" in parsed_result
        print(f" {len(parsed_result['documents'])} documents found. ✅")

        # Test complex content filtering
        print("5. Testing complex content filtering...", end="")
        result = await client.call_tool(
            "search_documents",
            {
                "text": "",
                "limit": 5,
                "filter_content": {
                    "$and": [{"$contains": "python"}, {"$not_contains": "test"}]
                },
            },
        )
        assert not result.is_error
        parsed_result = parse_tool_result(result)
        assert "documents" in parsed_result
        print(f" {len(parsed_result['documents'])} documents found. ✅")


if __name__ == "__main__":
    asyncio.run(test_mcp_server())
