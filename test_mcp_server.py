#!/usr/bin/env python3
"""
Test script for the MCP server

This script tests the MCP server functionality using the proper MCP client pattern.
"""

import asyncio
import json
import os
import sys

from dotenv import load_dotenv

# Add the current directory to the path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp_server import server


def parse_tool_result(result):
    """Parse the result from call_tool which returns a list of TextContent objects"""
    if isinstance(result, list) and len(result) > 0:
        # Extract the text content and parse as JSON
        text_content = result[0].text
        return json.loads(text_content)
    return result


import pytest


@pytest.mark.asyncio
async def test_mcp_server():
    """Test the MCP server functions using the proper client pattern"""

    print("Testing MCP Server for Second Brain Agent")
    print("=" * 50)

    # Load environment variables
    load_dotenv()

    # Test 1: Get document count
    print("\n1. Testing get_document_count...")
    try:
        result = await server.call_tool("get_document_count", {})
        parsed_result = parse_tool_result(result)
        print(f"✅ Document count: {parsed_result.get('document_count', 'N/A')}")
        if "error" in parsed_result:
            print(f"❌ Error: {parsed_result['error']}")
    except Exception as e:
        print(f"❌ Exception: {e}")

    # Test 2: List domains
    print("\n2. Testing list_domains...")
    try:
        result = await server.call_tool("list_domains", {})
        parsed_result = parse_tool_result(result)
        if "domains" in parsed_result:
            print(f"✅ Domains found: {len(parsed_result['domains'])}")
            print(
                f"   Domains: {', '.join(parsed_result['domains'][:5])}{'...' if len(parsed_result['domains']) > 5 else ''}"
            )
        if "error" in parsed_result:
            print(f"❌ Error: {parsed_result['error']}")
    except Exception as e:
        print(f"❌ Exception: {e}")

    # Test 3: Simple query
    print("\n3. Testing query_vector_database...")
    try:
        result = await server.call_tool(
            "query_vector_database",
            {"query": "What is this about?", "include_sources": False},
        )
        parsed_result = parse_tool_result(result)
        if "answer" in parsed_result:
            print(f"✅ Query successful")
            print(f"   Answer preview: {parsed_result['answer'][:100]}...")
        if "error" in parsed_result:
            print(f"❌ Error: {parsed_result['error']}")
    except Exception as e:
        print(f"❌ Exception: {e}")

    # Test 4: Search documents
    print("\n4. Testing search_documents...")
    try:
        result = await server.call_tool(
            "search_documents", {"query": "test", "limit": 3}
        )
        parsed_result = parse_tool_result(result)
        if "documents" in parsed_result:
            print(
                f"✅ Search successful: {len(parsed_result['documents'])} documents found"
            )
            if parsed_result["documents"]:
                print(
                    f"   First document preview: {parsed_result['documents'][0]['content'][:100]}..."
                )
        if "error" in parsed_result:
            print(f"❌ Error: {parsed_result['error']}")
    except Exception as e:
        print(f"❌ Exception: {e}")

    # Test 5: Get recent documents
    print("\n5. Testing get_recent_documents...")
    try:
        result = await server.call_tool(
            "get_recent_documents", {"limit": 3, "days": 30}
        )
        parsed_result = parse_tool_result(result)
        if "recent_documents" in parsed_result:
            print(f"✅ Recent documents: {len(parsed_result['recent_documents'])} found")
        if "error" in parsed_result:
            print(f"❌ Error: {parsed_result['error']}")
    except Exception as e:
        print(f"❌ Exception: {e}")

    print("\n" + "=" * 50)
    print("MCP Server testing completed!")


if __name__ == "__main__":
    asyncio.run(test_mcp_server())
