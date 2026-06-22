"""
AutoGen + Groq — Extension Tasks
=================================
Extension 1: Tool-Wielding Researcher Agent (calculator + stock price fetcher)
Extension 2: UserProxy Agent with human-in-the-loop approval
"""

import os
import math
import asyncio
import getpass
import requests

from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
from autogen_ext.models.openai import OpenAIChatCompletionClient


# ---------------------------------------------------------------------------
# Step 1 — API Key
# ---------------------------------------------------------------------------
if "GROQ_API_KEY" not in os.environ:
    os.environ["GROQ_API_KEY"] = getpass.getpass("Enter your Groq API Key: ")

GROQ_KEY = os.environ["GROQ_API_KEY"]


# ---------------------------------------------------------------------------
# Step 2 — Tools (Extension 1)
# ---------------------------------------------------------------------------

def calculate(expression: str) -> str:
    """
    Safely evaluate a mathematical expression and return the result.

    Args:
        expression: A valid Python math expression e.g. "2 ** 10", "sqrt(144)"

    Returns:
        The result as a string, or an error message.
    """
    try:
        allowed = {k: getattr(math, k) for k in dir(math) if not k.startswith("_")}
        result = eval(expression, {"__builtins__": {}}, allowed)
        return f"Result of '{expression}' = {result}"
    except Exception as e:
        return f"Error evaluating expression: {e}"


def get_stock_price(ticker: str) -> str:
    """
    Fetch the latest stock price for a given ticker symbol using Yahoo Finance.

    Args:
        ticker: Stock ticker symbol e.g. 'AAPL', 'TSLA', 'NVDA'

    Returns:
        A string with the current price, or an error message.
    """
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker.upper()}"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        meta = data["chart"]["result"][0]["meta"]
        price = meta["regularMarketPrice"]
        currency = meta.get("currency", "USD")
        name = meta.get("shortName", ticker.upper())
        return f"Current price of {name} ({ticker.upper()}): {currency} {price:.2f}"
    except Exception as e:
        return f"Could not fetch stock price for '{ticker}': {e}"


# ---------------------------------------------------------------------------
# Step 3 — Model clients (Groq)
# ---------------------------------------------------------------------------

researcher_model = OpenAIChatCompletionClient(
    model="llama-3.1-8b-instant",
    base_url="https://api.groq.com/openai/v1",
    api_key=GROQ_KEY,
    model_info={
        "vision": False,
        "function_calling": True,
        "json_output": True,
        "structured_output": True,
        "family": "unknown"
    }
)

editor_model = OpenAIChatCompletionClient(
    model="llama-3.3-70b-versatile",
    base_url="https://api.groq.com/openai/v1",
    api_key=GROQ_KEY,
    model_info={
        "vision": False,
        "function_calling": True,
        "json_output": True,
        "structured_output": True,
        "family": "unknown"
    }
)


# ---------------------------------------------------------------------------
# Step 4 — Agents
# ---------------------------------------------------------------------------

# Extension 1: Researcher equipped with tools
researcher = AssistantAgent(
    name="Researcher",
    model_client=researcher_model,
    tools=[calculate, get_stock_price],
    system_message=(
        "You are an expert researcher with access to two tools:\n"
        "1. calculate(expression) — evaluates any maths expression.\n"
        "2. get_stock_price(ticker) — fetches the live stock price.\n\n"
        "Always use the tools when you need real numbers. "
        "Present findings in clear Markdown with actual data values. "
        "End your message with TERMINATE when you are done."
    )
)

# Extension 2: UserProxy — pauses the pipeline for human review
user_proxy = UserProxyAgent(
    name="HumanReviewer",
    input_func=None,   # uses input() — pauses and waits for you to type
)

# Editor — finalises after seeing researcher output + human feedback
editor = AssistantAgent(
    name="Editor",
    model_client=editor_model,
    system_message=(
        "You are a strict editor. You will receive:\n"
        "1. The researcher's draft with real data.\n"
        "2. Feedback from the human reviewer.\n\n"
        "Incorporate the feedback, verify the data values are accurate, "
        "and produce a polished final version. "
        "End with TERMINATE when complete."
    )
)


# ---------------------------------------------------------------------------
# Step 5 — Team: Researcher -> HumanReviewer -> Editor
# ---------------------------------------------------------------------------

termination = (
    TextMentionTermination("TERMINATE") | MaxMessageTermination(max_messages=8)
)

team = RoundRobinGroupChat(
    participants=[researcher, user_proxy, editor],
    termination_condition=termination
)


# ---------------------------------------------------------------------------
# Step 6 — Run
# ---------------------------------------------------------------------------

async def main():
    print("=" * 60)
    print("  AutoGen + Groq — Extension Tasks")
    print("=" * 60)
    print()
    print("HOW TO USE:")
    print("  After the Researcher finishes, YOU will be prompted to type.")
    print("  → Press Enter (no text)   : approve, Editor proceeds")
    print("  → Type feedback and Enter : Editor will incorporate it")
    print("  → Type TERMINATE          : end the session immediately")
    print()

    task = (
        "Find the current stock prices of Apple (AAPL) and Nvidia (NVDA). "
        "Calculate the total cost to buy 10 shares of each. "
        "Then write a brief investment summary comparing the two."
    )
    print(f"Task: {task}\n")
    print("-" * 60)

    async for message in team.run_stream(task=task):
        source = getattr(message, "source", "System")
        content = getattr(message, "content", str(message))

        labels = {
            "Researcher":    " [Researcher — using tools]",
            "HumanReviewer": " [YOU — Human Reviewer]",
            "Editor":        " [Editor — final polish]",
        }
        label = labels.get(source, f"[{source}]")
        print(f"\n\033[1m{label}\033[0m")
        print(content)
        print("-" * 60)


if __name__ == "__main__":
    asyncio.run(main())
