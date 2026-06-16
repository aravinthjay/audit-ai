# ============================================================
# RAG Evaluation Framework (Production-Ready)
# ============================================================

import json
import time
import pandas as pd
from typing import Dict, List
from dataclasses import dataclass
from groq import Groq
from getpass import getpass

# ------------------------------------------------------------
# Configuration
# ------------------------------------------------------------

GROQ_API_KEY = getpass("Enter Groq API Key: ")

MODEL_NAME = "llama-3.3-70b-versatile"

client = Groq(api_key=GROQ_API_KEY)

# ------------------------------------------------------------
# Test Dataset
# ------------------------------------------------------------

samples = [
    {
        "question": "What is RAG?",
        "context": """
        Retrieval Augmented Generation (RAG)
        combines document retrieval and LLMs.
        Retrieved documents are supplied to the model
        before generating an answer.
        """,
        "answer": """
        RAG retrieves relevant documents and uses
        them while generating answers.
        """
    },
    {
        "question": "Who founded Microsoft?",
        "context": """
        Microsoft was founded by Bill Gates and
        Paul Allen in 1975.
        """,
        "answer": """
        Microsoft was founded by Steve Jobs.
        """
    }
]

# ------------------------------------------------------------
# Data Model
# ------------------------------------------------------------

@dataclass
class EvaluationResult:
    metric: str
    score: int
    reason: str


# ------------------------------------------------------------
# RAG Evaluator
# ------------------------------------------------------------

class RAGEvaluator:

    def __init__(self, client, model):
        self.client = client
        self.model = model

    def _call_llm(self, prompt: str) -> Dict:

        response = self.client.chat.completions.create(
            model=self.model,
            temperature=0,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        return response.choices[0].message.content

    def evaluate_metric(
        self,
        metric_name: str,
        question: str,
        context: str,
        answer: str
    ) -> EvaluationResult:

        prompt = f"""
You are an expert RAG Evaluation Judge.

Metric: {metric_name}

Question:
{question}

Context:
{context}

Answer:
{answer}

Instructions:
Evaluate ONLY the requested metric.

Scoring:
1 = Poor
2 = Weak
3 = Average
4 = Good
5 = Excellent

Return ONLY valid JSON.

{{
    "score": <1-5>,
    "reason": "<short explanation>"
}}
"""

        try:

            result = self._call_llm(prompt)

            parsed = json.loads(result)

            return EvaluationResult(
                metric=metric_name,
                score=parsed["score"],
                reason=parsed["reason"]
            )

        except Exception as e:

            return EvaluationResult(
                metric=metric_name,
                score=0,
                reason=f"Parsing Error: {e}"
            )

    def evaluate_sample(self, sample):

        metrics = [
            "Context Relevance",
            "Answer Relevance",
            "Groundedness"
        ]

        results = {}

        for metric in metrics:

            result = self.evaluate_metric(
                metric,
                sample["question"],
                sample["context"],
                sample["answer"]
            )

            results[metric] = result

        return results


# ------------------------------------------------------------
# Evaluation Runner
# ------------------------------------------------------------

evaluator = RAGEvaluator(
    client=client,
    model=MODEL_NAME
)

all_results = []

start_time = time.time()

for idx, sample in enumerate(samples):

    sample_results = evaluator.evaluate_sample(sample)

    row = {
        "Question": sample["question"]
    }

    for metric, result in sample_results.items():

        row[f"{metric}_Score"] = result.score
        row[f"{metric}_Reason"] = result.reason

    all_results.append(row)

end_time = time.time()

# ------------------------------------------------------------
# Report
# ------------------------------------------------------------

df = pd.DataFrame(all_results)

print("\nEvaluation Results")
print(df)

print("\nAverage Scores")

score_cols = [
    c for c in df.columns
    if c.endswith("_Score")
]

print(df[score_cols].mean())

print(
    f"\nTotal Runtime: "
    f"{round(end_time-start_time,2)} sec"
)

# ------------------------------------------------------------
# Save Results
# ------------------------------------------------------------

df.to_csv(
    "rag_evaluation_results.csv",
    index=False
)

print(
    "\nResults saved to "
    "'rag_evaluation_results.csv'"
)