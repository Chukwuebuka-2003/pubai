
import streamlit as st
import openai
import re
import os
from dotenv import load_dotenv
from xml_formatter import format_response_with_xml, get_formatted_explanation, get_formatted_methodology_analysis, get_formatted_research_gaps

# Load environment variables
load_dotenv()

# Initialize OpenAI with API key
openai.api_key = os.getenv("OPENAI_API_KEY")

def detect_medical_terms(text, max_terms=8):
    """
    Use OpenAI to detect medical terminology in text
    """
    if not text or text == "No abstract available":
        return []
    
    try:
        # Check if API key is available
        if not openai.api_key:
            st.error("OpenAI API key not found. Please check your .env file.")
            return []
            
        # Use OpenAI to detect medical terms
        response = openai.chat.completions.create(
            model="gpt-4o-mini",  # Use a smaller model for speed and cost efficiency
            messages=[
                {"role": "system", "content": "You are a medical terminology detector. Extract specialized medical terms from the text provided. Return only the most complex or technical medical terms that a general audience would find difficult to understand. Return the response as a comma-separated list of terms only."},
                {"role": "user", "content": f"Extract medical terms from this text:\n\n{text[:2000]}"}  # Limit to first 2000 chars
            ],
            temperature=0.3,
            max_tokens=100
        )
        
        # Extract the terms from the response
        terms_text = response.choices[0].message.content.strip()
        
        # Parse the comma-separated list
        terms = [term.strip() for term in terms_text.split(',') if term.strip()]
        
        # Limit to max_terms
        return terms[:max_terms]
        
    except Exception as e:
        st.error(f"Error detecting medical terms: {str(e)}")
        return []


def handle_explain_terms_button(terms_list, article_num=None):
    """
    Direct handler for the 'Explain These Terms' button.
    This bypasses the natural language processing and directly explains the terms.
    
    Parameters:
    terms_list: String containing comma-separated terms
    article_num: Optional article number for reference
    
    Returns:
    XML-formatted explanation
    """
    try:
        # Check if API key is available
        if not openai.api_key:
            return format_response_with_xml("general", "Error: OpenAI API key not found. Please check your .env file.")
        
        # Split the comma-separated terms
        terms = [term.strip() for term in terms_list.split(',') if term.strip()]
        
        if not terms:
            return format_response_with_xml("general", "No valid medical terms were provided to explain.")
        
        # Generate explanations using OpenAI
        if len(terms) > 1:
            # Format multiple terms for the prompt
            terms_prompt = "\n".join([f"- {term}" for term in terms])
            
            response = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a medical expert. For each term below, provide a clear, concise explanation in plain language that a patient would understand. For each term, first state the term, then provide the explanation."},
                    {"role": "user", "content": f"Please explain these medical terms:\n{terms_prompt}"}
                ],
                temperature=0.4,
                max_tokens=800
            )
            
            explanations = response.choices[0].message.content.strip()
            
            # Format as multiple terms XML
            return format_response_with_xml("multiple_terms", explanations)
        else:
            # Single term explanation - more concise
            term = terms[0]
            response = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a medical expert. Provide a clear, concise explanation of this medical term in plain language that a patient would understand."},
                    {"role": "user", "content": f"Please explain the medical term: {term}"}
                ],
                temperature=0.4,
                max_tokens=200
            )
            
            explanation = response.choices[0].message.content.strip()
            
            # Format as term explanation XML
            return format_response_with_xml("term_explanation", f"{term}: {explanation}")
            
    except Exception as e:
        error_message = f"Error generating explanations: {str(e)}"
        return format_response_with_xml("general", error_message)


def explain_medical_term(term):
    """
    Generate a plain-language explanation for a medical term using OpenAI
    """
    try:
        # Check if API key is available
        if not openai.api_key:
            return "Error: OpenAI API key not found. Please check your .env file."
        
        # Use the formatter function from xml_formatter.py
        return get_formatted_explanation(term)
        
    except Exception as e:
        error_message = f"I couldn't generate an explanation for '{term}': {str(e)}"
        return format_response_with_xml("general", error_message)


