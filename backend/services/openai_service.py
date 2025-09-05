import openai
import os
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

def explain_medical_terms(terms: list[str]) -> dict:
    if not terms:
        return {}
    prompt = (
        "You are a medical expert. For each medical term below, provide a short, simple explanation "
        "that a non-medical person can easily understand.\n" +
        "\n".join([f"{i+1}. {term}" for i, term in enumerate(terms)])
    )
    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo-16k",
            messages=[
                {"role": "system", "content": "You explain medical terminology simply."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=500,
        )
        answer = response.choices[0].message.content
        if answer is None:
            return {"error": "No response from OpenAI"}
        answer = answer.strip()

        # Optionally, post-process into {term: explanation} pairs
        explanations = {}
        for line in answer.split("\n"):
            if "." in line:
                term, explanation = line.split(".", 1)
                explanations[terms[int(term.strip())-1]] = explanation.strip()
        return explanations
    except Exception as e:
        return {"error": str(e)}

def analyze_methodology(abstract: str) -> str:
    prompt = (
        "Analyze the following research abstract to summarize the study's methodology: "
        "1) What type of study is it? 2) How many participants? 3) Methods used? 4) Any strengths/limitations? "
        "Respond with clear sections."
    )
    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a research methodology expert."},
                {"role": "user", "content": prompt + f"\n\nAbstract:\n{abstract}"}
            ],
            temperature=0.3,
            max_tokens=600,
        )
        answer = response.choices[0].message.content
        if answer is None:
            return "ERROR: No response from OpenAI"
        return answer.strip()
    except Exception as e:
        return f"ERROR: {str(e)}"

def analyze_research_gaps(abstracts: list[str], topic: str = "") -> list[str]:
    abstracts_text = "\n\n".join([f"Abstract {i+1}:\n{a}" for i, a in enumerate(abstracts)])
    prompt = (
        f"You are a medical research expert. Based on the following abstracts about '{topic or 'the topic'}', "
        "identify 3-5 important research gaps or open questions. Reply as a numbered list."
    )
    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Identify research gaps from provided abstracts."},
                {"role": "user", "content": prompt + "\n\n" + abstracts_text}
            ],
            temperature=0.3,
            max_tokens=700,
        )
        answer = response.choices[0].message.content
        if answer is None:
            return ["ERROR: No response from OpenAI"]
        answer = answer.strip()
        return [line.partition(".")[2].strip() for line in answer.split("\n") if line.strip() and line[0].isdigit()]
    except Exception as e:
        return [f"ERROR: {str(e)}"]

def generate_literature_review(abstracts: list[str], topic: str) -> str:
    abstracts_text = "\n\n".join([f"ARTICLE {i+1}:\n{a}" for i, a in enumerate(abstracts)])
    prompt = (
        f"You are a medical research expert. Write a structured literature review about '{topic}', "
        "based only on the provided article abstracts. Structure with: Introduction, Methods, Key Findings, "
        "Contradictions & Debates, Gaps, Conclusion."
    )
    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo-16k",
            messages=[
                {"role": "system", "content": "You synthesize literature reviews."},
                {"role": "user", "content": prompt + "\n\n" + abstracts_text}
            ],
            temperature=0.3,
            max_tokens=3500,
        )
        answer = response.choices[0].message.content
        if answer is None:
            return "ERROR: No response from OpenAI"
        return answer.strip()
    except Exception as e:
        return f"ERROR: {str(e)}"

def compare_studies(studies: list[dict]) -> str:
    studies_text = ""
    for i, s in enumerate(studies):
        studies_text += f"STUDY {i+1}: {s.get('title','')} | Abstract: {s.get('abstract','')}\n\n"
    prompt = (
        "Compare the provided research studies with focus on: "
        "1) Research questions 2) Methods 3) Main findings 4) Strengths & weaknesses 5) What's similar/different. "
        "Use structured sections with headings."
    )
    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo-16k",
            messages=[
                {"role": "system", "content": "You compare medical studies."},
                {"role": "user", "content": prompt + "\n\n" + studies_text}
            ],
            temperature=0.3,
            max_tokens=3500,
        )
        answer = response.choices[0].message.content
        if answer is None:
            return "ERROR: No response from OpenAI"
        return answer.strip()
    except Exception as e:
        return f"ERROR: {str(e)}"
