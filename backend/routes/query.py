import asyncio
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from models.request import QueryRequest
from services.llm_service import run_pipeline

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Query"])


# 🔹 Response model — documents what the endpoint returns
class QueryResponse(BaseModel):
    initial_answer: str
    critique: str
    final_answer: str


@router.post(
    "/query",
    response_model=QueryResponse,
    summary="Debug code using the LLM pipeline",
    status_code=200
)
async def process_query(req: QueryRequest):
    try:
        result = await asyncio.to_thread(run_pipeline, req.query, req.code, req.logs)
        
        # Guard: ensure all expected keys are present
        if not all(k in result for k in ("initial_answer", "critique", "final_answer")):
            raise ValueError(f"Pipeline returned incomplete result: {result.keys()}")
        
        return QueryResponse(**result)

    except ValueError as e:
        logger.error(f"Pipeline value error: {e}")
        raise HTTPException(status_code=422, detail=str(e))

    except Exception as e:
        logger.exception(f"Unexpected error in /query: {e}")
        raise HTTPException(status_code=500, detail="Internal server error. Check logs.")