def identify_research_gaps(topic=None, article_num=None):
    """
    Analyze search results or a specific article to identify potential research gaps using OpenAI
    
    Parameters:
    topic: Optional topic name to override current search query
    article_num: Optional article number to focus analysis on just that article
    
    Returns:
    Formatted research gaps response
    """
    if not st.session_state.search_results or not st.session_state.search_results["articles"]:
        return format_response_with_xml("general", "I need to see some search results first before I can identify research gaps. Please perform a search first.")
    
    # Extract relevant information from articles
    articles = st.session_state.search_results["articles"]
    query = st.session_state.current_query or topic or "the current topic"
    
    # If specific article number is provided, only analyze that article
    if article_num is not None:
        article_idx = int(article_num) - 1
        if 0 <= article_idx < len(articles):
            article = articles[article_idx]
            if article["abstract"] != "No abstract available":
                abstracts = [article["abstract"]]
                article_title = article["title"]
                # Update query to include article title for context
                query = f"{query} (focusing on '{article_title}')"
            else:
                return format_response_with_xml("general", f"The article #{article_num} doesn't have an abstract available for analysis.")
        else:
            return format_response_with_xml("general", f"I couldn't find article #{article_num} in your search results.")
    else:
        # Compile abstracts for analysis (limit to 5 for API efficiency)
        abstracts = [article["abstract"] for article in articles[:5] if article["abstract"] != "No abstract available"]
    
    if not abstracts:
        return format_response_with_xml("general", "I couldn't find enough abstracts to analyze. Try a different search with more detailed results.")
    
    try:
        # Check if API key is available
        if not openai.api_key:
            return format_response_with_xml("general", "Error: OpenAI API key not found. Please check your .env file.")
        
        # Create a system prompt that adjusts based on whether we're analyzing a single article or multiple
        if article_num is not None:
            system_prompt = (
                "You are a research gap analysis expert with deep knowledge of medical literature. "
                "You're analyzing a single research article to identify potential research gaps or future directions. "
                "Based on the abstract, identify 3-5 potential research questions or areas that are either: "
                "1) Explicitly mentioned by the authors as future work, "
                "2) Limitations acknowledged in the study that could be addressed, or "
                "3) Logical next steps or unexplored aspects related to this research. "
                "Format your response as clearly numbered points. Be specific and concrete in your suggestions."
            )
        else:
            system_prompt = (
                "You are a research gap analysis expert. Based on the abstracts provided, "
                "identify 3-5 potential research gaps related to the topic. "
                "Focus on questions that aren't well-addressed across these studies, "
                "conflicting findings that need resolution, or areas where methodology could be improved. "
                "Format your response as clearly numbered points. Be specific and concrete in your suggestions."
            )
        
        # Prepare context based on whether we're analyzing a single article or multiple
        if article_num is not None:
            user_content = f"Analyze this research article abstract to identify research gaps:\n\nTopic: {query}\n\nAbstract:\n{abstracts[0]}"
        else:
            abstracts_text = "\n\n".join([f"Abstract {i+1}:\n{abstract}" for i, abstract in enumerate(abstracts)])
            user_content = f"Analyze these PubMed search results to identify research gaps:\n\nTopic: {query}\n\nNumber of results found: {len(abstracts)}\n\n{abstracts_text}"
        
        # Generate research gaps analysis
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content[:3500]}  # Limit to 3500 chars
            ],
            temperature=0.4,
            max_tokens=800
        )
        
        analysis = response.choices[0].message.content.strip()
        
        # Use the formatter function from xml_formatter.py
        return format_response_with_xml("research_gaps", analysis)
        
    except Exception as e:
        error_message = f"Error analyzing research gaps: {str(e)}"
        return format_response_with_xml("general", error_message)

