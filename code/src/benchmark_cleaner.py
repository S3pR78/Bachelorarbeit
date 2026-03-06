import json
import os

# Configuration
INPUT_FILENAME = 'config/template-R1544125-2026-01-30.json'
OUTPUT_FILENAME = 'config/nlp4re_benchmark_clean.json'

def clean_benchmark_data(input_file, output_file):

    if not os.path.exists(input_file):
        print(f"Error: The file '{input_file}' was not found.")
        return

    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
        
        cleaned_list = []
        
        # Access the list of questions in the JSON structure
        questions = raw_data.get('questions', [])
        
        for entry in questions:
            # We only keep entries that contain a SPARQL query.
            # Descriptive texts or chart settings are ignored.
            sparql_query = entry.get('sparqlQuery')
            
            if sparql_query:
                # Create a streamlined dictionary for each test case
                clean_entry = {
                    "id": entry.get('id'),
                    "question": entry.get('title'), # NLP4RE uses 'title' for the question text
                    "gold_query": sparql_query.strip()
                }
                cleaned_list.append(clean_entry)
        
        # Save the filtered results to a new JSON file
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(cleaned_list, f, indent=4, ensure_ascii=False)
            
        print(f"Success! Processed {len(cleaned_list)} questions.")
        print(f"Cleaned data saved to: {output_file}")

    except Exception as e:
        print(f"An error occurred during processing: {e}")

if __name__ == "__main__":
    clean_benchmark_data(INPUT_FILENAME, OUTPUT_FILENAME)