#!/usr/bin/env python

"""
Transform markdown files from a directory or filenames read on the
standard input into json files and read the content of these markdown
files to extract url, youtube videos and pdf and transform them into
json files too.
"""

import datetime
import glob
import hashlib
import json
import os
import re
import shutil
import sys

import assemblyai as aai
import yt_dlp
from dotenv import load_dotenv
from langchain.document_loaders import (
    AssemblyAIAudioTranscriptLoader,
    PyMuPDFLoader,
    UnstructuredURLLoader,
)
from langchain.document_loaders.blob_loaders.youtube_audio import YoutubeAudioLoader
from langchain.document_loaders.generic import GenericLoader
from langchain.document_loaders.parsers import OpenAIWhisperParser
from youtube_transcript_api import YouTubeTranscriptApi, _errors

from lib import ChecksumStore, DateTimeEncoder, is_history_filename, is_same_time

YOUTUBE_REGEX = re.compile(r"https://www.youtube.com/embed/([^/\"]+)")
HTTP_REGEX = re.compile(r"https://[^ ]+")
IGNORED_REGEX = re.compile(r"^https://(docs.google.com|source.redhat.com)")


def get_output_file_path(directory, base):
    "return the path of the output json file"
    return os.path.join(directory, "Text", base + ".json")


def save_content(file_path, text, check_content=True, **metadata):
    "save the text and metatada into a json file"
    if check_content:
        try:
            print(f"reading {file_path}", file=sys.stderr)
            with open(file_path, "r", encoding="utf-8") as in_f:
                data = json.load(in_f)
            if data["text"] == text:
                print(f"content is the same for {file_path}", file=sys.stderr)
                return False
        except FileNotFoundError:
            pass
        except json.decoder.JSONDecodeError as exc:
            print(f"invalid json file {file_path}: {exc}", file=sys.stderr)
    print(f"writing {file_path} metadata={metadata}", file=sys.stderr)
    data = {"text": text, "metadata": metadata}
    with open(file_path, "w", encoding="utf-8") as out_f:
        json.dump(data, out_f, cls=DateTimeEncoder, ensure_ascii=False, indent=2)
    return True


def process_youtube_line(basename, line, directory, last_accessed_at):
    "Test the line contains a youtube url and extract the transcript in the output directory"
    res = YOUTUBE_REGEX.search(line)
    if res:
        video_id = res.group(1)
        print(f"found youtube video {video_id}", file=sys.stderr)
        transcript_path = get_output_file_path(directory, video_id)
        if os.path.exists(transcript_path):
            print(f"transcript already exists for video {video_id}", file=sys.stderr)
            return True
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
                last_accessed_at=last_accessed_at,
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
            print(
                f"ERROR: unable to download youtube video {video_id}",
                file=sys.stderr,
            )
            return False
        save_content(
            transcript_path,
            "\n".join([doc.page_content for doc in docs]),
            url=f"https://www.youtube.com/watch/{video_id}",
            referer=basename,
            type="youtube",
            last_accessed_at=last_accessed_at,
        )
        return True
    return False


def process_url_line(basename, line, directory, last_accessed_at):
    "process url line by download pdf or html content into a text file in {directory}"
    res = HTTP_REGEX.search(line)
    if res:
        url = res.group(0)
        print(f"found url {url}", file=sys.stderr)
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
                last_accessed_at=last_accessed_at,
            )
        else:
            print(f"ERROR: unable to get url content for {url}", file=sys.stderr)
        return True
    return False


MP3_REGEX = re.compile(r"(https://.*\.mp3)")