def analyze_methodologies(abstract=None, article_num=None):
    """
    Extract and summarize research methodologies from abstracts using OpenAI
    Now with support for structured abstract sections
    """
    # If specific article number is provided, extract methodology section if available
    if article_num is not None and st.session_state.search_results and st.session_state.search_results["articles"]:
        article_idx = int(article_num) - 1
        if 0 <= article_idx < len(st.session_state.search_results["articles"]):
            article = st.session_state.search_results["articles"][article_idx]
            
            # Check if we have structured sections and a methods section
            if 'abstract_sections' in article:
                # Look for methods section with various possible labels
                methods_text = None
                for label in ['METHODS', 'METHOD', 'METHODOLOGY', 'STUDY DESIGN', 'DESIGN']:
                    if label in article['abstract_sections']:
                        methods_text = article['abstract_sections'][label]
                        break
                
                if methods_text:
                    # We found a methods section, use it for analysis
                    text_to_analyze = methods_text
                    # Also get results and conclusions if available for context
                    results = ""
                    for label in ['RESULTS', 'FINDINGS']:
                        if label in article['abstract_sections']:
                            results = f"\n\nRESULTS: {article['abstract_sections'][label]}"
                            break
                    conclusions = ""
                    for label in ['CONCLUSION', 'CONCLUSIONS']:
                        if label in article['abstract_sections']:
                            conclusions = f"\n\nCONCLUSIONS: {article['abstract_sections'][label]}"
                            break
                    
                    text_to_analyze += results + conclusions
                else:
                    # No specific methods section found, use the whole abstract
                    text_to_analyze = article['abstract']
            else:
                # No structured sections, use the whole abstract
                text_to_analyze = article['abstract']
        else:
            return format_response_with_xml("general", f"I couldn't find article #{article_num} in your search results.")
    # If specific abstract provided, use it
    elif abstract:
        text_to_analyze = abstract
    # Otherwise use search results
    elif st.session_state.search_results and st.session_state.search_results["articles"]:
        # Compile abstracts for analysis (limit to 3 for API efficiency)
        abstracts = [article["abstract"] for article in st.session_state.search_results["articles"][:3] 
                    if article["abstract"] != "No abstract available"]
        if not abstracts:
            return format_response_with_xml("general", "I couldn't find enough abstracts to analyze. Try a different search with more detailed results.")
        text_to_analyze = " ".join(abstracts)
    else:
        return format_response_with_xml("general", "I need to see some search results first before I can analyze methodologies. Please perform a search first.")
    
    try:
        # Check if API key is available
        if not openai.api_key:
            return format_response_with_xml("general", "Error: OpenAI API key not found. Please check your .env file.")
        
        # Create a more targeted prompt based on whether we have a dedicated methods section
        if 'METHODS:' in text_to_analyze or 'METHODOLOGY:' in text_to_analyze:
            system_prompt = (
                "You are a research methodology expert. Analyze the provided research methodology section from a medical paper. "
                "Focus specifically on extracting and explaining: "
                "1) Study design (e.g., RCT, cohort, case-control) "
                "2) Participants/sample (selection criteria, demographics) "
                "3) Interventions or exposures (if applicable) "
                "4) Outcome measures and statistical methods "
                "5) Strengths and limitations of the methodology "
                "Format your response with clear headings for each section."
            )
        else:
            # More general prompt for unstructured abstracts
            system_prompt = (
                "You are a research methodology expert. Analyze the provided abstract to identify and explain the research methodology. "
                "Structure your response with clear sections, each with a heading: "
                "1) Study Design, 2) Key Methodological Elements, 3) Strengths, and 4) Limitations. "
                "Always include all four sections, especially the limitations section. "
                "If limitations aren't explicitly stated, analyze what potential limitations might exist based on the study design."
            )
        
        # Use the formatter function from xml_formatter.py with enhanced prompt
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Analyze this research methodology:\n\n{text_to_analyze[:3500]}"}
            ],
            temperature=0.4,
            max_tokens=800
        )
        
        analysis = response.choices[0].message.content.strip()
        return format_response_with_xml("methodology", analysis)
        
    except Exception as e:
        error_message = f"Error analyzing methodology: {str(e)}"
        return format_response_with_xml("general", error_message)

