"Various metadata extractors."

import sys
from datetime import date
from typing import Optional, Sequence

from langchain.llms import OpenAI
from langchain.llms.base import BaseLLM
from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import (
    ChatPromptTemplate,
    FewShotChatMessagePromptTemplate,
    PromptTemplate,
)
from pydantic import BaseModel

_DEBUG = True

####################
# Period extractor #
####################


class Period(BaseModel):
    start_date: date
    end_date: date


# Set up a parser + inject instructions into the prompt template.
_PERIOD_PARSER = PydanticOutputParser(pydantic_object=Period)

# Prompt
_PERIOD_PROMPT = PromptTemplate(
    template="Extract the dates. When a month is specicified starts at the first day of the month and ends at the last day of the month. When a week is specified starts on Monday and ends on Sunday.\n {format_instructions}\nToday is {day_of_week} {today}.\nInput: {query}\n",
    input_variables=["query", "today", "day_of_week"],
    partial_variables={"format_instructions": _PERIOD_PARSER.get_format_instructions()},
)


def extract_period(
    query: str, today: str = None, day_of_week: str = None, model: BaseLLM = None
) -> Optional[Period]:
    """
    Extract a period from a query.
    """
    if today is None:
        today = date.today().strftime("%Y-%m-%d")
    if day_of_week is None:
        day_of_week = date.today().strftime("%A")
    _input = _PERIOD_PROMPT.format_prompt(
        query=query, today=today, day_of_week=day_of_week
    )
    if _DEBUG:
        print(f"Input: {_input.to_string()}", file=sys.stderr)
    if model is None:
        model = OpenAI(temperature=0)
    output = model(_input.to_string())
    if _DEBUG:
        print(f"Output: {output}", file=sys.stderr)
    try:
        return _PERIOD_PARSER.parse(output)
    except:
        return None


####################
# Intent extractor #
####################


class Intent(BaseModel):
    intent: str


# Set up a parser + inject instructions into the prompt template.
_INTENT_PARSER = PydanticOutputParser(pydantic_object=Intent)

# Prompt
_INTENT_PROMPT = PromptTemplate(
    template="Please analyze the following question to classify if this is an activity report request, a summary request, or a regular question.\n{format_instructions}\nQuestion: {query}\n",
    input_variables=["query"],
    partial_variables={"format_instructions": _INTENT_PARSER.get_format_instructions()},
)


def extract_intent(query: str, model: BaseLLM = None) -> Optional[Intent]:
    """
    Extract a intent without any date from a query.
    """
    _input = _INTENT_PROMPT.format_prompt(query=query)
    if _DEBUG:
        print(f"Input: {_input.to_string()}", file=sys.stderr)
    if model is None:
        model = OpenAI(temperature=0)
    output = model(_input.to_string())
    if _DEBUG:
        print(f"Output: {output}", file=sys.stderr)
    try:
        return _INTENT_PARSER.parse(output)
    except:
        return None


#######################
# Documents extractor #
#######################


class Documents(BaseModel):
    document_names: Sequence[str]


# Set up a parser + inject instructions into the prompt template.
_DOC_PARSER = PydanticOutputParser(pydantic_object=Documents)

# Prompt
_DOC_PROMPT = PromptTemplate(
    template="Based on the question, please choose the most relevant document(s) to provide a well-informed answer. Here is the list of documents to choose from:\n{documents_desc}\n{format_instructions}\nQuestion: {query}\n",
    input_variables=["query"],
    partial_variables={"format_instructions": _DOC_PARSER.get_format_instructions()},
)


def extract_documents(
    query: str, documents_desc: str, model: BaseLLM = None
) -> Optional[Documents]:
    """
    Extract the document(s) from a query.
    """
    _input = _DOC_PROMPT.format_prompt(query=query, documents_desc=documents_desc)
    if _DEBUG:
        print(f"Input: {_input.to_string()}", file=sys.stderr)
    if model is None:
        model = OpenAI(temperature=0)
    output = model(_input.to_string())
    if _DEBUG:
        print(f"Output: {output}", file=sys.stderr)
    try:
        return _DOC_PARSER.parse(output)
    except Exception as excp:
        print(excp, file=sys.stderr)
        return None


######################
# Sentence extractor #
######################


class Sentence(BaseModel):
    sentence: str


# Set up a parser + inject instructions into the prompt template.
_SENTENCE_PARSER = PydanticOutputParser(pydantic_object=Sentence)

# Prompt
_SENTENCE_PROMPT = PromptTemplate(
    template="Please rephrase the following sentence to remove any notion of time.\n {format_instructions}\nSentence: {query}\n",
    input_variables=["query"],
    partial_variables={
        "format_instructions": _SENTENCE_PARSER.get_format_instructions()
    },
)


def extract_sentence_no_time(query: str, model: BaseLLM = None) -> Optional[Sentence]:
    """
    Extract a sentence without any time from a query.
    """
    _input = _SENTENCE_PROMPT.format_prompt(query=query)
    if _DEBUG:
        print(f"Input: {_input.to_string()}", file=sys.stderr)
    if model is None:
        model = OpenAI(temperature=0)
    output = model(_input.to_string())
    if _DEBUG:
        print(f"Output: {output}", file=sys.stderr)
    try:
        return _SENTENCE_PARSER.parse(output)
    except:
        return None


#######################
# Step Back extractor #
#######################

# Prompt
# Few Shot Examples
_EXAMPLES = [
    {
        "input": "Could the members of The Police perform lawful arrests?",
        "output": "what can the members of The Police do?",
    },
    {
        "input": "Jan Sindel’s was born in what country?",
        "output": "what is Jan Sindel’s personal history?",
    },
]
# We now transform these to example messages
_EXAMPLE_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("human", "{input}"),
        ("ai", "{output}"),
    ]
)

_FEW_SHOT_PROMPT = FewShotChatMessagePromptTemplate(
    example_prompt=_EXAMPLE_PROMPT,
    examples=_EXAMPLES,
)

_STEP_BACK_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are an expert at world knowledge. Your task is to step back and paraphrase a question to a more generic step-back question, which is easier to answer.\nHere are a few examples:""",
        ),
        # Few shot examples
        _FEW_SHOT_PROMPT,
        # New question
        ("user", "{question}"),
    ]
)


def extract_step_back(query: str, model: BaseLLM = None) -> Optional[Sentence]:
    """
    Extract a step back question from a query.
    """
    _input = _STEP_BACK_PROMPT.format(question=query)
    if _DEBUG:
        print(f"Input: {_input}", file=sys.stderr)
    if model is None:
        model = OpenAI(temperature=0)
    output = model(_input)
    if _DEBUG:
        print(f"Output: {output}", file=sys.stderr)
    try:
        return output.split("AI: ")[1].strip()
    except:
        return None


# extractors.py ends here
