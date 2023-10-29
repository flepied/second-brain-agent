#!/usr/bin/env python3

"CLI to ask questions to the agent"

import sys

from dotenv import load_dotenv

import lib

load_dotenv()
agent = lib.Agent()
metadata = dict([arg.split("=", 1) for arg in sys.argv[2:]])
print(agent.question(sys.argv[1], metadata))

# qa.py ends here
