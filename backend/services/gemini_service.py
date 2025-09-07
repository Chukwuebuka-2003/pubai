from google import genai
from google.genai import types
from dotenv import load_dotenv
import os
import yaml
import time
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path

load_dotenv()


client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_prompts_config() -> Dict[str, Any]:
    """Load prompts configuration from YAML file"""
    config_path = Path(__file__).parent.parent / "prompts" / "prompts.yaml"
    try:
        with open(config_path, 'r', encoding='utf-8') as file:
            return yaml.safe_load(file)
    except FileNotFoundError:
        logger.error(f"Prompts configuration file not found at {config_path}")
        raise
    except yaml.YAMLError as e:
        logger.error(f"Error parsing YAML configuration: {e}")
        raise


CONFIG = load_prompts_config()
GLOBAL_CONFIG = CONFIG['global']
PROMPTS = CONFIG['prompts']
ERROR_MESSAGES = CONFIG['error_handling']
VALIDATION = CONFIG['validation']

def validate_input(data: Any, function_name: str, additional_data: Optional[Any] = None) -> bool:
    """Validate input data based on function requirements"""
    if function_name == "explain_medical_terms":
        terms = data
        abstracts = additional_data
        if not isinstance(terms, list) or len(terms) == 0:
            return False
        if len(terms) > VALIDATION['max_terms_explain']:
            return False
        if not isinstance(abstracts, list):
            return False

        total_abstracts_length = sum(len(abstract) for abstract in abstracts)
        if total_abstracts_length > VALIDATION['max_abstracts_explain_context_length']:
            return False
        return True

    elif function_name == "analyze_methodology":
        if not isinstance(data, str) or len(data) < VALIDATION['min_abstract_length']:
            return False
        if len(data) > VALIDATION['max_abstract_length']:
            return False
        return True

    elif function_name == "analyze_research_gaps":
        if not isinstance(data, list) or len(data) == 0:
            return False
        if len(data) > VALIDATION['max_abstracts_gaps']:
            return False
        return True

    elif function_name == "generate_literature_review":
        if not isinstance(data, list) or len(data) == 0:
            return False
        if len(data) > VALIDATION['max_abstracts_review']:
            return False
        return True

    elif function_name == "compare_studies":
        if not isinstance(data, list) or len(data) == 0:
            return False
        if len(data) > VALIDATION['max_studies_compare']:
            return False
        return True

    return True

def make_api_call_with_retry(prompt: str, system_instruction: str, config: Dict[str, Any], function_name: str) -> str:
    """Make API call with retry logic and error handling"""
    for attempt in range(GLOBAL_CONFIG['retry_attempts']):
        try:
            # Build safety settings
            safety_settings = []
            for setting in GLOBAL_CONFIG['safety_settings']:
                safety_settings.append(types.SafetySetting(
                    category=setting['category'],
                    threshold=setting['threshold']
                ))

            response = client.models.generate_content(
                model=GLOBAL_CONFIG['model'],
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=config.get('temperature', GLOBAL_CONFIG['default_temperature']),
                    max_output_tokens=config.get('max_output_tokens', 1000),
                    top_p=config.get('top_p', 0.9),
                    top_k=config.get('top_k', 40),
                    safety_settings=safety_settings,
                ),
            )

            if hasattr(response, 'text') and response.text:
                return response.text.strip()
            elif hasattr(response, 'candidates') and response.candidates:
                # Handle case where response.text might not be available
                for candidate in response.candidates:
                    if hasattr(candidate, 'content') and candidate.content:
                        if hasattr(candidate.content, 'parts') and candidate.content.parts:
                            for part in candidate.content.parts:
                                if hasattr(part, 'text') and part.text:
                                    return part.text.strip()

            logger.warning(f"Empty response from API on attempt {attempt + 1}")
            if attempt < GLOBAL_CONFIG['retry_attempts'] - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
                continue
            else:
                return ERROR_MESSAGES['empty_response']

        except Exception as e:
            error_msg = str(e).lower()

            # Handle specific error types
            if 'timeout' in error_msg:
                if attempt < GLOBAL_CONFIG['retry_attempts'] - 1:
                    logger.warning(f"Timeout on attempt {attempt + 1}, retrying...")
                    time.sleep(2 ** attempt)
                    continue
                else:
                    return ERROR_MESSAGES['timeout_error']

            elif 'safety' in error_msg or 'content' in error_msg:
                return ERROR_MESSAGES['content_filter']

            elif 'recitation' in error_msg:
                logger.warning(f"Recitation error on attempt {attempt + 1}, retrying with adjusted prompt...")
                if attempt < GLOBAL_CONFIG['retry_attempts'] - 1:
                    time.sleep(1)
                    continue
                else:
                    return ERROR_MESSAGES['api_error'].format(error_message="Content recitation detected")

            else:
                logger.error(f"API call failed on attempt {attempt + 1}: {e}")
                if attempt < GLOBAL_CONFIG['retry_attempts'] - 1:
                    time.sleep(2 ** attempt)
                    continue
                else:
                    return ERROR_MESSAGES['api_error'].format(error_message=str(e))

