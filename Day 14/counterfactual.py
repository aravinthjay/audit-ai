from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
import torch

print("Loading zero-shot classifier (no fine-tuning required for demo)...")
# In a real scenario, you'd fine-tune on labelled domain data.
# Here we use zero-shot classification to demonstrate the concept.
classifier = pipeline(
    "zero-shot-classification",
    model="facebook/bart-large-mnli",
    device=0 if torch.cuda.is_available() else -1
)

INTENT_LABELS = [
    "safe credit inquiry",
    "discriminatory bias request",
    "PII data extraction",
    "jailbreak or policy bypass",
    "financial misinformation"
]

def classify_intent(text: str) -> dict:
    result = classifier(text, INTENT_LABELS, multi_label=False)
    return dict(zip(result['labels'], [round(s, 3) for s in result['scores']]))

print("\n🤗 INTENT CLASSIFICATION RESULTS")
print("-" * 80)
for prompt in test_prompts[:4]:
    scores = classify_intent(prompt)
    top_intent = max(scores, key=scores.get)
    print(f"Prompt: {prompt[:70]}")
    print(f"  Top intent: '{top_intent}'  (score: {scores[top_intent]:.3f})")
