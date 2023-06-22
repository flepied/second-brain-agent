#!/usr/bin/env python
"""
"""

import hashlib
import os
import re
import sys

from langchain.document_loaders import (
    UnstructuredMarkdownLoader,
    UnstructuredURLLoader,
    PyMuPDFLoader,
)

from youtube_transcript_api import YouTubeTranscriptApi, _errors

YOUTUBE_REGEX = re.compile(r"https://www.youtube.com/embed/([^/\"]+)")
HTTP_REGEX = re.compile(r"https?://[^ ]+")
IGNORED_REGEX = re.compile(r"^https://(docs.google.com|source.redhat.com)")


def process_line(line, directory):
    if line == "":
        return line
    # process youtube url
    res = YOUTUBE_REGEX.search(line)
    if res:
        video_id = res.group(1)
        transcript_path = os.path.join(directory, "Text", video_id + ".txt")
        if os.path.exists(transcript_path):
            print(f"transcript already exists for video {video_id}", file=sys.stderr)
            return
        try:
            transcript = YouTubeTranscriptApi.get_transcript(
                video_id, languages=["en", "fr"]
            )
        except _errors.TranscriptsDisabled:
            print(f"transcript disabled for video {video_id}", file=sys.stderr)
            return
        except _errors.NoTranscriptFound:
            print(f"no transcript found for video {video_id}", file=sys.stderr)
            return
        print(f"writing video transcript {video_id}.txt", file=sys.stderr)
        with open(transcript_path, "w") as out_f:
            print(f"url=https://www.youtube.com/watch/{video_id}", file=out_f)
            for entry in transcript:
                print(entry["text"], file=out_f)
    else:
        res = HTTP_REGEX.search(line)
        if res:
            url = res.group(0)
            print(f"found url {url}", file=sys.stderr)
            # replace http by https
            if url.startswith("http://"):
                url = url.replace("http://", "https://")
                print(f"switched to {url}", file=sys.stderr)
            # skip private or local network urls
            if (
                url.startswith("https://192.168.")
                or url.startswith("https://10.")
                or url.startswith("https://127.")
            ):
                print(f"skipping private network url {url}", file=sys.stderr)
                return
            # skip urls that match the IGNORE_REGEX
            if IGNORED_REGEX.match(url):
                print(f"skipping ignored url {url}", file=sys.stderr)
                return
            # compute the output filename using the md5 hash of the url
            hash = hashlib.md5(url.encode("utf-8")).hexdigest()
            output_path = os.path.join(directory, "Text", hash + ".txt")
            if os.path.exists(output_path):
                print(f"file already exists for {output_path}", file=sys.stderr)
                return
            if url.endswith(".pdf"):
                try:
                    output = PyMuPDFLoader(url).load()
                except:
                    output = None
            else:
                output = UnstructuredURLLoader(
                    [url], continue_on_failure=True, encoding="UTF-8"
                ).load()
            if output:
                with open(output_path, "w") as out_f:
                    print(f"writing {hash}.txt", file=sys.stderr)
                    print(f"url={url}", file=out_f)
                    print(output[0].page_content, file=out_f)
            else:
                print(f"unable to get url content for {url}", file=sys.stderr)


def process_content(content, directory):
    for line in content.split("\n"):
        process_line(line, directory)


def main(in_dir, out_dir):
    excpt = os.getenv("IGNORE_REGEXP", None)
    if excpt:
        excpt = re.compile(excpt)
    # sync in -> out to create the new files
    for entry in os.scandir(in_dir):
        if not entry.name.endswith(".md"):
            continue
        fname = os.path.join(in_dir, entry.name)
        ftime = os.stat(fname).st_mtime
        oname = os.path.join(out_dir, "Text", os.path.basename(fname[:-3]) + ".txt")
        # do not write if the timestamps are the same
        try:
            otime = os.stat(oname).st_mtime
            if otime == ftime:
                continue
        except FileNotFoundError:
            pass
        print(f"writing {oname}", file=sys.stderr)
        loader = UnstructuredMarkdownLoader(fname)
        output = loader.load()[0]
        with open(oname, "w") as out_f:
            print(output.page_content, file=out_f)
        # support UTF-8 and latin-1 encodings
        try:
            with open(fname, encoding="utf-8") as in_f:
                process_content(in_f.read(-1), out_dir)
        except Exception:
            with open(fname, encoding="latin-1") as in_f:
                process_content(in_f.read(-1), out_dir)

        # set the timestamp to be the same
        stat = os.stat(fname)
        os.utime(oname, (stat.st_atime, stat.st_mtime))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])

# transform.py ends here
