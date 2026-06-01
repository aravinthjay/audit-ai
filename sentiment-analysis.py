"""
Day 1 Coding Activity — Sentiment Analysis with Hugging Face
EY Workshop | Participant: [Your Name]
"""

from transformers import pipeline

# TODO 1: Initialise a sentiment-analysis pipeline
# Hint: classifier = pipeline("sentiment-analysis")
classifier = pipeline("sentiment-analysis")

# Sample sentences relevant to consulting work
sentences = [
    "The client was very satisfied with the delivery.",
    "The project is significantly over budget and behind schedule.",
    "The new regulatory framework presents both risks and opportunities.",
    # TODO 2: Add ONE sentence of your own — make it work-relevant
    "The team delivered high-quality insights under tight deadlines."
]

# TODO 3: Run the classifier on all sentences and print results
# Expected output format:
# "The client was satisfied..." → POSITIVE (0.9987)
for sentence in sentences:
    result = classifier(sentence)
    label = result[0]['label']
    score = result[0]['score']
    print(f'"{sentence[:50]}..." → {label} ({score:.4f})')