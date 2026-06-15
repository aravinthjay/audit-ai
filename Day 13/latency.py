import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.metrics.pairwise import cosine_similarity

# ---------------------------------------------------
# 8 Evaluation Queries
# ---------------------------------------------------
EVAL_8 = [
    ("What is retrieval augmented generation?", "Retrieval-Augmented Generation"),
    ("How does FAISS work?", "FAISS"),
    ("What is BM25?", "BM25"),
    ("Explain transformer architecture", "Transformer"),
    ("How does CRISPR edit DNA?", "CRISPR"),
    ("What causes climate change?", "Climate Change"),
    ("What is hybrid search?", "Azure AI Search"),
    ("What are embeddings?", "Embeddings")
]

results = []

for query, expected_title in EVAL_8:

    # ---------------------------------------
    # Context Precision
    # ---------------------------------------
    docs = azure_hybrid_search(query, top_k=5)

    relevant = sum(
        1 for d in docs
        if expected_title.lower() in d["title"].lower()
    )

    precision = relevant / len(docs)

    # ---------------------------------------
    # Run RAG
    # ---------------------------------------
    rag = rag_answer(query)

    answer = rag.answer

    # ---------------------------------------
    # Answer Relevance
    # Query ↔ Answer Similarity
    # ---------------------------------------
    query_vec = embeddings.embed_query(query)
    answer_vec = embeddings.embed_query(answer)

    relevance = cosine_similarity(
        [query_vec],
        [answer_vec]
    )[0][0]

    # ---------------------------------------
    # Token Estimation
    # ---------------------------------------
    total_tokens = (
        len(query.split()) +
        len(answer.split())
    ) * 1.3

    results.append({
        "Query": query,
        "Context_Precision": round(precision,3),
        "Answer_Relevance": round(float(relevance),3),
        "Total_Tokens": int(total_tokens),
        "Embed_ms": round(rag.embed_ms,2),
        "Retrieve_ms": round(rag.retrieve_ms,2),
        "Generate_ms": round(rag.generate_ms,2),
        "Total_ms": round(rag.total_ms,2)
    })

# ---------------------------------------------------
# DataFrame
# ---------------------------------------------------
eval_df = pd.DataFrame(results)

print("\nPER QUERY RESULTS")
print(eval_df.to_string(index=False))

# ---------------------------------------------------
# Aggregate Metrics
# ---------------------------------------------------
avg_precision = eval_df["Context_Precision"].mean()

avg_relevance = eval_df["Answer_Relevance"].mean()

avg_tokens = eval_df["Total_Tokens"].mean()

avg_latency = eval_df["Total_ms"].mean()

p95_latency = np.percentile(
    eval_df["Total_ms"],
    95
)

std_latency = eval_df["Total_ms"].std()

cv_latency = (
    std_latency /
    avg_latency
) * 100

summary = pd.DataFrame({
    "Metric":[
        "Average Context Precision",
        "Average Answer Relevance",
        "Average Tokens",
        "Average Latency (ms)",
        "P95 Latency (ms)",
        "Latency Std Dev",
        "Latency CV (%)"
    ],
    "Value":[
        round(avg_precision,3),
        round(avg_relevance,3),
        round(avg_tokens,0),
        round(avg_latency,2),
        round(p95_latency,2),
        round(std_latency,2),
        round(cv_latency,2)
    ]
})

print("\nSUMMARY")
print(summary.to_string(index=False))

# ---------------------------------------------------
# Latency Plot
# ---------------------------------------------------
plt.figure(figsize=(10,5))

plt.plot(
    range(1,9),
    eval_df["Total_ms"],
    marker="o"
)

plt.xticks(
    range(1,9),
    [f"Q{i}" for i in range(1,9)]
)

plt.xlabel("Queries")
plt.ylabel("Latency (ms)")
plt.title("Latency Variation Across 8 Queries")
plt.grid(True)

plt.show()