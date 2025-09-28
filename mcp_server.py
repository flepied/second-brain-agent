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
        """Optional metadata filters for complex document queries.

**USAGE EXAMPLES:**
- To find YouTube videos: `{"type": "youtube"}`
- To find YouTube videos from 2025: `{"$and": [{"type": {"$eq": "youtube"}}, {"last_accessed_at": {"$gte": 1735689600.0}}]}`
- To find all documents: `{}` (empty dict) or omit this parameter
- To find work notes: `{"type": "notes", "domain": "work"}`

**Basic Examples:**
- `{'type': 'notes'}` - Find all personal notes (shorthand for `{'type': {'$eq': 'notes'}}`)
- `{'domain': 'work'}` - Find all work-related documents
- `{'type': 'youtube', 'domain': 'personal'}` - Find YouTube videos in personal domain (requires `$and` for multiple conditions)

**Complex Query Examples:**

1. **Date Range Queries:**
   ```python
   # Documents created after a specific timestamp
   {"created_at": {"$gt": 1685469600.0}}

   # Documents created in the last 30 days
   {"created_at": {"$gte": (datetime.now() - timedelta(days=30)).timestamp()}}

   # Documents created between two dates
   {"$and": [
       {"created_at": {"$gte": 1685469600.0}},
       {"created_at": {"$lte": 1693152000.0}}
   ]}
   ```

2. **Multiple Type Filtering:**
   ```python
   # Find notes OR history documents
   {"$or": [
       {"type": {"$eq": "notes"}},
       {"type": {"$eq": "history"}}
   ]}

   # Find all document types except audio
   {"type": {"$ne": "audio"}}
   ```

3. **Domain and Type Combinations:**
   ```python
   # Work-related notes created recently
   {"$and": [
       {"domain": {"$eq": "work"}},
       {"type": {"$eq": "notes"}},
       {"created_at": {"$gt": 1685469600.0}}
   ]}

   # Personal YouTube videos or PDFs
   {"$and": [
       {"domain": {"$eq": "personal"}},
       {"$or": [
           {"type": {"$eq": "youtube"}},
           {"type": {"$eq": "pdf"}}
       ]}
   ]}
   ```

4. **Referer and Source Filtering:**
   ```python
   # Documents from a specific referer
   {"referer": {"$eq": "DciNotes"}}

   # Documents from multiple referers
   {"referer": {"$in": ["DciNotes", "ProjectNotes", "MeetingNotes"]}}

   # Documents with specific source pattern (use exact match instead of regex)
   {"source": {"$eq": "/home/flepied/.second-brain/Chunk/DciNotes20240406-0001.txt"}}
   ```

5. **Part and Chunk Filtering:**
   ```python
   # First part of multi-part documents
   {"part": {"$eq": 1}}

   # Documents with multiple parts (not first part)
   {"part": {"$gt": 1}}

   # Specific part range
   {"$and": [
       {"part": {"$gte": 2}},
       {"part": {"$lte": 5}}
   ]}
   ```

6. **Last Accessed Time Filtering:**
   ```python
   # Recently accessed documents (last 7 days)
   {"last_accessed_at": {"$gte": (datetime.now() - timedelta(days=7)).timestamp()}}

   # Documents accessed more than 30 days ago
   {"last_accessed_at": {"$lt": (datetime.now() - timedelta(days=30)).timestamp()}}
   ```

7. **URL and Main Source Filtering:**
   ```python
   # Documents from specific URL pattern (use exact match instead of regex)
   {"url": {"$eq": "https://github.com/hieblmi/go-host-lnaddr"}}

   # Documents with specific main source (use exact match instead of exists)
   {"main_source": {"$eq": "/home/flepied/.second-brain/Text/DciNotes20240406.json"}}

   # Documents with different main source (use not equal instead of exists false)
   {"main_source": {"$ne": "/home/flepied/.second-brain/Text/DciNotes20240406.json"}}
   ```

8. **Complex Nested Queries:**
   ```python
   # Work notes created in last 30 days OR personal YouTube videos
   {"$or": [
       {"$and": [
           {"domain": {"$eq": "work"}},
           {"type": {"$eq": "notes"}},
           {"created_at": {"$gte": (datetime.now() - timedelta(days=30)).timestamp()}}
       ]},
       {"$and": [
           {"domain": {"$eq": "personal"}},
           {"type": {"$eq": "youtube"}}
       ]}
   ]}

   # Documents with specific referer pattern AND created recently
   {"$and": [
       {"referer": {"$eq": "OpenSourceStategyProject"}},
       {"created_at": {"$gte": 1685469600.0}},
       {"$or": [
           {"type": {"$eq": "notes"}},
           {"type": {"$eq": "history"}}
       ]}
   ]}
   ```

**Available Operators:**
- `$eq`, `$ne` - Equal, Not equal
- `$gt`, `$gte`, `$lt`, `$lte` - Greater than, Greater or equal, Less than, Less or equal (numeric values only)
- `$in`, `$nin` - In array, Not in array
- `$and`, `$or` - Logical operators
- Shorthand: `{"key": "value"}` is equivalent to `{"key": {"$eq": "value"}}`

**Limitations:**
- `$regex`, `$exists`, `$contains`, `$like`, `$ilike`, and other pattern matching operators are NOT supported for metadata filtering
- ChromaDB only supports the basic comparison operators listed above for metadata filtering
- For pattern matching, use exact matches with `$eq` or `$ne`
- For field existence, use `$eq` with specific values or `$ne` to exclude values
- For substring matching, consider using semantic search with the `text` parameter instead of metadata filters
- Example: Use `search_documents(text="github", limit=10)` instead of `{"url": {"$contains": "github"}}`

**Complex Filtering Limitations:**
- ChromaDB requires explicit `$and` operator when combining multiple conditions
- **❌ Invalid**: `{"type": "youtube", "last_accessed_at": {"$gte": 1735689600.0}}`
- **✅ Valid**: `{"$and": [{"type": {"$eq": "youtube"}}, {"last_accessed_at": {"$gte": 1735689600.0}}]}`
- For complex date range queries, consider filtering results in Python after the initial search
- Example: Search for `{"type": "youtube"}` then filter by date in your application code

**Note on Document Filtering:**
- ChromaDB supports `$contains`, `$not_contains`, and `$regex` for document content filtering
- This MCP server now exposes both metadata filtering (`filter_metadata`) and content filtering (`filter_content`)
- Use `filter_content` for exact text matching, `text` parameter for semantic search
        """,
    ] = None,
    filter_content: Annotated[
        Optional[Dict[str, Any]],
        """Optional content filters for document text content.

**Available Content Operators:**
- `$contains` - Document contains the specified text
- `$not_contains` - Document does not contain the specified text
- `$regex` - Document matches the specified regex pattern
- `$and`, `$or` - Logical operators for combining conditions

**Examples:**
```python
# Find documents containing "github"
{"$contains": "github"}

# Find documents not containing "test"
{"$not_contains": "test"}

# Find documents matching regex pattern
{"$regex": "(?i)python.*script"}

# Complex content filtering
{"$and": [
    {"$contains": "python"},
    {"$not_contains": "test"}
]}

# Multiple conditions
{"$or": [
    {"$contains": "github"},
    {"$contains": "gitlab"}
]}
```

**Note:** Content filtering searches within the document text content, not metadata.
        """,
    ] = None,
) -> Dict[str, Any]:
    """
        Search for documents in the vector database using semantic similarity. The documents are split pieces if they contained an history and then each piece is split into chunks, and the search is performed on these chunks.

        **QUICK START EXAMPLES:**
        - Find YouTube videos: `search_documents(filter_metadata={"type": "youtube"})`
        - Find YouTube videos from 2025: `search_documents(filter_metadata={"$and": [{"type": {"$eq": "youtube"}}, {"last_accessed_at": {"$gte": 1735689600.0}}]})`
        - Find all documents: `search_documents()` or `search_documents(filter_metadata={})`
        - Search for "python" in content: `search_documents(text="python")`

        **IMPORTANT: Results are sorted by similarity score (most similar first), NOT by date or other criteria.**
        To get the most recent documents, you'll need to sort them in your application code after retrieval.

        **Date Field Availability:**
        - `last_accessed_at`: File modification time of the source markdown file when processed
          - **For markdown content**: When the .md file was last modified
          - **For YouTube videos**: When the markdown file containing the YouTube link was modified
          - **For web URLs**: When the markdown file containing the URL was modified
          - **For text files**: Inherited from JSON metadata (may not be set)
        - `created_at`: Document creation timestamp
          - **For newer documents**: File modification time or date header from markdown
          - **For older documents**: May not be set (use `last_accessed_at` instead)
        - **Recommendation**: Use `last_accessed_at` as the most reliable date field for all documents

        **Example: Get most recent YouTube videos:**
        ```python
        # Get all YouTube videos (sorted by similarity)
        results = search_documents(filter_metadata={"type": "youtube"})

        # Sort by last_accessed_at (most reliable date field for all documents)
        documents = results['documents']
        sorted_docs = sorted(documents,
                            key=lambda x: x['metadata'].get('last_accessed_at', 0),
                            reverse=True)
        most_recent = sorted_docs[0]  # Most recent YouTube video
        ```

        Returns:
            Dictionary containing search results like: {"documents": [{"content": "...", "metadata": {...}, "similarity_score": 0.95}], "total_results": 5, "timestamp": "2023-10-01T12:00:00Z"}

            Example metadata: {'created_at': 1685469900.0, 'source': '~/.second-brain/Chunk/DciNotes20240406-0001.txt', 'last_accessed_at': 1712397600.0, 'part': 1, 'referer': 'DciNotes', 'url': 'file:///home/flepied/Wiki/DciNotes', 'type': 'history', 'main_source': '~/.second-brain//Text/DciNotes20240406.json'}

            similarity_score: float representing the similarity score of the document to the search text. Lower score represents more similarity.

            total_results: Total number of documents found matching the search criteria.

            **Metadata Field Details:**

            **Date Fields:**
            - `created_at`: Document creation timestamp (file modification time or date header)
            - `last_accessed_at`: File modification time of source markdown file when processed

            **Content Identification:**
            - `type`: Document type classification
                - `'notes'`: Personal notes (default for markdown files)
                - `'youtube'`: YouTube video transcripts
                - `'pdf'`: PDF document content
                - `'web'`: Web page content
                - `'audio'`: Audio file transcripts
                - `'history'`: Historical project notes
            - `domain`: Content domain (set from markdown header, e.g., 'work', 'personal', 'project')

            **Source Tracking:**
            - `source`: Path to the individual chunk file (e.g., `/path/to/Chunk/DciNotes20240406-0001.txt`)
            - `main_source`: Path to the original JSON file before chunking (e.g., `/path/to/Text/DciNotes20240406.json`)
            - `referer`: Basename of the source markdown file (e.g., 'DciNotes', 'WorkHistory20231201')
            - `url`: Original URL or file path
                - For markdown: `file:///path/to/file.md`
                - For YouTube: `https://www.youtube.com/watch/VIDEO_ID`
                - For web content: Original URL
            - `part`: Chunk number within a document (1, 2, 3, etc.)

            **Processing Context:**
            - `last_accessed_at`: When the source markdown file was last modified (not when accessed)
            - `created_at`: When the document was first processed (file modification time or date header)
            - `referer`: Identifies which markdown file generated this content
            - `main_source`: Points to the JSON file that was chunked to create this document

    **Practical Use Cases:**

    1. **Find Recent Work Notes:**
       ```python
       {"$and": [
           {"domain": "work"},
           {"type": "notes"},
           {"created_at": {"$gte": (datetime.now() - timedelta(days=7)).timestamp()}}
       ]}
       ```

    2. **Search for Project Documentation:**
       ```python
       {"$and": [
           {"referer": {"$regex": ".*Project.*"}},
           {"$or": [{"type": "notes"}, {"type": "history"}]}
       ]}
       ```

    3. **Find Learning Materials:**
       ```python
       {"$or": [
           {"type": "youtube"},
           {"type": "pdf"},
           {"type": "audio"}
       ]}
       ```

    4. **Get Documents from Specific Time Period:**
       ```python
       {"$and": [
           {"created_at": {"$gte": 1685469600.0}},  # After specific date
           {"created_at": {"$lt": 1693152000.0}}    # Before specific date
       ]}
       ```

    5. **Find Multi-part Documents:**
       ```python
       {"part": {"$gt": 1}}  # Documents with multiple parts
       ```

    6. **Search by URL Pattern:**
       ```python
       # For exact URL matches, use $eq
       {"url": {"$eq": "https://github.com/hieblmi/go-host-lnaddr"}}

       # For pattern matching, use semantic search instead of metadata filters
       # search_documents(text="github", limit=10)  # This will find documents containing "github"
       ```
    """
    try:
        vectorstore = get_vectorstore()

        # Build search kwargs
        search_kwargs = {"k": limit}
        if filter_metadata:
            search_kwargs["filter"] = filter_metadata
        if filter_content:
            search_kwargs["where_document"] = filter_content

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
        """Optional metadata filters for complex document queries.

**Basic Examples:**
- `{'type': 'notes'}` - Count all personal notes
- `{'domain': 'work'}` - Count all work-related documents
- `{'type': 'youtube', 'domain': 'personal'}` - Count YouTube videos in personal domain

**Complex Query Examples:**

1. **Date Range Queries:**
   ```python
   # Count documents created after a specific timestamp
   {"created_at": {"$gt": 1685469600.0}}

   # Count documents created in the last 30 days
   {"created_at": {"$gte": (datetime.now() - timedelta(days=30)).timestamp()}}

   # Count documents created between two dates
   {"$and": [
       {"created_at": {"$gte": 1685469600.0}},
       {"created_at": {"$lte": 1693152000.0}}
   ]}
   ```

2. **Multiple Type Filtering:**
   ```python
   # Count notes OR history documents
   {"$or": [
       {"type": {"$eq": "notes"}},
       {"type": {"$eq": "history"}}
   ]}

   # Count all document types except audio
   {"type": {"$ne": "audio"}}
   ```

3. **Domain and Type Combinations:**
   ```python
   # Count work-related notes created recently
   {"$and": [
       {"domain": {"$eq": "work"}},
       {"type": {"$eq": "notes"}},
       {"created_at": {"$gt": 1685469600.0}}
   ]}

   # Count personal YouTube videos or PDFs
   {"$and": [
       {"domain": {"$eq": "personal"}},
       {"$or": [
           {"type": {"$eq": "youtube"}},
           {"type": {"$eq": "pdf"}}
       ]}
   ]}
   ```

4. **Referer and Source Filtering:**
   ```python
   # Count documents from a specific referer
   {"referer": {"$eq": "DciNotes"}}

   # Count documents from multiple referers
   {"referer": {"$in": ["DciNotes", "ProjectNotes", "MeetingNotes"]}}

   # Count documents with specific source pattern
   {"source": {"$regex": ".*DciNotes.*"}}
   ```

5. **Part and Chunk Filtering:**
   ```python
   # Count first part of multi-part documents
   {"part": {"$eq": 1}}

   # Count documents with multiple parts (not first part)
   {"part": {"$gt": 1}}

   # Count specific part range
   {"$and": [
       {"part": {"$gte": 2}},
       {"part": {"$lte": 5}}
   ]}
   ```

6. **Last Accessed Time Filtering:**
   ```python
   # Count recently accessed documents (last 7 days)
   {"last_accessed_at": {"$gte": (datetime.now() - timedelta(days=7)).timestamp()}}

   # Count documents accessed more than 30 days ago
   {"last_accessed_at": {"$lt": (datetime.now() - timedelta(days=30)).timestamp()}}
   ```

7. **URL and Main Source Filtering:**
   ```python
   # Count documents from specific URL pattern
   {"url": {"$regex": ".*github.*"}}

   # Count documents with main source
   {"main_source": {"$exists": True}}

   # Count documents without main source
   {"main_source": {"$exists": False}}
   ```

8. **Complex Nested Queries:**
   ```python
   # Count work notes created in last 30 days OR personal YouTube videos
   {"$or": [
       {"$and": [
           {"domain": {"$eq": "work"}},
           {"type": {"$eq": "notes"}},
           {"created_at": {"$gte": (datetime.now() - timedelta(days=30)).timestamp()}}
       ]},
       {"$and": [
           {"domain": {"$eq": "personal"}},
           {"type": {"$eq": "youtube"}}
       ]}
   ]}

   # Count documents with specific referer pattern AND created recently
   {"$and": [
       {"referer": {"$regex": ".*Project.*"}},
       {"created_at": {"$gte": 1685469600.0}},
       {"$or": [
           {"type": {"$eq": "notes"}},
           {"type": {"$eq": "history"}}
       ]}
   ]}
   ```

**Available Operators:**
- `$eq`, `$ne` - Equal, Not equal
- `$gt`, `$gte`, `$lt`, `$lte` - Greater than, Greater or equal, Less than, Less or equal (numeric values only)
- `$in`, `$nin` - In array, Not in array
- `$and`, `$or` - Logical operators
- Shorthand: `{"key": "value"}` is equivalent to `{"key": {"$eq": "value"}}`

**Limitations:**
- `$regex`, `$exists`, `$contains`, `$like`, `$ilike`, and other pattern matching operators are NOT supported for metadata filtering
- ChromaDB only supports the basic comparison operators listed above for metadata filtering
- For pattern matching, use exact matches with `$eq` or `$ne`
- For field existence, use `$eq` with specific values or `$ne` to exclude values
- For substring matching, consider using semantic search with the `text` parameter instead of metadata filters
- Example: Use `search_documents(text="github", limit=10)` instead of `{"url": {"$contains": "github"}}`

**Complex Filtering Limitations:**
- ChromaDB requires explicit `$and` operator when combining multiple conditions
- **❌ Invalid**: `{"type": "youtube", "last_accessed_at": {"$gte": 1735689600.0}}`
- **✅ Valid**: `{"$and": [{"type": {"$eq": "youtube"}}, {"last_accessed_at": {"$gte": 1735689600.0}}]}`
- For complex date range queries, consider filtering results in Python after the initial search
- Example: Search for `{"type": "youtube"}` then filter by date in your application code

**Note on Document Filtering:**
- ChromaDB supports `$contains`, `$not_contains`, and `$regex` for document content filtering
- This MCP server now exposes both metadata filtering (`filter_metadata`) and content filtering (`filter_content`)
- Use `filter_content` for exact text matching, `text` parameter for semantic search
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
