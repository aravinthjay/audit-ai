import os
import re
import json
import pandas as pd

from rouge_score import rouge_scorer
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI


# ============================================================
# STEP 1: Create the LLM
# ============================================================
# Make sure OPENAI_API_KEY is already set in environment variables

from langchain_community.llms import HuggingFacePipeline
from transformers import pipeline

pipe = pipeline("text-generation", model="gpt2")

llm = HuggingFacePipeline(pipeline=pipe)


# ============================================================
# PART 1: ZERO-SHOT + FEW-SHOT SUMMARISATION CHAIN
# ============================================================

print("\n" + "=" * 80)
print("PART 1: ZERO-SHOT + FEW-SHOT SUMMARISATION")
print("=" * 80 + "\n")


# ------------------------------------------------------------
# A) Prompt for generating 3 earnings call snippets
# ------------------------------------------------------------
generate_snippets_template = """
You are a financial data generator.

Generate exactly 3 realistic earnings call snippets for 3 different companies.
Each snippet should be 4 to 5 lines long and include:
1. Financial performance
2. Key business driver
3. Management outlook

Return the output in this format only:

Snippet 1:
...

Snippet 2:
...

Snippet 3:
...
"""

generate_snippets_prompt = PromptTemplate(
    input_variables=[],
    template=generate_snippets_template
)

generate_snippets_chain = generate_snippets_prompt | llm

generated_snippets_response = generate_snippets_chain.invoke({})
generated_snippets_text = generated_snippets_response

print("Generated Earnings Call Snippets:\n")
print(generated_snippets_text)
print("\n" + "-" * 80 + "\n")


# ------------------------------------------------------------
# Extract the 3 snippets from model response
# ------------------------------------------------------------
snippet_pattern = r"Snippet\s*\d+\s*:\s*(.*?)(?=Snippet\s*\d+\s*:|$)"
matches = re.findall(snippet_pattern, generated_snippets_text, re.DOTALL)

earnings_snippets = [match.strip() for match in matches]

# Fallback in case parsing does not return 3 snippets
if len(earnings_snippets) != 3:
    earnings_snippets = [
        """Revenue grew 12% year-over-year, driven by strong cloud subscription demand.
Operating margin improved to 21% because of lower infrastructure costs.
Management said enterprise renewals remained healthy across key regions.
The company expects steady momentum in the next quarter, though it remains cautious on global macro headwinds.""",

        """Quarterly sales declined 4% due to weaker smartphone shipments in Asia.
However, services revenue hit a record level and gross margin stayed stable.
Executives highlighted strong user retention and rising recurring revenue.
Management expects gradual recovery as supply chain conditions improve in the coming months.""",

        """Advertising revenue fell 6% because retail clients reduced spending.
Despite this, the firm added over 150 new enterprise AI customers during the quarter.
Operating expenses declined following restructuring efforts.
Leadership expects profitability to improve in the second half of the year as AI adoption grows."""
    ]


# ------------------------------------------------------------
# B) Prompts for summarizing
#    1. Zero-shot prompt
#    2. Few-shot prompt
# ------------------------------------------------------------

# Zero-shot summarisation prompt
zero_shot_summary_template = """
You are a financial analyst assistant.

Summarize the following earnings call snippet in exactly 3 bullet points.

Focus on:
1. Financial performance
2. Business driver
3. Management outlook

Snippet:
{snippet}

Summary:
"""

zero_shot_prompt = PromptTemplate(
    input_variables=["snippet"],
    template=zero_shot_summary_template
)

zero_shot_chain = zero_shot_prompt | llm


# Few-shot summarisation prompt
few_shot_summary_template = """
You are a financial analyst assistant.

Below are examples of how earnings call snippets should be summarized.

Example 1
Snippet:
Revenue increased 10% year-over-year due to strong software demand.
Operating profit improved because of lower marketing spend.
Management expects moderate growth next quarter.

Summary:
- Revenue rose 10% year-over-year, mainly supported by software demand.
- Profitability improved due to lower marketing expenses.
- Management expects moderate growth in the upcoming quarter.

Example 2
Snippet:
Hardware sales declined, but cloud revenue grew 18%.
Margins were pressured by logistics costs.
Executives remain optimistic about retention and product expansion.

Summary:
- Hardware performance was weak, while cloud revenue increased 18%.
- Margins were affected by higher logistics expenses.
- Leadership remains positive about customer retention and future expansion.

Now summarize the following earnings call snippet in the same style.

Snippet:
{snippet}

Summary:
"""

few_shot_prompt = PromptTemplate(
    input_variables=["snippet"],
    template=few_shot_summary_template
)

few_shot_chain = few_shot_prompt | llm


# ------------------------------------------------------------
# Reference summaries (for ROUGE-L evaluation)
# These are "gold summaries" used to compare model output
# ------------------------------------------------------------
reference_summaries = [
    """- Revenue grew strongly year-over-year due to cloud subscription demand.
- Margins improved because of reduced infrastructure costs and healthy renewals.
- Management expects steady next-quarter performance but remains cautious on macro conditions.""",

    """- Sales declined because of weaker smartphone demand, especially in Asia.
- Services revenue remained strong and supported stability in margins.
- Management expects supply chain improvements and gradual recovery ahead.""",

    """- Advertising revenue declined as retail clients cut spending.
- AI customer growth and lower operating expenses were major positives.
- Leadership expects profitability improvement in the second half of the year."""
]

# If snippets were generated dynamically, create reference summaries for them
# using simple manual-style fallback if lengths mismatch
if len(earnings_snippets) != len(reference_summaries):
    reference_summaries = [
        "Revenue performance, key business driver, and management outlook were discussed.",
        "Revenue performance, business trends, and future guidance were highlighted.",
        "Financial results, growth drivers, and future outlook were summarized."
    ]


