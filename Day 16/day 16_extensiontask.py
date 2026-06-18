# ─── Extension: Hybrid Retrieval + Re-Ranker ─────────────────────────────────

# Steps 1-3: BM25 + dense ensemble


from langchain_community.retrievers import BM25Retriever
from langchain.retrievers import EnsembleRetriever

bm25_retriever = BM25Retriever.from_documents(chunks)
bm25_retriever.k = 4

hybrid_retriever = EnsembleRetriever(
    retrievers=[retriever, bm25_retriever],
    weights=[0.6, 0.4]  # 60% dense, 40% BM25
)

hybrid_results = hybrid_retriever.invoke('Apple net income fiscal 2023')
print(f'Hybrid retrieved {len(hybrid_results)} chunks')
for r in hybrid_results:
    print(f'  - {r.metadata["source"]}: {r.page_content[:80]}...')
print('✅ Steps 1-3 complete: hybrid (dense + BM25) retriever built')

# Step 4: Cross-encoder re-ranker on top of the hybrid shortlist
# (sentence-transformers is already installed from Step 0)
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import CrossEncoderReranker
from langchain_community.cross_encoders import HuggingFaceCrossEncoder

print('⏳ Loading cross-encoder (cross-encoder/ms-marco-MiniLM-L-6-v2)...')
cross_encoder_model = HuggingFaceCrossEncoder(model_name='cross-encoder/ms-marco-MiniLM-L-6-v2')
reranker = CrossEncoderReranker(model=cross_encoder_model, top_n=4)

hybrid_rerank_retriever = ContextualCompressionRetriever(
    base_compressor=reranker,
    base_retriever=hybrid_retriever,
)

reranked_results = hybrid_rerank_retriever.invoke('Apple net income fiscal 2023')
print(f'✅ Re-ranked down to {len(reranked_results)} chunks')
for r in reranked_results:
    score = r.metadata.get('relevance_score')
    print(f'  - {r.metadata["source"]} (score={score:.3f}): {r.page_content[:80]}...')

# Step 5: Re-run RAGAS across dense vs hybrid vs hybrid+rerank
# ⚠️ Makes a lot of API calls (3 strategies × 5 queries, plus RAGAS's internal
# LLM calls for scoring) -- expect a few minutes and a real chunk of token budget
import time
import pandas as pd
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_recall, context_precision

def build_chain(active_retriever):
    return (
        {"context": active_retriever | format_docs, "question": RunnablePassthrough()}
        | RAG_PROMPT | llm | StrOutputParser()
    )

strategies = {
    'dense': retriever,
    'hybrid': hybrid_retriever,
    'hybrid_rerank': hybrid_rerank_retriever,
}

comparison_runs = {}

for name, active_retriever in strategies.items():
    print(f'\n🔧 Running strategy: {name}')
    chain = build_chain(active_retriever)

    answers, latencies = [], []
    for q in TEST_QUERIES:
        t0 = time.time()
        a = chain.invoke(q)
        latencies.append(time.time() - t0)
        answers.append(a)

    contexts = [[d.page_content for d in active_retriever.invoke(q)] for q in TEST_QUERIES]

    eval_ds = Dataset.from_dict({
        'question': TEST_QUERIES,
        'answer': answers,
        'contexts': contexts,
        'ground_truth': GROUND_TRUTHS,
    })

    print(f'⏳ Scoring {name} with RAGAS...')
    scores = evaluate(
        dataset=eval_ds,
        metrics=[faithfulness, answer_relevancy, context_recall, context_precision],
        llm=llm,
        embeddings=az_embeddings,
    )

    comparison_runs[name] = {
        'avg_latency_s': sum(latencies) / len(latencies),
        'scores_df': scores.to_pandas(),
    }
    print(f'   Avg latency: {comparison_runs[name]["avg_latency_s"]:.2f}s')
    print(scores)

print('\n✅ All three strategies evaluated')

# Build the comparison table
summary_rows = []
for name, run in comparison_runs.items():
    sdf = run['scores_df']
    summary_rows.append({
        'strategy': name,
        'avg_latency_s': round(run['avg_latency_s'], 2),
        'faithfulness': round(sdf['faithfulness'].mean(), 3),
        'answer_relevancy': round(sdf['answer_relevancy'].mean(), 3),
        'context_recall': round(sdf['context_recall'].mean(), 3),
        'context_precision': round(sdf['context_precision'].mean(), 3),
    })

comparison_df = pd.DataFrame(summary_rows)
print('📊 Strategy comparison:')
print(comparison_df.to_string(index=False))

met_target = comparison_df[comparison_df['faithfulness'] > 0.88]['strategy'].tolist()
print(f"\n🎯 Target (faithfulness > 0.88) met by: {met_target or 'none yet -- try tuning weights or top_n'}")

# Step 6: Present -- faithfulness vs latency
import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(7, 5))
colors = {'dense': '#4C72B0', 'hybrid': '#DD8452', 'hybrid_rerank': '#55A868'}

for _, row in comparison_df.iterrows():
    ax.scatter(row['avg_latency_s'], row['faithfulness'], s=160,
               color=colors.get(row['strategy'], 'gray'), label=row['strategy'], zorder=3)
    ax.annotate(row['strategy'], (row['avg_latency_s'], row['faithfulness']),
                textcoords='offset points', xytext=(8, 6))

ax.axhline(0.88, color='gray', linestyle='--', linewidth=1, label='Target (0.88)')
ax.set_xlabel('Average latency (s)')
ax.set_ylabel('Faithfulness')
ax.set_title('Faithfulness vs Latency: Dense vs Hybrid vs Hybrid + Re-rank')
ax.legend()
plt.tight_layout()
plt.savefig('faithfulness_vs_latency.png', dpi=150)
plt.show()

print('✅ Saved plot to faithfulness_vs_latency.png')