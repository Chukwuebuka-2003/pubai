# pubmed/backend/routers/search.py

from fastapi import APIRouter, Depends, Query, HTTPException
from typing import List
from .utils import get_current_user
from pubmed_api import search_pubmed, fetch_pubmed_articles_by_ids, get_related_articles
router = APIRouter(prefix="/search", tags=["search"])

@router.get("/", summary="Search PubMed for articles")
def search(
    query: str = Query(..., description="PubMed search query"),
    max_results: int = Query(10, ge=1, le=100),
    start: int = Query(0, ge=0),
    sort: str = Query("relevance", description="Sort by: relevance, date, etc."),
    current_user: str = Depends(get_current_user)
):
    """
    Search PubMed and return articles.
    """
    results = search_pubmed(query, max_results=max_results, start=start, sort=sort)
    return results

@router.get("/articles/{pmid}", summary="Get a single PubMed article by PMID")
def get_article_details(
    pmid: str,
    current_user: str = Depends(get_current_user)
):
    """
    Fetch details for a single PubMed article using its PMID.
    """
    articles = fetch_pubmed_articles_by_ids([pmid])
    if not articles:
        raise HTTPException(status_code=404, detail=f"Article with PMID {pmid} not found.")
    return articles[0]

@router.get("/articles/{pmid}/related", summary="Get related PubMed articles for a given PMID")
def get_related_articles_endpoint(
    pmid: str,
    max_results: int = Query(10, ge=1, le=20), # limit to 20 for related articles
    current_user: str = Depends(get_current_user)
):
    """
    Fetch articles related to a specific PubMed ID.
    """
    related_results = get_related_articles(pmid, max_results=max_results)
    if not related_results["articles"]:
        raise HTTPException(status_code=404, detail=f"No related articles found for PMID {pmid}.")
    return related_results
