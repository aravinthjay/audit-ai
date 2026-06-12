# EXTENSION: Re-Ranking with Cohere Rerank API
# Compare MRR before vs after re-ranking for top-10 results

if not COHERE_API_KEY:
    print("COHERE_API_KEY is empty -- skipping extension task.")
else:
    import cohere

    co = cohere.Client(COHERE_API_KEY)

    # Evaluation set: (query, expected relevant title)
    EVAL_SET = [
        ("How does FAISS handle approximate nearest neighbour search?", "FAISS"),
        ("What is the difference between BM25 and dense retrieval?", "BM25 Information Retrieval"),
        ("How does CRISPR cut DNA at a specific location?", "CRISPR Gene Editing"),
        ("What triggered the COVID-19 pandemic?", "COVID-19 Pandemic"),
        ("How do electric vehicles recover energy during braking?", "Electric Vehicles"),
    ]

    def compute_mrr(retrieved_docs, relevant_title):
        for rank, doc in enumerate(retrieved_docs, start=1):
            if relevant_title.lower() in doc.metadata.get("title", "").lower():
                return 1.0 / rank
        return 0.0

    def rerank_with_cohere(query, top_k_retrieve=10, top_k_final=10):
        initial_docs = faiss_store.similarity_search(query, k=top_k_retrieve)
        passages = [doc.page_content for doc in initial_docs]

        rerank_response = co.rerank(
            model="rerank-english-v3.0",
            query=query,
            documents=passages,
            top_n=top_k_final
        )

        reranked_docs = [initial_docs[item.index] for item in rerank_response.results]
        return initial_docs, reranked_docs

    mrr_before = []
    mrr_after = []

    for query, relevant_title in EVAL_SET:
        before_docs, after_docs = rerank_with_cohere(query, top_k_retrieve=10, top_k_final=10)

        mrr_before.append(compute_mrr(before_docs, relevant_title))
        mrr_after.append(compute_mrr(after_docs, relevant_title))

    avg_mrr_before = np.mean(mrr_before)
    avg_mrr_after = np.mean(mrr_after)

    print(f"MRR@10 Before Re-ranking : {avg_mrr_before:.3f}")
    print(f"MRR@10 After Re-ranking  : {avg_mrr_after:.3f}")
    print(f"Improvement              : +{(avg_mrr_after - avg_mrr_before) * 100:.1f} percentage points")

    # Plot comparison
    plt.figure(figsize=(6, 4))
    bars = plt.bar(
        ["Before Re-rank", "After Cohere Re-rank"],
        [avg_mrr_before, avg_mrr_after],
        color=["#DD8452", "#55A868"],
        edgecolor="white"
    )

    plt.title("MRR@10 Before vs After Cohere Re-rank", fontweight="bold")
    plt.ylabel("Mean Reciprocal Rank")
    plt.ylim(0, 1.1)
    plt.grid(axis="y", alpha=0.3)

    for bar, value in zip(bars, [avg_mrr_before, avg_mrr_after]):
        plt.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.02,
            f"{value:.3f}",
            ha="center",
            fontweight="bold"
        )

    plt.tight_layout()
    plt.savefig("mrr_comparison.png", dpi=150, bbox_inches="tight")
    plt.show()

    print("Saved mrr_comparison.png")