def explain_medical_terms(terms: List[str], abstracts: List[str]) -> str:
    """
    Explain medical terms using production-grade prompts, providing contextual, layered,
    and clinically relevant explanations in markdown format.

    Args:
        terms: List of medical terms to explain\
        abstracts: List of abstracts from selected articles to provide context\

    Returns:
        A single markdown-formatted string with explanations, or an error message\
    """
    if not terms:
        return "" # Return empty string for no terms

    # Validate input, passing abstracts as additional_data
    if not validate_input(terms, "explain_medical_terms", abstracts):
        return f"ERROR: Invalid input for medical term explanation. Max {VALIDATION['max_terms_explain']} terms and max combined abstract length of {VALIDATION['max_abstracts_explain_context_length']} characters allowed."

    # Get prompt configuration
    prompt_config = PROMPTS['explain_medical_terms']

    # Format terms list for the prompt
    terms_list = ", ".join([f"'{term}'" for term in terms])

    # Format abstracts for context
    context_text = ""
    if abstracts:
        context_text = "\\n\\n--- Contextual Articles ---\\n"
        for i, abstract in enumerate(abstracts):
            context_text += f"Abstract {i+1}: {abstract}\\n"

    # Build prompt from template
    prompt = prompt_config['user_prompt_template'].format(
        terms_list=terms_list,
        context_text=context_text
    )

    # Make API call with retry logic
    response_text = make_api_call_with_retry(
        prompt=prompt,
        system_instruction=prompt_config['system_instruction'],
        config=prompt_config['config'],
        function_name="explain_medical_terms"
    )


    if response_text.startswith("ERROR:"):
        return response_text

    # no parsing needed here; the model is expected to return the final markdown string
    return response_text



def analyze_methodology(abstract: str) -> str:
    """
    Analyze research methodology using production-grade prompts

    Args:
        abstract: Research abstract to analyze

    Returns:
        Methodology analysis string
    """
    # Validate input
    if not validate_input(abstract, "analyze_methodology"):\
        return f"ERROR: Abstract must be between {VALIDATION['min_abstract_length']} and {VALIDATION['max_abstract_length']} characters"

    # Get prompt configuration
    prompt_config = PROMPTS['analyze_methodology']

    # Build prompt from template
    prompt = prompt_config['user_prompt_template'].format(abstract=abstract)

    # Make API call with retry logic
    response_text = make_api_call_with_retry(
        prompt=prompt,
        system_instruction=prompt_config['system_instruction'],
        config=prompt_config['config'],
        function_name="analyze_methodology"
    )

    return response_text