def process_mp3_line(basename, line, directory, last_accessed_at):
    "Process mp3 url by extracting the text using AssemblyAI"
    res = MP3_REGEX.search(line)
    if res:
        print(f"found mp3 url {res.group(0)}", file=sys.stderr)
        aai_api_key = os.getenv("ASSEMBLYAI_API_KEY")
        if aai_api_key is None:
            print(
                "ERROR: ASSEMBLYAI_API_KEY environment variable is not set",
                file=sys.stderr,
            )
            return True
        url = res.group(0)
        filename_hash = hashlib.md5(url.encode("utf-8")).hexdigest()
        output_path = get_output_file_path(directory, filename_hash)
        if os.path.exists(output_path):
            print(f"file already exists for {output_path}", file=sys.stderr)
            return True
        config = aai.TranscriptionConfig(
            speaker_labels=True,
            auto_chapters=True,
            entity_detection=True,
        )

        output = AssemblyAIAudioTranscriptLoader(
            file_path=url, config=config, api_key=aai_api_key
        ).load()
        if output:
            save_content(
                output_path,
                output[0].page_content,
                url=url,
                referer=basename,
                type="audio",
                last_accessed_at=last_accessed_at,
            )
        else:
            print(f"ERROR: unable to get mp3 transcript for {url}", file=sys.stderr)
        return True
    return False


def process_line(basename, line, directory, last_accessed_at):
    "Extract information from a line of a text file"
    return (
        line == ""
        or process_youtube_line(basename, line, directory, last_accessed_at)
        or process_mp3_line(basename, line, directory, last_accessed_at)
        or process_url_line(basename, line, directory, last_accessed_at)
    )


def process_content(basename, content, directory, last_accessed_at):
    "Process all the content from a file line by line skipping the header"
    in_header = True
    for line in content.split("\n"):
        if in_header:
            if line in ("---", "", "...") or len(line.split(":", 1)) == 2:
                continue
            in_header = False
        process_line(basename, line, directory, last_accessed_at)


def get_metadata(content):
    "Extract metadata from the header and remove the header from the content"
    metadata = {}
    lines = content.split("\n")
    idx = 0
    for idx, line in enumerate(lines):
        header = line.split(":", 1)
        if len(header) == 2:
            metadata[header[0].strip().lower()] = header[1].strip()
            continue
        if line in ("---", "", "..."):
            continue
        break
    if "date" in metadata:
        # transform date to a date object and save is as created_at
        # because langchain uses that field
        try:
            metadata["created_at"] = datetime.datetime.strptime(
                metadata["date"], "%Y/%m/%d %H:%M"
            )
            del metadata["date"]
        except ValueError:
            pass
    content = "\n".join(lines[idx:])
    return metadata, content


def remove_dash(content, level):
    "Remove dashes from the content"
    lines = content.split("\n")
    dashes = "#" * level
    for idx, line in enumerate(lines):
        if line.startswith(dashes):
            lines[idx] = line[level:].strip()
    return "\n".join(lines)


def get_date(date_str):
    "Get the date from a string trying different formats: 01 Jan 2020 then 01 January 2020"
    try:
        return datetime.datetime.strptime(date_str, "%d %B %Y")
    except ValueError:
        try:
            return datetime.datetime.strptime(date_str, "%d %b %Y")
        except ValueError:
            print(f"Unable to parse date {date_str}", file=sys.stderr)
            return date_str


def clean_referer(referer):
    "remove numbers from the referer"
    return re.sub(r"\d+", "", referer)


DATE2_REGEXP = re.compile(r"^## (\d\d \w+ \d\d\d\d)", re.MULTILINE)
DATE3_REGEXP = re.compile(r"^### (\d\d \w+ \d\d\d\d)", re.MULTILINE)


def split_md_file(fname, md_dir):
    "Split a markdown file into multiple files according to history"
    basename = os.path.basename(fname[:-3])
    with open(fname, "r", encoding="UTF-8") as fptr:
        content = fptr.read()
    files = []
    # journal/history files have only history entries
    if is_history_filename(fname):
        history = DATE2_REGEXP.split(content)
        level = 1
    elif content.find("## History") != -1:
        history = DATE3_REGEXP.split(content)
        level = 2
    else:
        history = []
        files = [fname]
    if len(history) >= 3:
        base_fname = os.path.join(md_dir, basename + ".md")
        with open(base_fname, "w", encoding="UTF-8") as fptr:
            fptr.write(history[0])
        files.append(base_fname)
        stat = os.stat(fname)
        os.utime(base_fname, (stat.st_atime, stat.st_mtime))
        for idx in range(1, len(history), 2):
            history_date = get_date(history[idx])
            if isinstance(history_date, str):
                continue
            if level == 1:
                date = history_date.strftime("%d")
            else:
                date = history_date.strftime("%Y%m%d")
            part_fname = os.path.join(md_dir, basename + date + ".md")
            with open(part_fname, "w", encoding="UTF-8") as fptr:
                fptr.write(f"---\nReferer: {clean_referer(basename)}\n---\n\n")
                fptr.write("# " + history[idx] + remove_dash(history[idx + 1], level))
            mtime = (history_date + datetime.timedelta(hours=12)).timestamp()
            os.utime(part_fname, (mtime, mtime))
            files.append(part_fname)
    print(f"found {len(files)} history files", file=sys.stderr)
    return files


