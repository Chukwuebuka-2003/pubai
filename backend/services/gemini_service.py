import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Initialize the model
model = genai.GenerativeModel('gemini-1.5-flash')

def explain_medical_terms(terms: list[str]) -> dict:
    if not terms:
        return {}

    prompt = (
        "You are a medical expert. For each medical term below, provide a short, simple explanation "
        "that a non-medical person can easily understand.\n" +
        "\n".join([f"{i+1}. {term}" for i, term in enumerate(terms)])
    )

    try:
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.2,
                max_output_tokens=500,
            )
        )

        if not response.text:
            return {"error": "No response from Gemini"}

        answer = response.text.strip()

        # Post-process into {term: explanation} pairs
        explanations = {}
        for line in answer.split("\n"):
            if "." in line and line.strip():
                try:
                    parts = line.split(".", 1)
                    if len(parts) == 2 and parts[0].strip().isdigit():
                        term_index = int(parts[0].strip()) - 1
                        if 0 <= term_index < len(terms):
                            explanations[terms[term_index]] = parts[1].strip()
                except (ValueError, IndexError):
                    continue

        return explanations
    except Exception as e:
        return {"error": str(e)}

def analyze_methodology(abstract: str) -> str:
    prompt = (
        "Analyze the following research abstract to summarize the study's methodology: "
        "1) What type of study is it? 2) How many participants? 3) Methods used? 4) Any strengths/limitations? "
        "Respond with clear sections.\n\n"
        f"Abstract:\n{abstract}"
    )

    try:
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.3,
                max_output_tokens=600,
            )
        )

        if not response.text:
            return "ERROR: No response from Gemini"

        return response.text.strip()
    except Exception as e:
        return f"ERROR: {str(e)}"

def analyze_research_gaps(abstracts: list[str], topic: str = "") -> list[str]:
    abstracts_text = "\n\n".join([f"Abstract {i+1}:\n{a}" for i, a in enumerate(abstracts)])
    prompt = (
        f"You are a medical research expert. Based on the following abstracts about '{topic or 'the topic'}', "
        "identify 3-5 important research gaps or open questions. Reply as a numbered list.\n\n"
        f"{abstracts_text}"
    )

    try:
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.3,
                max_output_tokens=700,
            )
        )

        if not response.text:
            return ["ERROR: No response from Gemini"]

        answer = response.text.strip()
        # Extract numbered list items
        gaps = []
        for line in answer.split("\n"):
            if line.strip() and line[0].isdigit():
                gap = line.partition(".")[2].strip()
                if gap:
                    gaps.append(gap)

        return gaps if gaps else [answer]
    except Exception as e:
        return [f"ERROR: {str(e)}"]

def generate_literature_review(abstracts: list[str], topic: str) -> str:
    abstracts_text = "\n\n".join([f"ARTICLE {i+1}:\n{a}" for i, a in enumerate(abstracts)])
    prompt = (
        f"You are a medical research expert. Write a structured literature review about '{topic}', "
        "based only on the provided article abstracts. Structure with: Introduction, Methods, Key Findings, "
        "Contradictions & Debates, Gaps, Conclusion.\n\n"
        f"{abstracts_text}"
    )

    try:
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.3,
                max_output_tokens=3500,
            )
        )

        if not response.text:
            return "ERROR: No response from Gemini"

        return response.text.strip()
    except Exception as e:
        return f"ERROR: {str(e)}"

def compare_studies(studies: list[dict]) -> str:
    studies_text = ""
    for i, s in enumerate(studies):
        studies_text += f"STUDY {i+1}: {s.get('title','')} | Abstract: {s.get('abstract','')}\n\n"

    prompt = (
        "Compare the provided research studies with focus on: "
        "1) Research questions 2) Methods 3) Main findings 4) Strengths & weaknesses 5) What's similar/different. "
        "Use structured sections with headings.\n\n"
        f"{studies_text}"
    )

    try:
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.3,
                max_output_tokens=3500,
            )
        )

        if not response.text:
            return "ERROR: No response from Gemini"

        return response.text.strip()
    except Exception as e:
        return f"ERROR: {str(e)}"
