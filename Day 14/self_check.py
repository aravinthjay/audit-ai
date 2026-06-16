import spacy
from selfcheckgpt.modeling_selfcheck import SelfCheckBERTScore

# 1. Main generation you want to check, and 3 alternative stochastic samples from the LLM
main_generation = "Michael Jordan was born in Brooklyn, New York. He played for the Chicago Bulls."
sampled_passages = [
"Michael Jordan is a legendary basketball player who spent most of his career with the Bulls. He was born in Brooklyn.",
"Jordan was born in New York City. He is widely considered the greatest basketball player of all time.",
"Born in Brooklyn, Michael Jordan became a global icon playing for the Chicago Bulls."
]

# 2. Tokenize the main text into individual sentences using SpaCy
nlp = spacy.load("en_core_web_sm")
sentences = [sent.text.strip() for sent in nlp(main_generation).sents]

# 3. Initialize SelfCheckGPT using its BERTScore approach
selfcheck_bert = SelfCheckBERTScore(rescale_with_baseline=True)

# 4. Predict hallucination scores per sentence (Higher score = More likely to be a hallucination)
sent_scores = selfcheck_bert.predict(
sentences=sentences,
sampled_passages=sampled_passages
)

# 5. Output results
for sent, score in zip(sentences, sent_scores):
    print(f"Sentence: '{sent}'")
    print(f"Hallucination Score: {score:.4f} (0=Consistent, 1=Inconsistent/Hallucinated)\n")