def get_chatbot_response(user_input):
    """
    Process user input and return appropriate chatbot response using natural language understanding
    instead of slash commands
    """
    # FIXED: Special handling for the "Explain These Terms" button from apps.py
    if "explain these medical terms from article" in user_input.lower():
        # Extract terms from the input
        term_extraction = re.search(r'Explain these medical terms from article #?(\d+): (.*)', user_input, re.IGNORECASE)
        if term_extraction:
            article_num = term_extraction.group(1).strip()
            terms = term_extraction.group(2).strip()
            
            # Use our direct handler instead of the general explain_medical_term function
            explanation = handle_explain_terms_button(terms, article_num)
            
            # Add to conversation history
            st.session_state.conversation.append({"role": "user", "content": user_input, "format": "text"})
            st.session_state.conversation.append({"role": "assistant", "content": explanation, "format": "xml"})
            
            return explanation
    
    # Special handling for "Find research gaps in article X" requests
    if "find research gaps" in user_input.lower() and "article" in user_input.lower():
        # Extract article number from the input
        article_match = re.search(r'article #?(\d+)', user_input, re.IGNORECASE)
        if article_match:
            article_num = article_match.group(1).strip()
            gaps_analysis = identify_research_gaps(article_num=int(article_num))
            
            # Add to conversation history
            st.session_state.conversation.append({"role": "user", "content": user_input, "format": "text"})
            st.session_state.conversation.append({"role": "assistant", "content": gaps_analysis, "format": "xml"})
            
            return gaps_analysis
    
    # Natural language pattern matching for specific feature requests
    # Term explanation patterns
    term_patterns = [
        r"(?:explain|define|what (?:does|is|are)(?: the)? (?:term|word|meaning of))(?:s|) (?:called |named |)(?:\"|\')([\w\s\-]+)(?:\"|\')(?:\?|)",
        r"(?:explain|define|what (?:does|is|are)(?: the)?(?: medical| clinical)? (?:term|word|meaning of))(?:s|) ([\w\s\-]+)(?:\?|)",
        r"(?:what|how) (?:does|is|are) ([\w\s\-]+) (?:mean|defined as)(?:\?|)",
        r"definition (?:of|for) ([\w\s\-]+)(?:\?|)"
    ]
    
    # Research gap patterns
    gap_patterns = [
        r"(?:find|identify|discover|what are)(?: the| some| potential)? (?:research |)gaps(?:.+?)",
        r"(?:what|which) (?:areas|topics) (?:need|require) (?:more|further|additional) research(?:\?|)",
        r"(?:unexplored|understudied) (?:areas|topics)(?:.+?)",
        r"(?:missing|lacking) (?:research|studies|evidence)(?:.+?)",
        r"future (?:research|directions)(?:.+?)"
    ]
    
    # Methodology patterns
    method_patterns = [
        r"(?:analyze|examine|explain|describe|what is|how is)(?: the| this)? (?:methodology|method|study design|research design|approach)(?:s|)(?:.+?)",
        r"(?:how|what) (?:was|were)(?: the)? (?:study|research|this) (?:conducted|done|performed|carried out)(?:\?|)",
        r"(?:how did they|what methods did they|how were data) (?:conduct|use|collect|analyze)(?:.+?)"
    ]
    
    # Abstract reference patterns
    abstract_patterns = [
        r"(?:(?:study|article|abstract|paper) (?:\#|number) ?(\d+))",
        r"(?:(?:the|this) (\d+)(?:st|nd|rd|th) (?:study|article|abstract|paper))",
        r"(?:article|abstract|paper|study) (\d+)"
    ]
    
    # Search command patterns
    search_patterns = [
        r"(?:search|find|look up|look for)(?: for)? ([\w\s\-\+]+?)(?:\.|$)",
        r"(?:search pubmed|find articles|find papers) (?:about|on|for|related to) ([\w\s\-\+]+?)(?:\.|$)", 
        r"(?:articles|papers|studies|research) (?:about|on|for|related to) ([\w\s\-\+]+?)(?:\.|$)",
        r"(?:i want|i need|i'm looking for) (?:articles|papers|studies|research) (?:about|on|for|related to) ([\w\s\-\+]+?)(?:\.|$)",
        r"(?:show me|get me|find me) (?:articles|papers|studies|research) (?:about|on|for|related to) ([\w\s\-\+]+?)(?:\.|$)"
    ]
    
    # Check for term explanation match
    term_match = None
    for pattern in term_patterns:
        match = re.search(pattern, user_input, re.IGNORECASE)
        if match:
            term_match = match
            break
    
    # Check for research gap match
    gap_match = False
    for pattern in gap_patterns:
        if re.search(pattern, user_input, re.IGNORECASE):
            gap_match = True
            break
    
    # Check for methodology match
    method_match = False
    for pattern in method_patterns:
        if re.search(pattern, user_input, re.IGNORECASE):
            method_match = True
            break
    
    # Look for abstract number reference
    abstract_num = None
    if method_match or gap_match:  # Check for both methodology and gap analysis
        for pattern in abstract_patterns:
            match = re.search(pattern, user_input, re.IGNORECASE)
            if match:
                abstract_num = match.group(1)
                break
    
    # Check for search request
    search_query = None
    for pattern in search_patterns:
        match = re.search(pattern, user_input, re.IGNORECASE)
        if match:
            search_query = match.group(1).strip()
            break
    
    # Handle search request
    if search_query:
        # Add to conversation history
        st.session_state.conversation.append({"role": "user", "content": user_input, "format": "text"})
        
        # Create a response with the search command
        response = f"I'll search PubMed for articles about '{search_query}'.\n\n[SEARCH: {search_query}]"
        
        # Add to conversation history
        st.session_state.conversation.append({"role": "assistant", "content": response, "format": "text"})
        
        return response
    
    # Define behavior based on the type of request
    if term_match:
        term = term_match.group(1).strip()
        explanation = explain_medical_term(term)
        
        # Add to conversation history
        st.session_state.conversation.append({"role": "user", "content": user_input, "format": "text"})
        st.session_state.conversation.append({"role": "assistant", "content": explanation, "format": "xml"})
        
        return explanation
        
    elif gap_match:
        # Check if there's a reference to a specific article
        if abstract_num:
            gaps_analysis = identify_research_gaps(article_num=int(abstract_num))
        else:
            gaps_analysis = identify_research_gaps()
        
        # Add to conversation history
        st.session_state.conversation.append({"role": "user", "content": user_input, "format": "text"})
        st.session_state.conversation.append({"role": "assistant", "content": gaps_analysis, "format": "xml"})
        
        return gaps_analysis
        
    elif method_match:
        # Check if there's a reference to a specific article or abstract
        abstract = None
        article_num = abstract_num
        
        if article_num and st.session_state.search_results and st.session_state.search_results["articles"]:
            article_num = int(article_num)  # Get article number
            article_idx = article_num - 1  # Convert to 0-based index
            if 0 <= article_idx < len(st.session_state.search_results["articles"]):
                abstract = st.session_state.search_results["articles"][article_idx]["abstract"]
        
        methodology_analysis = analyze_methodologies(abstract, article_num)
        
        # Add to conversation history
        st.session_state.conversation.append({"role": "user", "content": user_input, "format": "text"})
        st.session_state.conversation.append({"role": "assistant", "content": methodology_analysis, "format": "xml"})
        
        return methodology_analysis
        
    else:
        # Default PubMed assistant behavior - using OpenAI
        try:
            # Check if API key is available
            if not openai.api_key:
                error_msg = "Error: OpenAI API key not found. Please check your .env file."
                st.session_state.conversation.append({"role": "user", "content": user_input, "format": "text"})
                st.session_state.conversation.append({"role": "assistant", "content": error_msg, "format": "text"})
                return error_msg
                
            # Record user input in conversation history
            st.session_state.conversation.append({"role": "user", "content": user_input, "format": "text"})
            
            # Define system prompt for the general assistant with natural language capabilities
            system_prompt = {
                "role": "system", 
                "content": (
                    "You are a specialized assistant for a PubMed search application. Your purpose is to assist users with PubMed-related tasks, such as formulating search queries, interpreting search results, suggesting MeSH terms, or explaining PubMed syntax (e.g., AND, OR, [MeSH], [Author]). "
                    "You can understand natural language requests for the following functions: "
                    "1. Search PubMed: When a user wants to search for articles, respond with `[SEARCH: query]` followed by an explanation."
                    "2. Explain medical terminology: When a user asks 'what does X mean' or 'explain term X'"
                    "3. Identify research gaps: When a user asks about unexplored areas or research gaps"
                    "4. Analyze methodology: When a user asks how a study was conducted or about research methods"
                    "Use a conversational, helpful tone and focus on providing clear, concise responses. "
                    "If the user's input is unrelated to PubMed or medical research, politely redirect them."
                )
            }
            
            # Send conversation history to OpenAI
            response = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[system_prompt] + [
                    {"role": m["role"], "content": m["content"]} 
                    for m in st.session_state.conversation[-10:] if "format" in m
                ],
                temperature=0.5,
                max_tokens=500
            )
            
            assistant_message = response.choices[0].message.content.strip()
            
            # Post-process to ensure `[SEARCH: query]` is valid if present
            search_match = re.search(r"\[SEARCH:\s*(.*?)\]", assistant_message)
            if search_match and not search_match.group(1).strip():
                assistant_message = assistant_message.replace(search_match.group(0), "") + "\n\nPlease provide a specific query for me to search PubMed."

            # Store assistant response in conversation history
            st.session_state.conversation.append({"role": "assistant", "content": assistant_message, "format": "text"})
            
            return assistant_message
            
        except Exception as e:
            error_message = f"Error with OpenAI API: {str(e)}"
            st.session_state.conversation.append({"role": "assistant", "content": error_message, "format": "text"})
            return error_message

def process_search_command(response):
    """
    Extract and process search command from response
    """
    match = re.search(r"\[SEARCH:\s*(.*?)\]", response)
    if match and match.group(1).strip():
        query = match.group(1).strip()
        st.session_state.current_query = query
        from pubmed_api import search_pubmed
        with st.spinner("Performing PubMed search..."):
            try:
                # Execute the search
                search_results = search_pubmed(query)
                
                # Store search results in session state
                st.session_state.search_results = search_results
                
                # Add a message with the search results
                result_count = search_results.get("count", 0)
                if result_count > 0:
                    message = f"Found {result_count} results for '{query}'. You can view them on the Search page or ask me to analyze them."
                    st.session_state.conversation.append({"role": "assistant", "content": message, "format": "text"})
                else:
                    message = f"No results found for '{query}'. Try a different search term or check your syntax."
                    st.session_state.conversation.append({"role": "assistant", "content": message, "format": "text"})
                
                return True
            except Exception as e:
                error_message = f"Error searching PubMed: {str(e)}"
                st.session_state.conversation.append({"role": "assistant", "content": error_message, "format": "text"})
                return False
    return False