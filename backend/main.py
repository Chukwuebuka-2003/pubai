from fastapi import FastAPI
from routers.auth import router as auth_router
from routers.search import router as search_router
from routers.user_router import router as user_router
from routers.search_history import router as search_history_router
from routers.ai import router as ai_router
from advanced_research import router as advanced_router  # Add this
from database import init_db

app = FastAPI()

# Initialize DB
init_db()

# Include Routers
app.include_router(auth_router)
app.include_router(search_router)
app.include_router(user_router)
app.include_router(search_history_router)
app.include_router(advanced_router)  # Add this
app.include_router(ai_router)

@app.get("/")
def read_root():
    return {"hello": "welcome to PubMed FastAPI backend"}
