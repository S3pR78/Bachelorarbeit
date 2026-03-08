import json
import requests


API_URL = "https://kolby-unpondered-sniffingly.ngrok-free.dev/ask"

def run_benchmark():
    # load template
    with open('config/prompt_template.txt', 'r', encoding='utf-8') as f:
        template_text = f.read()

    # load the benchmark
    with open('config/benchmark.json', 'r', encoding='utf-8') as f:
        benchmark_data = json.load(f)

    results = []

    print(f"Starting process for {len(benchmark_data)} questions...")

    for item in benchmark_data:
        question_id = item.get("id")
        question_text = item.get("question")
        
        print(f"Processing ID {question_id}...")

        # craeete payload
        payload = {
            "instruction": template_text,
            "question": question_text
        }

        try:
            
            response = requests.post(API_URL, json=payload)
            
            if response.status_code == 200:
                generated_sparql = response.json().get("sparql_query")
                
                
                results.append({
                    "id": question_id,
                    "question": question_text,
                    "generated_query": generated_sparql
                })
            else:
                print(f"Error at ID {question_id}: Server returned {response.status_code}")
                
        except Exception as e:
            print(f"Connection failed at ID {question_id}: {e}")

    
    with open('config/results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=4, ensure_ascii=False)
    
    print("\nFinished! All answers are saved in 'results.json'.")

if __name__ == "__main__":
    run_benchmark()