from prompt_loader import build_prompt_for_entry

entry = {
	"family": "nlp4re",
	"question": "Which papers report machine learning with at least one Machine learning algorithm but without a Metric?"
}

final_prompt = build_prompt_for_entry(entry)
print(final_prompt)