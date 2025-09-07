import requests
import xml.etree.ElementTree as ET
import time
from config import BASE_URL, EMAIL, TOOL, NCBI_API_KEY

def search_pubmed(query, max_results=20, start=0, sort="relevance", webenv=None, query_key=None):
    """
    Search PubMed API and return formatted results
    """
    search_url = f"{BASE_URL}esearch.fcgi"
    search_params = {
        "db": "pubmed",
        "term": query,
        "retmax": max_results,
        "retstart": start,
        "sort": sort,
        "retmode": "xml",
        "tool": TOOL,
        "email": EMAIL,
        "usehistory": "n"
    }
    if NCBI_API_KEY:
        search_params["api_key"] = NCBI_API_KEY

    response = requests.get(search_url, params=search_params)
    response.raise_for_status()
    tree = ET.fromstring(response.content)
    id_list = [id_elem.text for id_elem in tree.findall(".//Id")]
    count_elem = tree.find(".//Count")
    count = int(count_elem.text or 0) if count_elem is not None else 0

    # Fetch details for returned IDs
    if id_list:
        fetch_url = f"{BASE_URL}efetch.fcgi"
        fetch_params = {
            "db": "pubmed",
            "id": ",".join(id for id in id_list if id is not None),
            "retmode": "xml",
            "rettype": "abstract",
            "tool": TOOL,
            "email": EMAIL
        }
        if NCBI_API_KEY:
            fetch_params["api_key"] = NCBI_API_KEY
        detail_response = requests.get(fetch_url, params=fetch_params)
        detail_response.raise_for_status()
        articles = parse_pubmed_xml(detail_response.content)
    else:
        articles = []
    return {"count": count, "articles": articles}

def parse_pubmed_xml(xml_content):
    """
    Parse PubMed XML response into structured article data
    """
    root = ET.fromstring(xml_content)
    articles = []
    for article_elem in root.findall(".//PubmedArticle"):
        try:
            # Extract PMID
            pmid_elem = article_elem.find(".//PMID")
            pmid = pmid_elem.text if pmid_elem is not None else "Unknown PMID"

            # Extract title
            title_elem = article_elem.find(".//ArticleTitle")
            title = title_elem.text if title_elem is not None else "No title available"

            # Extract abstract text
            abstract_parts = article_elem.findall(".//AbstractText")
            abstract_sections = {}
            has_labeled_sections = False

            for part in abstract_parts:
                label = part.get("Label")
                if label:
                    has_labeled_sections = True
                    abstract_sections[label.upper()] = part.text or ""
                else:
                    abstract_sections["UNLABELED"] = part.text or ""

            if has_labeled_sections:
                abstract = " ".join([f"{label}: {text}" for label, text in abstract_sections.items() if label != "UNLABELED"])
                if abstract_sections and "UNLABELED" in abstract_sections and abstract_sections["UNLABELED"]:
                    abstract = abstract_sections["UNLABELED"] + " " + abstract if abstract else abstract_sections["UNLABELED"]
            else:
                abstract = " ".join([part.text for part in abstract_parts if part.text]) or "No abstract available"

            # Extract author information
            authors = []
            for author_elem in article_elem.findall(".//Author"):
                last_name = author_elem.find("LastName")
                fore_name = author_elem.find("ForeName")
                if last_name is not None:
                    if fore_name is not None:
                        authors.append(f"{fore_name.text} {last_name.text}")
                    else:
                        initials = author_elem.find("Initials")
                        if initials is not None:
                            authors.append(f"{initials.text} {last_name.text}")
                        else:
                            authors.append(f"{last_name.text}")

            if not authors:
                collective = article_elem.find(".//CollectiveName")
                if collective is not None and collective.text:
                    authors.append(collective.text)
                else:
                    authors.append("Unknown")

            # Extract journal information
            journal = article_elem.find(".//Journal/Title")
            journal_name = journal.text if journal is not None else "Unknown Journal"

            # Extract publication date
            year_elem = article_elem.find(".//PubDate/Year")
            if year_elem is None or year_elem.text is None:
                medline_date = article_elem.find(".//PubDate/MedlineDate")
                year = medline_date.text[:4] if medline_date is not None and medline_date.text else "Unknown Year"
            else:
                year = year_elem.text

            month_elem = article_elem.find(".//PubDate/Month")
            month_text = month_elem.text if month_elem is not None and month_elem.text else ""
            pub_date = f"{month_text} {year}".strip()

            # Extract DOI if available
            doi = None
            for id_elem in article_elem.findall(".//ArticleId"):
                if id_elem.get("IdType") == "doi" and id_elem.text:
                    doi = id_elem.text
                    break

            article_data = {
                "pmid": pmid,
                "title": title,
                "abstract": abstract,
                "abstract_sections": abstract_sections if has_labeled_sections else {},
                "authors": ", ".join(authors),
                "journal": journal_name,
                "pub_date": pub_date,
                "year": year,
                "doi": doi,
                "pubmed_url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
            }

            articles.append(article_data)
        except Exception as e:
            st.warning(f"Error parsing article: {e}")

    return articles

