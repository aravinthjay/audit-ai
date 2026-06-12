from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from anthropic import Anthropic
import os

# ---------------- FAQ DATA ----------------
faqs = [
    "What is RAG? RAG combines retrieval and generation for grounded answers.",
    "What is FAISS? FAISS is a vector database for similarity search.",
    "What are embeddings? Embeddings convert text into numerical vectors.",
    "What is LangChain? LangChain helps build LLM-powered applications.",
    "What is cosine similarity? It measures similarity between vectors.",
    "Why use RAG? To reduce hallucinations and improve factual accuracy.",
    "What is Claude? Claude is an LLM developed by Anthropic.",
    "What is vector search? Finding similar documents using embeddings.",
    "What is prompt engineering? Designing prompts to improve LLM output.",
    "What is chunking? Splitting large documents into smaller sections."
]

# ---------------- INDEXING ----------------
embeddings = OpenAIEmbeddings(
    api_key=os.getenv("OPENAI_API_KEY")
)

vectorstore = FAISS.from_texts(faqs, embeddings)

# ---------------- CLAUDE CLIENT ----------------
client = Anthropic(
    api_key=os.getenv("ANTHROPIC_API_KEY")
)

print("\n Smart FAQ Bot Ready!")
print("Type 'exit' to quit\n")

# ---------------- CLI LOOP ----------------
while True:
    query = input("You: ")

    if query.lower() == "exit":
        break

    docs_scores = vectorstore.similarity_search_with_score(
        query,
        k=2
    )

    context = "\n".join(
        [doc.page_content for doc, _ in docs_scores]
    )

    prompt = f"""
Answer ONLY using the FAQ context below.

FAQ Context:
{context}

Question:
{query}

Provide a concise answer.
"""

    response = client.messages.create(
        model="claude-3-5-sonnet-latest",
        max_tokens=150,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    print("\nBot:", response.content[0].text)

    print("\nTop Matches:")
    for doc, score in docs_scores:
        print(f"Score={score:.4f} | {doc.page_content}")

    print("-" * 50)