from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from google.api_core.exceptions import GoogleAPICallError

from app.config import allowed_origins
from app.routers import chat, conversations, data


app = FastAPI(title="Pageful API", version="1.0.0", description="독서 습관 분석 AI 비서 API")


@app.exception_handler(GoogleAPICallError)
async def database_error(_request, _error):
    return JSONResponse(status_code=503, content={"detail": "데이터베이스에 연결하지 못했습니다. 잠시 후 다시 시도해 주세요."})


app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}


app.include_router(data.router)
app.include_router(conversations.router)
app.include_router(chat.router)
