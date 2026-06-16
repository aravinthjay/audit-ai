from transformers import AutoModelForSequenceClassification, AutoTokenizer
import torch

# Load Vectara's open-source HHEM model
model_name = "vectara/hallucination_evaluation_model"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSequenceClassification.from_pretrained(model_name, trust_remote_code=True)

# Define context and the response to evaluate
context = "The sky is blue today because of Rayleigh scattering, and it is 72 degrees Fahrenheit outside."
generated_response = "The weather is completely cloudy and raining."

# Format the pair for the classifier
inputs = tokenizer(context, generated_response, return_tensors="pt")

# Predict consistency
with torch.no_grad():
    outputs = model(**inputs)
    # The model outputs raw logits which we convert to probabilities using softmax
    probs = torch.softmax(outputs.logits, dim=-1)

# Index 1 typically represents the probability of being factually consistent/true
consistency_score = probs[0][1].item()

print(f"HHEM Factual Consistency Score: {consistency_score:.4f}")
print(f"Hallucination Probability: {1 - consistency_score:.4f}")