def write_output_file(md_file, out_dir, metadata):
    "Write the output json file from a markdown file and process the its content"
    with open(md_file, "r", encoding="UTF-8") as fptr:
        output = fptr.read()
    md_stat = os.stat(md_file)
    last_accessed_at = datetime.datetime.fromtimestamp(md_stat.st_mtime)
    basename = os.path.basename(md_file[:-3])
    if metadata is None:
        # add metadata and remove header from content from the first file
        metadata, content = get_metadata(output)
        metadata["type"] = "notes"
    else:
        new_metadata, content = get_metadata(output)
        metadata.update(new_metadata)
        metadata["type"] = "history"
    metadata["last_accessed_at"] = last_accessed_at
    if "url" not in metadata:
        metadata["url"] = f"file://{md_file}"
    print(f"saving {md_file=} with {metadata=}", file=sys.stderr)
    omdname = get_output_file_path(out_dir, basename)
    saved = save_content(
        omdname,
        content,
        **metadata,
    )
    # if content has been saved, process it
    if saved:
        # support UTF-8 and latin-1 encodings
        try:
            with open(md_file, encoding="utf-8") as in_f:
                process_content(basename, in_f.read(-1), out_dir, last_accessed_at)
        # pylint: disable=broad-exception-caught
        except Exception:
            with open(md_file, encoding="latin-1") as in_f:
                process_content(basename, in_f.read(-1), out_dir, last_accessed_at)

    return metadata


def process_md_file(fname, out_dir, checksum_store):
    "Process a markdown file if the output text file is older or non existent"
    print(f"processing '{fname}'", file=sys.stderr)
    if not fname.endswith(".md"):
        print(f"Ignoring non md file {fname}", file=sys.stderr)
        return False
    basename = os.path.basename(fname[:-3])
    oname = get_output_file_path(out_dir, basename)
    if not os.path.exists(fname):
        print(f"removing {oname} as {fname} do not exist anymore", file=sys.stderr)
        os.remove(oname)
        if is_history_filename(fname):
            for hname in glob.glob(
                os.path.join(out_dir, "Markdown", basename + "*.md")
            ):
                basename = os.path.basename(hname[:-3])
                oname = get_output_file_path(out_dir, basename)
                print(
                    f"removing {hname} / {oname} as {fname} do not exist anymore",
                    file=sys.stderr,
                )
                os.remove(hname)
                os.remove(oname)
        return True
    if is_same_time(fname, oname):
        print(f"skipping {fname} as there is no time change", file=sys.stderr)
        return False
    if checksum_store.has_file_changed(fname) is not False or not os.path.exists(oname):
        md_files = split_md_file(fname, os.path.join(out_dir, "Markdown"))
        metadata = None
        # extract the metadata and content from the first file and pass it to the others
        for md_file in md_files:
            metadata = write_output_file(md_file, out_dir, metadata)
    else:
        print(f"skipping {fname} / {oname} as content did not change", file=sys.stderr)
        return False
    print(f"processed '{fname}'", file=sys.stderr)
    return True


def main(in_dir, out_dir):
    "Entry point"
    checksum_store = ChecksumStore(os.path.join(out_dir, "checksums.json"))
    # read filenames from stdin
    if in_dir == "-":
        print("Reading filenames from stdin", file=sys.stderr)
        for fname in sys.stdin:
            process_md_file(fname.rstrip(), out_dir, checksum_store)
    else:
        # scan input dir
        for entry in os.scandir(in_dir):
            process_md_file(os.path.join(in_dir, entry.name), out_dir, checksum_store)


if __name__ == "__main__":
    load_dotenv()
    main(sys.argv[1], sys.argv[2])

# transform_md.py ends here
