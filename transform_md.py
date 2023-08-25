#!/usr/bin/env python

"""
Transform markdown files from a directory or filenames read on the
standard input into json files and read the content of these markdown
files to extract url, youtube videos and pdf and transform them into
json files too.
"""

import hashlib
import json
import os
import re
import shutil
import sys

import yt_dlp
from dotenv import load_dotenv
from langchain.document_loaders import (
    PyMuPDFLoader,
    UnstructuredMarkdownLoader,
    UnstructuredURLLoader,
)
from langchain.document_loaders.blob_loaders.youtube_audio import YoutubeAudioLoader
from langchain.document_loaders.generic import GenericLoader
from langchain.document_loaders.parsers import OpenAIWhisperParser
from youtube_transcript_api import YouTubeTranscriptApi, _errors

from lib import ChecksumStore, is_same_time

YOUTUBE_REGEX = re.compile(r"https://www.youtube.com/embed/([^/\"]+)")
HTTP_REGEX = re.compile(r"https?://[^ ]+")
IGNORED_REGEX = re.compile(r"^https://(docs.google.com|source.redhat.com)")


def get_output_file_path(directory, base):
    "return the path of the output json file"
    return os.path.join(directory, "Text", base + ".json")


def save_content(file_path, text, **metadata):
    "save the text and metatada into a json file"
    print(f"writing {file_path} metadata={metadata}", file=sys.stderr)
    data = {"text": text, "metadata": metadata}
    with open(file_path, "w", encoding="utf-8") as out_f:
        json.dump(data, out_f)


def process_youtube_line(basename, line, directory):
    "Test the line contains a youtube url and extract the transcript in the output directory"
    res = YOUTUBE_REGEX.search(line)
    if res:
        video_id = res.group(1)
        print(f"found youtube video {video_id}", file=sys.stderr)
        transcript_path = get_output_file_path(directory, video_id)
        if os.path.exists(transcript_path):
            print(f"transcript already exists for video {video_id}", file=sys.stderr)
        else:
            try:
                transcript = YouTubeTranscriptApi.get_transcript(
                    video_id, languages=["en", "fr"]
                )
                save_content(
                    transcript_path,
                    "\n".join([entry["text"] for entry in transcript]),
                    url=f"https://www.youtube.com/watch/{video_id}",
                    referer=basename,
                    type="youtube",
                )
                return True
            except _errors.TranscriptsDisabled:
                print(f"transcript disabled for video {video_id}", file=sys.stderr)
            except _errors.NoTranscriptFound:
                print(f"no transcript found for video {video_id}", file=sys.stderr)
                print(f"writing video transcript {video_id}.txt", file=sys.stderr)
            print(f"falling back to whisper for {video_id}", file=sys.stderr)
            # Directory to save audio files
            save_dir = os.path.join(directory, "Orig")

            # Transcribe the videos to text
            loader = GenericLoader(
                YoutubeAudioLoader([f"https://youtu.be/{video_id}"], save_dir),
                OpenAIWhisperParser(),
            )
            try:
                docs = loader.load()
            except yt_dlp.utils.DownloadError:
                print(f"unable to download youtube video {video_id}", file=sys.stderr)
                return False
            save_content(
                transcript_path,
                "\n".join([doc.page_content for doc in docs]),
                url=f"https://www.youtube.com/watch/{video_id}",
                referer=basename,
                type="youtube",
            )
        return True
    return False


def process_url_line(basename, line, directory):
    "process url line by download pdf or html content into a text file in {directory}"
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
            return True
        # skip urls that match the IGNORE_REGEX
        if IGNORED_REGEX.match(url):
            print(f"skipping ignored url {url}", file=sys.stderr)
            return True
        # compute the output filename using the md5 hash of the url
        filename_hash = hashlib.md5(url.encode("utf-8")).hexdigest()
        output_path = get_output_file_path(directory, filename_hash)
        if url.endswith(".pdf"):
            if os.path.exists(output_path):
                print(f"file already exists for {output_path}", file=sys.stderr)
                return True
            try:
                file_type = "pdf"
                loader = PyMuPDFLoader(url)
                output = loader.load()
                # save pdf to the Orig directory
                shutil.copyfile(
                    loader.file_path,
                    os.path.join(
                        directory,
                        "Orig",
                        os.path.basename(url),
                    ),
                )
            # pylint: disable=broad-exception-caught
            except Exception as excpt:
                output = None
                print(f"Unable to get {url}: {excpt}")
        else:
            file_type = "web"
            output = UnstructuredURLLoader(
                [url], continue_on_failure=True, encoding="UTF-8"
            ).load()
        if output:
            save_content(
                output_path,
                output[0].page_content,
                url=url,
                referer=basename,
                type=file_type,
            )
        else:
            print(f"unable to get url content for {url}", file=sys.stderr)
        return True
    return False


def process_line(basename, line, directory):
    "Extract information from a line of a text file"
    return (
        line == ""
        or process_youtube_line(basename, line, directory)
        or process_url_line(basename, line, directory)
    )


def process_content(basename, content, directory):
    "Process all the content form a file line by line"
    for line in content.split("\n"):
        process_line(basename, line, directory)


def process_file(fname, out_dir, checksum_store):
    "Process a markdown file if the output text file is older or non existent"
    print(f"processing '{fname}'", file=sys.stderr)
    if not fname.endswith(".md"):
        print(f"Ignoring non md file {fname}", file=sys.stderr)
        return
    basename = os.path.basename(fname[:-3])
    oname = get_output_file_path(out_dir, basename)
    if is_same_time(fname, oname):
        return
    if checksum_store.has_file_changed(fname) is not False:
        print(f"writing {oname}", file=sys.stderr)
        loader = UnstructuredMarkdownLoader(fname)
        output = loader.load()[0]
        save_content(oname, output.page_content, type="notes", url=f"file://{fname}")
        # support UTF-8 and latin-1 encodings
        try:
            with open(fname, encoding="utf-8") as in_f:
                process_content(basename, in_f.read(-1), out_dir)
        # pylint: disable=broad-exception-caught
        except Exception:
            with open(fname, encoding="latin-1") as in_f:
                process_content(basename, in_f.read(-1), out_dir)
    else:
        print(f"skipping {fname} as content did not change", file=sys.stderr)
    # set the timestamp to be the same
    stat = os.stat(fname)
    os.utime(oname, (stat.st_atime, stat.st_mtime))


def main(in_dir, out_dir):
    "Entry point"
    checksum_store = ChecksumStore(os.path.join(out_dir, "checksums.json"))
    # read filenames from stdin
    if in_dir == "-":
        print("Reading filenames from stdin", file=sys.stderr)
        for fname in sys.stdin:
            process_file(fname.rstrip(), out_dir, checksum_store)
    else:
        # scan input dir
        for entry in os.scandir(in_dir):
            process_file(os.path.join(in_dir, entry.name), out_dir, checksum_store)


if __name__ == "__main__":
    load_dotenv()
    main(sys.argv[1], sys.argv[2])

# transform_md.py ends here
