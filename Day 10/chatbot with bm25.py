import re
import math
from rank_bm25 import BM25Okapi

# -------------------------------------------------------
# 1. Company Knowledge Base
# -------------------------------------------------------
company_knowledge_base = [
    {
        "id": 0,
        "question": "What is the leave policy?",
        "answer": "Employees can take 20 paid leaves per year. Sick leave and casual leave are included in this policy."
    },
    {
        "id": 1,
        "question": "How do I apply for work from home?",
        "answer": "You can apply for work from home through the HR portal and get approval from your manager."
    },
    {
        "id": 2,
        "question": "What are the office working hours?",
        "answer": "The standard office working hours are from 9:00 AM to 6:00 PM, Monday to Friday."
    },
    {
        "id": 3,
        "question": "How do I reset my company email password?",
        "answer": "You can reset your company email password using the self-service password reset portal or contact IT support."
    },
    {
        "id": 4,
        "question": "What is the reimbursement policy?",
        "answer": "Employees can submit travel and food reimbursement claims through the finance portal with valid bills."
    },
    {
        "id": 5,
        "question": "How can I contact HR?",
        "answer": "You can contact HR by email at hr@company.com or by visiting the HR helpdesk."
    },
    {
        "id": 6,
        "question": "What should I do if my laptop is not working?",
        "answer": "If your laptop is not working, raise a ticket with the IT support team through the service portal."
    },
    {
        "id": 7,
        "question": "Where can I find the company holiday list?",
        "answer": "The company holiday list is available in the HR portal under the holidays section."
    }
]

# -------------------------------------------------------
# 2. Ground Truth Test Set
#    Each query has the correct relevant document ID
# -------------------------------------------------------
ground_truth_data = [
    {"query": "leave policy", "relevant_ids": [0]},
    {"query": "work from home request", "relevant_ids": [1]},
    {"query": "office hours", "relevant_ids": [2]},
    {"query": "forgot email password", "relevant_ids": [3]},
    {"query": "travel reimbursement", "relevant_ids": [4]},
    {"query": "hr contact", "relevant_ids": [5]},
    {"query": "laptop issue", "relevant_ids": [6]},
    {"query": "company holidays", "relevant_ids": [7]}
]

# -------------------------------------------------------
# 3. Sample Prompts for Testing
# -------------------------------------------------------
sample_prompts = [
    "leave policy",
    "how to apply work from home",
    "office timing",
    "reset email password",
    "reimbursement claim",
    "contact hr",
    "laptop not working",
    "holiday list"
]

# -------------------------------------------------------
# 4. Text Cleaning Function
# -------------------------------------------------------
def clean_text(text):
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", "", text)
    return text.split()

# -------------------------------------------------------
# 5. Prepare Documents for BM25
#    Combine question + answer into one searchable document
# -------------------------------------------------------
documents = []
for item in company_knowledge_base:
    combined_text = item["question"] + " " + item["answer"]
    documents.append(combined_text)

tokenized_documents = [clean_text(doc) for doc in documents]

# Create BM25 model
bm25_model = BM25Okapi(tokenized_documents)

# -------------------------------------------------------
# 6. Retrieve Top-K Matching Results
# -------------------------------------------------------
def retrieve_top_k(user_query, top_k=5):
    tokenized_query = clean_text(user_query)
    scores = bm25_model.get_scores(tokenized_query)

    ranked_indexes = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)

    top_results = []
    for index in ranked_indexes[:top_k]:
        top_results.append({
            "id": company_knowledge_base[index]["id"],
            "question": company_knowledge_base[index]["question"],
            "answer": company_knowledge_base[index]["answer"],
            "score": float(scores[index])
        })

    return top_results

# -------------------------------------------------------
# 7. Helper Function - Get relevant IDs from ground truth
#    for a given user query
# -------------------------------------------------------
def get_ground_truth_relevant_ids(user_query):
    normalized_user_query = user_query.strip().lower()

    for item in ground_truth_data:
        if item["query"].strip().lower() == normalized_user_query:
            return item["relevant_ids"]

    return None

# -------------------------------------------------------
# 8. Reciprocal Rank for one query
# -------------------------------------------------------
def calculate_reciprocal_rank(retrieved_ids, relevant_ids):
    for rank_position, document_id in enumerate(retrieved_ids, start=1):
        if document_id in relevant_ids:
            return 1 / rank_position
    return 0.0

# -------------------------------------------------------
# 9. Mean Reciprocal Rank (MRR) for all test queries
# -------------------------------------------------------
def calculate_mrr(test_data, top_k=5):
    reciprocal_ranks = []

    for item in test_data:
        query = item["query"]
        relevant_ids = item["relevant_ids"]

        retrieved_results = retrieve_top_k(query, top_k=top_k)
        retrieved_ids = [result["id"] for result in retrieved_results]

        rr = calculate_reciprocal_rank(retrieved_ids, relevant_ids)
        reciprocal_ranks.append(rr)

    if len(reciprocal_ranks) == 0:
        return 0.0

    return sum(reciprocal_ranks) / len(reciprocal_ranks)

# -------------------------------------------------------
# 10. DCG Calculation
# -------------------------------------------------------
def dcg(relevance_scores):
    dcg_value = 0.0
    for index, rel in enumerate(relevance_scores):
        position = index + 1
        dcg_value += rel / math.log2(position + 1)
    return dcg_value

