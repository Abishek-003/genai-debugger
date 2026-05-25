from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator


class QueryRequest(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "query": "Why is my FastAPI endpoint returning 422?",
                    "code": "@app.post('/query')\ndef run(req: QueryRequest): ...",
                    "logs": "422 Unprocessable Entity",
                }
            ]
        },
    )

    query: str = Field(
        ...,
        min_length=3,
        max_length=2000,
        description="The debugging question or task description",
    )
    code: str = Field(
        default="",
        max_length=10000,
        description="The code snippet related to the query",
    )
    logs: str = Field(
        default="",
        max_length=5000,
        description="Error logs or stack traces",
    )

    @field_validator("code", "logs", mode="before")
    @classmethod
    def normalize_optional_text(cls, value):
        if value is None:
            return ""
        if isinstance(value, str):
            return value.strip()
        return value

    @model_validator(mode="after")
    def validate_meaningful_request(self):
        if not self.query.strip():
            raise ValueError("query must not be empty")
        if not (self.query.strip() or self.code.strip() or self.logs.strip()):
            raise ValueError("At least one of query, code, or logs must contain meaningful content")
        return self