# ------------------------------------------------------------
# Generate zero-shot and few-shot summaries
# ------------------------------------------------------------
zero_shot_outputs = []
few_shot_outputs = []

print("ZERO-SHOT SUMMARIES:\n")
for i, snippet in enumerate(earnings_snippets, start=1):
    result = zero_shot_chain.invoke({"snippet": snippet})
    summary = result.strip()
    zero_shot_outputs.append(summary)

    print(f"Snippet {i}:\n{summary}\n")


print("\n" + "-" * 80 + "\n")

print("FEW-SHOT SUMMARIES:\n")
for i, snippet in enumerate(earnings_snippets, start=1):
    result = few_shot_chain.invoke({"snippet": snippet})
    summary = result.strip()
    few_shot_outputs.append(summary)

    print(f"Snippet {i}:\n{summary}\n")


# ------------------------------------------------------------
# C) Evaluate the response with ROUGE-L
# ------------------------------------------------------------
print("\n" + "=" * 80)
print("ROUGE-L EVALUATION")
print("=" * 80 + "\n")

scorer = rouge_scorer.RougeScorer(['rougeL'], use_stemmer=True)

evaluation_rows = []

for i in range(len(earnings_snippets)):
    reference = reference_summaries[i] if i < len(reference_summaries) else ""

    zero_score = scorer.score(reference, zero_shot_outputs[i])["rougeL"].fmeasure
    few_score = scorer.score(reference, few_shot_outputs[i])["rougeL"].fmeasure

    evaluation_rows.append({
        "Snippet": i + 1,
        "ROUGE-L Zero-shot": round(zero_score, 4),
        "ROUGE-L Few-shot": round(few_score, 4)
    })

evaluation_df = pd.DataFrame(evaluation_rows)
print(evaluation_df)

avg_zero = evaluation_df["ROUGE-L Zero-shot"].mean()
avg_few = evaluation_df["ROUGE-L Few-shot"].mean()

print("\nAverage ROUGE-L (Zero-shot):", round(avg_zero, 4))
print("Average ROUGE-L (Few-shot):", round(avg_few, 4))


# ============================================================
# PART 2: 5-CLASS TICKET CLASSIFIER WITH REASONING
# ============================================================

print("\n" + "=" * 80)
print("PART 2: 5-CLASS TICKET CLASSIFIER")
print("=" * 80 + "\n")


# ------------------------------------------------------------
# Sample support tickets
# ------------------------------------------------------------
support_tickets = [
    "I was charged twice for my monthly subscription and need help fixing the invoice.",
    "The mobile app crashes every time I try to upload a document.",
    "I canceled my order yesterday and want my money returned.",
    "How do I update my profile details in the portal?",
    "My account has been locked for a week and no one from support has responded. This is urgent."
]


# ------------------------------------------------------------
# Classification prompt with reasoning-style output
# ------------------------------------------------------------
ticket_classifier_template = """
You are a customer support classifier.

You must classify the following support ticket into exactly one of these 5 classes:
1. Billing
2. Tech
3. Refund
4. General
5. Escalate

Instructions:
- First identify the core issue.
- Then provide a short reasoning summary.
- Then provide the final class label.
- Keep the reasoning concise and relevant.

Support Ticket:
{ticket}

Return the answer in this format exactly:

Reasoning:
...

Class:
...
"""

ticket_classifier_prompt = PromptTemplate(
    input_variables=["ticket"],
    template=ticket_classifier_template
)

ticket_classifier_chain = ticket_classifier_prompt | llm


# ------------------------------------------------------------
# Run classification
# ------------------------------------------------------------
classified_rows = []

for i, ticket in enumerate(support_tickets, start=1):
    result = ticket_classifier_chain.invoke({"ticket": ticket})
    response_text = result.strip()

    reasoning_match = re.search(r"Reasoning:\s*(.*?)\s*Class:", response_text, re.DOTALL)
    class_match = re.search(r"Class:\s*(.*)", response_text, re.DOTALL)

    reasoning_text = reasoning_match.group(1).strip() if reasoning_match else "Not found"
    predicted_class = class_match.group(1).strip() if class_match else "Not found"

    classified_rows.append({
        "Ticket Number": i,
        "Ticket": ticket,
        "Reasoning": reasoning_text,
        "Predicted Class": predicted_class
    })

classification_df = pd.DataFrame(classified_rows)

print(classification_df.to_string(index=False))


# ------------------------------------------------------------
# Save outputs to files (optional, useful for assignment/demo)
# ------------------------------------------------------------
evaluation_df.to_csv("rouge_l_scores.csv", index=False)
classification_df.to_csv("ticket_classification_results.csv", index=False)

with open("generated_earnings_snippets.txt", "w", encoding="utf-8") as f:
    f.write(generated_snippets_text)

with open("zero_shot_summaries.txt", "w", encoding="utf-8") as f:
    for i, text in enumerate(zero_shot_outputs, start=1):
        f.write(f"Snippet {i} Zero-shot Summary:\n{text}\n\n")

with open("few_shot_summaries.txt", "w", encoding="utf-8") as f:
    for i, text in enumerate(few_shot_outputs, start=1):
        f.write(f"Snippet {i} Few-shot Summary:\n{text}\n\n")

print("\nFiles saved:")
print("- rouge_l_scores.csv")
print("- ticket_classification_results.csv")
print("- generated_earnings_snippets.txt")
print("- zero_shot_summaries.txt")
print("- few_shot_summaries.txt")
