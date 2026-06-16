from factscore.factscorer import FactScorer

# Initialize FactScorer
# Note: To run locally, you will need to download their processed Wikipedia dump
# or register your own knowledge source database.
fs = FactScorer(openai_key="your-openai-api-key")

# Define your data
topics = ["Alan Turing"]
generations = ["Alan Turing was a British mathematician. He was born in 1912 and died in 1954."]

# Calculate the score
# gamma is the length penalty parameter
out = fs.get_score(topics, generations, gamma=10)

print(f"FactScore: {out['score']}") # Final length-penalized score
print(f"Initial Score (w/o penalty): {out['init_score']}")
print(f"Avg Number of Facts: {out['num_facts_per_response']}")