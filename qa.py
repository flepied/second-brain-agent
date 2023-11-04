#!/usr/bin/env python3

"CLI to ask questions to the agent"

import sys

from dotenv import load_dotenv

import lib

load_dotenv()
agent = lib.Agent()
print(agent.question(sys.argv[1]))

# qa.py ends here
