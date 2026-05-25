# Pydantic — Common Errors and Fixes

---

## Error: `ValidationError` — field required

Cause: A required field (no default) was not passed during model instantiation.
Fix:
```python
class QueryRequest(BaseModel):
    query: str
    code: str
    logs: str = ""        # optional with default — won't raise if omitted
    timeout: int = 30     # optional with default

# Bad — missing 'code'
QueryRequest(query="fix this")   # ValidationError: code field required

# Good
QueryRequest(query="fix this", code="x =+ 1")
```

---

## Error: `ValidationError` — value is not a valid string (type=string_type)

Cause: A `str` field received `None` or an integer.
Fix:
```python
class MyModel(BaseModel):
    name: str

# Bad
MyModel(name=None)   # ValidationError

# Good — allow None explicitly
class MyModel(BaseModel):
    name: Optional[str] = None
```

---

## Error: `ValidationError` — value is not a valid integer (type=int_parsing)

Cause: A numeric string was passed to an `int` field. Pydantic V2 does not coerce strings to int by default.
Fix:
```python
# Option 1: Accept string and coerce
from pydantic import field_validator

class MyModel(BaseModel):
    count: int

    @field_validator("count", mode="before")
    @classmethod
    def parse_count(cls, v):
        return int(v) if isinstance(v, str) else v

# Option 2: Use model_config to allow coercion
from pydantic import ConfigDict

class MyModel(BaseModel):
    model_config = ConfigDict(coerce_numbers_to_str=True)
    count: int
```

---

## Error: Pydantic V1 vs V2 — `.dict()` deprecated

Cause: `.dict()` was removed in Pydantic V2; calling it raises `AttributeError`.
Fix:
```python
# Bad (V1 style)
data = my_model.dict()

# Good (V2)
data = my_model.model_dump()

# For JSON string
json_str = my_model.model_dump_json()
```

---

## Error: `model_fields` not found / `__fields__` empty

Cause: `__fields__` was removed in Pydantic V2.
Fix:
```python
# Bad (V1)
fields = MyModel.__fields__

# Good (V2)
fields = MyModel.model_fields
```

---

## Error: Mutable default value in Pydantic model field

Cause: Using a mutable object as a default directly raises an error in Pydantic V2.
Fix:
```python
from pydantic import BaseModel, Field

# Bad
class MyModel(BaseModel):
    tags: list = []    # raises SchemaError in V2

# Good
class MyModel(BaseModel):
    tags: list[str] = Field(default_factory=list)
```

---

## Error: `ValidationError` — extra fields not permitted

Cause: Model has `model_config = ConfigDict(extra="forbid")` and the request body contains unexpected fields.
Fix:
```python
# Allow extra fields to be ignored
from pydantic import ConfigDict

class QueryRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    query: str
    code: str
    logs: str = ""
```

---

## Error: `@validator` not working in Pydantic V2

Cause: `@validator` was deprecated and removed in Pydantic V2.
Fix:
```python
# Bad (V1)
from pydantic import validator

class MyModel(BaseModel):
    name: str

    @validator("name")
    def name_not_empty(cls, v):
        if not v.strip():
            raise ValueError("name must not be empty")
        return v

# Good (V2)
from pydantic import field_validator

class MyModel(BaseModel):
    name: str

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("name must not be empty")
        return v
```

---

## Error: Response model strips extra fields — data lost silently

Cause: FastAPI uses the response model to filter output — fields not declared in the model are silently dropped.
Fix: Declare all fields you want returned in the response model:
```python
class QueryResponse(BaseModel):
    initial_answer: str
    critique: str
    final_answer: str
    ast_bugs: list = Field(default_factory=list)  # add missing field
```

---

## Error: `orm_mode` not found in Pydantic V2

Cause: `orm_mode = True` was renamed to `from_attributes = True` in Pydantic V2.
Fix:
```python
# Bad (V1)
class MyModel(BaseModel):
    class Config:
        orm_mode = True

# Good (V2)
from pydantic import ConfigDict

class MyModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
```

---

## Error: Nested model validation fails silently

Cause: A nested Pydantic model field receives a plain dict — in V2 this is usually coerced automatically, but if types mismatch it silently uses defaults.
Fix:
```python
class Inner(BaseModel):
    score: float

class Outer(BaseModel):
    result: Inner

# Validate explicitly when unsure
try:
    obj = Outer.model_validate(raw_dict)
except ValidationError as e:
    print(e.errors())
```

---

## Error: `UUID` field fails when receiving string from JSON

Cause: JSON always carries UUIDs as strings; Pydantic V2 coerces them automatically, but V1 does not.
Fix (V1):
```python
from uuid import UUID
from pydantic import BaseModel

class MyModel(BaseModel):
    id: UUID   # V2 handles str→UUID automatically; V1 needs explicit validator

    @validator("id", pre=True)
    @classmethod
    def parse_uuid(cls, v):
        return UUID(v) if isinstance(v, str) else v
```
