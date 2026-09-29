import os
import sys

# Ensure no LLM_API_KEY leaks in from the environment during tests, so the
# whole suite runs offline in demo mode as required.
os.environ.pop("LLM_API_KEY", None)
os.environ["LLM_API_KEY"] = ""

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
