import streamlit as st 
import json
import os
import time
import requests
import pandas as pd


def load_json(filename):
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def build_prompt_from_file(question_text):
    with open('config/prompt_template.txt', 'r', encoding='utf-8') as f:
        template = f.read()
    
    full_prompt = template + question_text
    return full_prompt


def ask_llm(question):
    url = "https://kolby-unpondered-sniffingly.ngrok-free.dev/predict"

    prompt = build_prompt_from_file(question)

    try:
        response = requests.post(
            url,
            json={"inputs": prompt},
            timeout=120        )

        print(response.status_code)
        print(response.text)

        if response.status_code == 200:
            data = response.json()

            if isinstance(data, list) and len(data) > 0:
                output = data[0].get("generated_text", "")
                return output, 200

            return "Empty response", 500

        return f"Error {response.status_code}", response.status_code

    except Exception as e:
        return str(e), 500


# Web Interface
st.set_page_config(page_title="ORKG Benchmark Engine", layout="wide")

st.title("ORKG SPARQL Benchmark Engine")
st.markdown("Update your JSON files to add new models or questions.")


# 1. Check Token
token = os.getenv('HF_TOKEN')
if not token:
    st.error("HF_TOKEN not found in environment variables!")
    st.stop()


# 2. Sidebar Settings
st.sidebar.header("Settings")

config = load_json('config/models_config.json')
benchmark = load_json('config/nlp4re_benchmark_clean.json')

if st.sidebar.button("Refresh Files"):
    st.rerun()

models = config.get('models_to_test', [])

st.sidebar.write(f"Models found: {len(models)}")
st.sidebar.write(f"Questions found: {len(benchmark)}")


# 3. Run Benchmark
if st.button("Start Benchmark Run"):

    if not models or not benchmark:
        st.error("No models or benchmark questions found!")
        st.stop()

    results = []
    progress_bar = st.progress(0)
    status_text = st.empty()

    total_steps = len(models) * len(benchmark)
    step = 0

    for model in models:
        for q in benchmark:

            status_text.text(f"Testing {model['name']} with Question {q['id']}...")

            start = time.time()
            prediction, status = ask_llm(
                q['question']
            )

            duration = time.time() - start

            results.append({
                "Model": model['name'],
                "ID": q['id'],
                "Question": q['question'],
                "Prediction": prediction,
                "Gold Standard": q['gold_query'],
                "Time (s)": round(duration, 2)
            })

            step += 1
            progress_bar.progress(step / total_steps)

            time.sleep(0.5)


    # 4. Display Results
    st.success("Benchmark Finished!")

    df = pd.DataFrame(results)

    st.subheader("Detailed Results")
    st.dataframe(df, use_container_width=True)


    # Performance Summary (Fix für KeyError)
    st.subheader("Performance Summary")

    if not df.empty and "Model" in df.columns:
        avg_times = df.groupby("Model")["Time (s)"].mean()
        st.bar_chart(avg_times)
    else:
        st.warning("No benchmark results available.")


    # Save Results
    with open('benchmark_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=4)

    st.info("Results saved to benchmark_results.json")