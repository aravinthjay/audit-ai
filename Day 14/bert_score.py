from bert_score import score

# Define generated text and reference text
candidates = ["The city was covered in a thick blanket of snow during the winter holidays."]
references = ["Snow completely covered the town over the festive season."]

# Calculate BERTScore (Precision, Recall, F1)
# lang="en" automatically selects the default model (e.g., roberta-common)
P, R, F1 = score(candidates, references, lang="en", verbose=False)

# The outputs are PyTorch tensors containing values for each sentence pair
print(f"BERTScore Precision: {P.mean().item():.4f}")
print(f"BERTScore Recall: {R.mean().item():.4f}")
print(f"BERTScore F1-Score: {F1.mean().item():.4f}")