def get_related_articles(pmid, max_results=10):
    """
    Get articles related to a specific PubMed ID
    """
    if NCBI_API_KEY:
        time.sleep(0.1)
    else:
        time.sleep(0.34)

    elink_url = f"{BASE_URL}elink.fcgi"
    elink_params = {
        "dbfrom": "pubmed",
        "db": "pubmed",
        "id": pmid,
        "linkname": "pubmed_pubmed",
        "retmode": "xml",
        "retmax": max_results,
        "tool": TOOL,
        "email": EMAIL
    }
    if NCBI_API_KEY:
        elink_params["api_key"] = NCBI_API_KEY

    try:
        elink_response = requests.get(elink_url, params=elink_params)
        elink_response.raise_for_status()

        elink_tree = ET.fromstring(elink_response.content)
        linked_ids = [id_elem.text for id_elem in elink_tree.findall(".//LinkSetDb/Link/Id") if id_elem.text]

        if not linked_ids:
            return {"count": 0, "articles": []}

        related_ids = ",".join(linked_ids[:max_results])
        fetch_url = f"{BASE_URL}efetch.fcgi"
        fetch_params = {
            "db": "pubmed",
            "id": related_ids,
            "retmode": "xml",
            "rettype": "abstract",
            "tool": TOOL,
            "email": EMAIL
        }
        if NCBI_API_KEY:
            fetch_params["api_key"] = NCBI_API_KEY

        fetch_response = requests.get(fetch_url, params=fetch_params)
        fetch_response.raise_for_status()
        related_articles = parse_pubmed_xml(fetch_response.content)

        return {"count": len(related_articles), "articles": related_articles}

    except requests.exceptions.RequestException as e:
        if hasattr(e, 'response') and e.response is not None and e.response.status_code == 429:
            st.error("PubMed API rate limit exceeded. Please try again in a few seconds.")
            time.sleep(2)
        else:
            st.error(f"Error finding related articles: {e}")
        return {"count": 0, "articles": []}
    except ET.ParseError as e:
        st.error(f"XML parsing error: {e}")
        return {"count": 0, "articles": []}

def get_citation_suggestions(query, max_results=5):
    """
    Get citation suggestions for a search query
    """
    if NCBI_API_KEY:
        time.sleep(0.1)
    else:
        time.sleep(0.34)

    espell_url = f"{BASE_URL}espell.fcgi"
    espell_params = {
        "db": "pubmed",
        "term": query,
        "retmode": "xml",
        "tool": TOOL,
        "email": EMAIL
    }
    if NCBI_API_KEY:
        espell_params["api_key"] = NCBI_API_KEY

    try:
        espell_response = requests.get(espell_url, params=espell_params)
        espell_response.raise_for_status()

        espell_tree = ET.fromstring(espell_response.content)
        suggestions = [suggestion.text for suggestion in espell_tree.findall(".//CorrectedQuery") if suggestion.text]

        return suggestions

    except requests.exceptions.RequestException as e:
        st.error(f"Error getting citation suggestions: {e}")
        return []
    except ET.ParseError as e:
        st.error(f"XML parsing error: {e}")
        return []


def fetch_pubmed_articles_by_ids(pmids: list[str]) -> list[dict]:
    """
    Fetch details for a list of PubMed IDs directly using EFetch.
    """
    if not pmids:
        return []

    fetch_url = f"{BASE_URL}efetch.fcgi"
    fetch_params = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "xml",
        "rettype": "abstract",
        "tool": TOOL,
        "email": EMAIL
    }
    if NCBI_API_KEY:
        fetch_params["api_key"] = NCBI_API_KEY

    try:
        # Respect rate limits
        if NCBI_API_KEY:
            time.sleep(0.1)
        else:
            time.sleep(0.34)

        response = requests.get(fetch_url, params=fetch_params)
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        articles = parse_pubmed_xml(response.content)
        return articles
    except requests.exceptions.RequestException as e:
        # Removed st.error, as streamlit is a frontend library and should not be used in the backend
        print(f"Error fetching articles by ID from PubMed API: {e}")
        return []
    except ET.ParseError as e:
        print(f"XML parsing error when fetching articles by ID: {e}")
        return []
