from fastapi import APIRouter, Depends, HTTPException, status
from schemas import ExplainTermRequest, ExplainTermResponse
from services.gemini_service import explain_medical_terms
from .utils import get_current_user

from schemas import (
    MethodologyAnalysisRequest, MethodologyAnalysisResponse,
    ResearchGapRequest, ResearchGapResponse,
    LiteratureReviewRequest, LiteratureReviewResponse,
    StudyComparisonRequest, StudyComparisonResponse
)
from services.gemini_service import (
    analyze_methodology, analyze_research_gaps,
    generate_literature_review, compare_studies
)

router = APIRouter(prefix='/ai', tags=['ai'])

@router.post("/explain-term", response_model=ExplainTermResponse)
def explain_term(
    body: ExplainTermRequest,
    current_user: str = Depends(get_current_user)
):
    """
    Explain medical terms (Gemini-powered) with context from abstracts.
    """
    # Pass both terms and abstracts to the service function
    result = explain_medical_terms(body.terms, body.abstracts)

    if result.startswith("ERROR:"):
        raise HTTPException(status_code=500, detail=result)

    return {"explanation": result}


@router.post("/analyze-methodology", response_model=MethodologyAnalysisResponse)
def analyze_methodology_endpoint(
    body: MethodologyAnalysisRequest,
    current_user: str = Depends(get_current_user)
):
    result = analyze_methodology(body.abstract)
    if result.startswith("ERROR:"):
        raise HTTPException(status_code=500, detail=result)
    return {"analysis": result}

@router.post("/research-gaps", response_model=ResearchGapResponse)
def research_gaps_endpoint(
    body: ResearchGapRequest,
    current_user: str = Depends(get_current_user)
):
    result = analyze_research_gaps(body.abstracts, body.topic or "")
    if result and result[0].startswith("ERROR:"):
        raise HTTPException(status_code=500, detail=result[0])
    return {"gaps": result}

@router.post("/literature-review", response_model=LiteratureReviewResponse)
def literature_review_endpoint(
    body: LiteratureReviewRequest,
    current_user: str = Depends(get_current_user)
):
    result = generate_literature_review(body.abstracts, body.topic)
    if result.startswith("ERROR:"):
        raise HTTPException(status_code=500, detail=result)
    return {"review": result}

@router.post("/compare-studies", response_model=StudyComparisonResponse)
def compare_studies_endpoint(
    body: StudyComparisonRequest,
    current_user: str = Depends(get_current_user)
):
    result = compare_studies(body.studies)
    if result.startswith("ERROR:"):
        raise HTTPException(status_code=500, detail=result)
    return {"comparison": result}
