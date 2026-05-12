from pydantic import BaseModel, Field
from pydantic import ConfigDict


class QueryRequest(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra='forbid',
        json_schema_extra={
            "examples": [
                {
                    "query": "Why is my FastAPI endpoint returning 422?",
                    "code": "@app.post('/query')\ndef run(req: QueryRequest): ...",
                    "logs": "422 Unprocessable Entity"
                }
            ]
        }
    )

    query: str = Field(
        ...,
        min_length=3,
        max_length=2000,
        description="The debugging question or task description"
    )
    code: str = Field(
        default="",
        max_length=10000,
        description="The code snippet related to the query"
    )
    logs: str = Field(
        default="",
        max_length=5000,
        description="Error logs or stack traces"
    )