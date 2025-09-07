# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers.auth import router as auth_router
from routers.search import router as search_router
from routers.user_router import router as user_router
from routers.search_history import router as search_history_router
from routers.ai import router as ai_router
from advanced_research import router as advanced_router
from database import init_db

app = FastAPI()


origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://satoru-ai.vercel.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,  # Allow cookies to be sent (for JWT tokens, etc.)
    allow_methods=["*"],     # Allow all HTTP methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],     # Allow all headers
)



init_db()


app.include_router(auth_router)
app.include_router(search_router)
app.include_router(user_router)
app.include_router(search_history_router)
app.include_router(advanced_router)
app.include_router(ai_router)

@app.get("/")
def read_root():
    return {"hello": "welcome to PubMed FastAPI backend"}
