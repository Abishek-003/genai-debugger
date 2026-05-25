import asyncio
import logging

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, ConfigDict

from models.request import QueryRequest
from services.llm_service import run_pipeline


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Query"])


class QueryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    initial_answer: str
    critique: str
    final_answer: str


@router.post(
    "/query",
    response_model=QueryResponse,
    summary="Debug code using the LLM pipeline",
    status_code=status.HTTP_200_OK,
)
async def process_query(req: QueryRequest) -> QueryResponse:
    try:
        result = await asyncio.to_thread(run_pipeline, req.query, req.code, req.logs)

        if not isinstance(result, dict):
            raise RuntimeError(f"Pipeline returned non-dict result: {type(result).__name__}")

        required_keys = {"initial_answer", "critique", "final_answer"}
        missing = required_keys - set(result.keys())
        if missing:
            raise RuntimeError(f"Pipeline returned incomplete result. Missing keys: {sorted(missing)}")

        return QueryResponse(
            initial_answer=result["initial_answer"],
            critique=result["critique"],
            final_answer=result["final_answer"],
        )

    except HTTPException:
        raise

    except ValueError as e:
        logger.warning("Client-facing validation error in /query: %s", e)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        ) from e

    except Exception as e:
        logger.exception("Unexpected error in /query")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error. Check logs.",
        ) from e