# -------------------------------------------------------
# 11. NDCG for one query
# -------------------------------------------------------
def calculate_ndcg_for_query(retrieved_ids, relevant_ids, top_k=5):
    actual_relevance = []

    for doc_id in retrieved_ids[:top_k]:
        if doc_id in relevant_ids:
            actual_relevance.append(1)
        else:
            actual_relevance.append(0)

    ideal_relevance = sorted(actual_relevance, reverse=True)

    actual_dcg = dcg(actual_relevance)
    ideal_dcg = dcg(ideal_relevance)

    if ideal_dcg == 0:
        return 0.0

    return actual_dcg / ideal_dcg

# -------------------------------------------------------
# 12. Average NDCG for all test queries
# -------------------------------------------------------
def calculate_average_ndcg(test_data, top_k=5):
    ndcg_scores = []

    for item in test_data:
        query = item["query"]
        relevant_ids = item["relevant_ids"]

        retrieved_results = retrieve_top_k(query, top_k=top_k)
        retrieved_ids = [result["id"] for result in retrieved_results]

        ndcg_score = calculate_ndcg_for_query(retrieved_ids, relevant_ids, top_k=top_k)
        ndcg_scores.append(ndcg_score)

    if len(ndcg_scores) == 0:
        return 0.0

    return sum(ndcg_scores) / len(ndcg_scores)

# -------------------------------------------------------
# 13. Chatbot Response Function
#     Updated:
#     - shows BM25 score
#     - shows RR and NDCG if the query is in ground truth
# -------------------------------------------------------
def get_chatbot_response(user_query):
    results = retrieve_top_k(user_query, top_k=5)

    if len(results) == 0 or results[0]["score"] <= 0:
        return "Sorry, I could not find a matching answer in the company knowledge base."

    best_result = results[0]

    response = (
        f"Most relevant answer:\n"
        f"{best_result['answer']}\n\n"
        f"Matched Question: {best_result['question']}\n"
        f"BM25 Score: {best_result['score']:.4f}"
    )

    # Check if this query exists in ground truth
    relevant_ids = get_ground_truth_relevant_ids(user_query)

    if relevant_ids is not None:
        retrieved_ids = [item["id"] for item in results]

        rr = calculate_reciprocal_rank(retrieved_ids, relevant_ids)
        ndcg_value = calculate_ndcg_for_query(retrieved_ids, relevant_ids, top_k=5)

        response += (
            f"\nReciprocal Rank (RR): {rr:.4f}"
            f"\nNDCG: {ndcg_value:.4f}"
        )
    else:
        response += (
            "\nReciprocal Rank (RR): Not available"
            "\nNDCG: Not available"
            "\nReason: This query is not defined in the ground-truth test set."
        )

    return response

# -------------------------------------------------------
# 14. Show Sample Prompt Results
# -------------------------------------------------------
def show_sample_prompt_results():
    print("\n================ SAMPLE PROMPT RESULTS ================\n")

    for prompt in sample_prompts:
        print(f"User Prompt: {prompt}")
        results = retrieve_top_k(prompt, top_k=3)

        for rank_number, item in enumerate(results, start=1):
            print(f"Rank {rank_number}")
            print(f"Question : {item['question']}")
            print(f"Answer   : {item['answer']}")
            print(f"Score    : {item['score']:.4f}")
            print("-" * 50)

        print("=" * 60)

# -------------------------------------------------------
# 15. Search Evaluation
#     Prints overall MRR and average NDCG
# -------------------------------------------------------
def evaluate_search_engine():
    print("\n================ SEARCH EVALUATION ====================\n")

    mrr_score = calculate_mrr(ground_truth_data, top_k=5)
    ndcg_score = calculate_average_ndcg(ground_truth_data, top_k=5)

    print(f"Overall MRR  (Mean Reciprocal Rank)       : {mrr_score:.4f}")
    print(f"Overall NDCG (Average Ranking Quality)    : {ndcg_score:.4f}")

    print("\nDetailed Per Query Evaluation:\n")

    for item in ground_truth_data:
        query = item["query"]
        relevant_ids = item["relevant_ids"]

        retrieved_results = retrieve_top_k(query, top_k=5)
        retrieved_ids = [result["id"] for result in retrieved_results]

        rr = calculate_reciprocal_rank(retrieved_ids, relevant_ids)
        ndcg_value = calculate_ndcg_for_query(retrieved_ids, relevant_ids, top_k=5)

        print(f"Query          : {query}")
        print(f"Retrieved IDs  : {retrieved_ids}")
        print(f"Relevant IDs   : {relevant_ids}")
        print(f"RR             : {rr:.4f}")
        print(f"NDCG           : {ndcg_value:.4f}")
        print("-" * 60)

# -------------------------------------------------------
# 16. Interactive Chatbot
# -------------------------------------------------------
def run_chatbot():
    print("\n================ COMPANY BM25 CHATBOT =================")
    print("Type 'exit' to stop the chatbot.\n")
    print("Try queries such as:")
    print("- leave policy")
    print("- work from home request")
    print("- office hours")
    print("- forgot email password")
    print("- travel reimbursement")
    print("- hr contact")
    print("- laptop issue")
    print("- company holidays\n")

    while True:
        user_input = input("You: ").strip()

        if user_input.lower() == "exit":
            print("Bot: Goodbye!")
            break

        response = get_chatbot_response(user_input)
        print("\nBot:")
        print(response)
        print()

# -------------------------------------------------------
# 17. Main Program
# -------------------------------------------------------
if __name__ == "__main__":
    show_sample_prompt_results()
    evaluate_search_engine()
    run_chatbot()