def analyze_research_gaps(abstracts: List[str], topic: str = "") -> List[str]:
    """
    Analyze research gaps using production-grade prompts

    Args:
        abstracts: List of research abstracts
        topic: Research topic (optional)

    Returns:
        List of identified research gaps
    """
    # Validate input
    if not validate_input(abstracts, "analyze_research_gaps"):
        return [f"ERROR: Maximum {VALIDATION['max_abstracts_gaps']} abstracts allowed"]

    # Get prompt configuration
    prompt_config = PROMPTS['analyze_research_gaps']

    # Format abstracts
    abstracts_text = "\\n\\n".join([f"Abstract {i+1}:\\n{abstract}" for i, abstract in enumerate(abstracts)])

    # Build prompt from template
    prompt = prompt_config['user_prompt_template'].format(
        topic=topic or "the research area",
        abstracts_text=abstracts_text
    )

    # Make API call with retry logic
    response_text = make_api_call_with_retry(
        prompt=prompt,
        system_instruction=prompt_config['system_instruction'],
        config=prompt_config['config'],
        function_name="analyze_research_gaps"
    )

    # Handle errors
    if response_text.startswith("ERROR:") or "error" in response_text.lower():
        return [response_text]

    # Parse response into list
    try:
        gaps = []
        for line in response_text.split("\\n"):
            line = line.strip()
            if line and any(char.isdigit() for char in line[:3]):
                # Extract gap after numbering
                if ":" in line:
                    gap = line.split(":", 1)[1].strip()
                elif "." in line:
                    parts = line.split(".", 1)
                    if len(parts) > 1:
                        gap = parts[1].strip()
                    else:
                        gap = line
                else:
                    gap = line

                if gap and not gap.startswith(("ERROR", "error")):\
                    gaps.append(gap)

        return gaps if gaps else ["ERROR: Failed to parse research gaps"]

    except Exception as e:
        logger.error(f"Error parsing research gaps response: {e}")
        return [f"ERROR: Parse error - {str(e)}"]



def generate_literature_review(abstracts: List[str], topic: str) -> str:
    """
    Generate literature review using production-grade prompts

    Args:
        abstracts: List of research abstracts
        topic: Review topic

    Returns:
        Literature review string
    """
    # Validate input
    if not validate_input(abstracts, "generate_literature_review"):
        return f"ERROR: Maximum {VALIDATION['max_abstracts_review']} abstracts allowed"

    # Get prompt configuration
    prompt_config = PROMPTS['generate_literature_review']

    # Format abstracts
    abstracts_text = "\\n\\n".join([f"ARTICLE {i+1}:\\n{abstract}" for i, abstract in enumerate(abstracts)])

    # Build prompt from template
    prompt = prompt_config['user_prompt_template'].format(
        topic=topic,
        abstracts_text=abstracts_text
    )

    # Make API call with retry logic
    response_text = make_api_call_with_retry(
        prompt=prompt,
        system_instruction=prompt_config['system_instruction'],
        config=prompt_config['config'],
        function_name="generate_literature_review"
    )

    return response_text



def compare_studies(studies: List[Dict[str, Any]]) -> str:
    """
    Compare studies using production-grade prompts

    Args:
        studies: List of study dictionaries with 'title' and 'abstract' keys

    Returns:
        Study comparison string
    """
    # Validate input
    if not validate_input(studies, "compare_studies"):
        return f"ERROR: Maximum {VALIDATION['max_studies_compare']} studies allowed"

    # Get prompt configuration
    prompt_config = PROMPTS['compare_studies']

    # Format studies
    studies_text = ""
    for i, study in enumerate(studies):
        title = study.get('title', f'Study {i+1}')
        abstract = study.get('abstract', '')
        studies_text += f"STUDY {i+1}: {title}\\nAbstract: {abstract}\\n\\n"

    # Build prompt from template
    prompt = prompt_config['user_prompt_template'].format(studies_text=studies_text)

    # Make API call with retry logic
    response_text = make_api_call_with_retry(
        prompt=prompt,
        system_instruction=prompt_config['system_instruction'],
        config=prompt_config['config'],
        function_name="compare_studies"
    )

    return response_text



def get_config_info() -> Dict[str, Any]:
    """Get current configuration information"""
    return {
        "model": GLOBAL_CONFIG['model'],
        "retry_attempts": GLOBAL_CONFIG['retry_attempts'],
        "timeout_seconds": GLOBAL_CONFIG['timeout_seconds'],
        "validation_limits": VALIDATION,
        "functions_available": list(PROMPTS.keys())
    }

def reload_config():
    """Reload configuration from YAML file"""
    global CONFIG, GLOBAL_CONFIG, PROMPTS, ERROR_MESSAGES, VALIDATION
    CONFIG = load_prompts_config()
    GLOBAL_CONFIG = CONFIG['global']
    PROMPTS = CONFIG['prompts']
    ERROR_MESSAGES = CONFIG['error_handling']
    VALIDATION = CONFIG['validation']
    logger.info("Configuration reloaded successfully")
