import os
import re
import sys
import string

from langchain.vectorstores import Chroma
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.indexes.vectorstore import VectorStoreIndexWrapper

from chromadb.config import Settings

import py3langid as langid

import nltk
from nltk.corpus import stopwords


STOP_WORDS = {}

# keep in sync with the languages in ~/nltk_data/corpora/stopwords
# language codes from https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes
SUPPORTED_LANGUAGES = {
    "ar": "arabic",
    "az": "azerbaijani",
    "eu": "basque",
    "bn": "bengali",
    "ca": "catalan",
    "zh": "chinese",
    "da": "danish",
    "nl": "dutch",
    "en": "english",
    "fi": "finnish",
    "fr": "french",
    "de": "german",
    "el": "greek",
    "he": "hebrew",
    "hi": "hinglish",
    "hu": "hungarian",
    "id": "indonesian",
    "it": "italian",
    "kk": "kazakh",
    "ne": "nepali",
    "no": "norwegian",
    "pt": "portuguese",
    "ro": "romanian",
    "ru": "russian",
    "sl": "slovene",
    "es": "spanish",
    "sv": "swedish",
    # tajik is not supported by langid
    # "tg": "tajik",
    "tr": "turkish",
}

# from https://stackoverflow.com/questions/2136556/in-python-how-do-i-split-a-string-and-keep-the-separators
SEPARATOR_REGEX = re.compile("([\s%s])" % re.escape(string.punctuation))


def init(langs):
    nltk.download("stopwords")
    for lang in langs:
        STOP_WORDS[lang] = stopwords.words(SUPPORTED_LANGUAGES[lang])
    print(f"Configuring languages: {langs}", file=sys.stderr)
    langid.set_languages(langs)


def cleanup_text(x):
    """Clean up text.

    - lowercase
    - remove stop words
    - remove urls
    - remove hashtag
    - remove consecutive spaces
    - remove consecutive newlines
    """
    x = x.lower()
    #     try:
    #         x = x.encode("latin1", "ignore").decode()
    #     except Exception as excpt:
    #         print(f"Unable to decode text: {excpt}")
    lang = langid.classify(x)[0]
    if lang not in STOP_WORDS:
        print(f"Invalid language {lang} detected", file=sys.stderr)
        lang = "en"
    else:
        print(f"Detected language {lang}", file=sys.stderr)
    x = "".join(
        [word for word in SEPARATOR_REGEX.split(x) if word not in STOP_WORDS[lang]]
    )
    x = re.sub(r"https?://\S+", " ", x)
    x = x.replace("#", "")
    x = re.sub(r"[ \t]{2,}", " ", x)
    x = re.sub(r"\n{3,}", "\n\n", x)
    return x


def get_embeddings():
    return HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")


def get_vectorstore(out_dir):
    db_dir = os.path.join(out_dir, "Db")
    # Define the Chroma settings
    CHROMA_SETTINGS = Settings(
        chroma_db_impl="duckdb+parquet",
        persist_directory=db_dir,
        anonymized_telemetry=False,
    )
    vectorstore = Chroma(
        embedding_function=get_embeddings(),
        persist_directory=db_dir,
        client_settings=CHROMA_SETTINGS,
    )
    return vectorstore


def get_indexer(out_dir):
    return VectorStoreIndexWrapper(vectorstore=get_vectorstore(out_dir))


# lib.py ends here
