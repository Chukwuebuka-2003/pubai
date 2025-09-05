from fastapi import APIRouter, Depends, Query
from .utils import get_current_user
from pubmed_api import search_pubmed

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
