# Pydantic Validation

> Auto-generated from 2 sources

## Source: https://docs.pydantic.dev/latest/concepts/validators/

Validators | Pydantic Docs
Skip to content
Validators
In addition to Pydantic’s
built-in validation capabilities
,
you can leverage custom validators at the field and model levels to enforce more complex constraints
and ensure the integrity of your data.
Field validators
API Documentation
pydantic.functional_validators.WrapValidator
pydantic.functional_validators.PlainValidator
pydantic.functional_validators.BeforeValidator
pydantic.functional_validators.AfterValidator
pydantic.functional_validators.field_validator
In its simplest form, a field validator is a callable taking the value to be validated as an argument and
returning the validated value
. The callable can perform checks for specific conditions (see
raising validation errors
) and make changes to the validated value (coercion or mutation).
Four
different types of validators can be used. They can all be defined using the
annotated pattern
or using the
@field_validator
decorator, applied on a
class method
:
After
validators
: run after Pydantic’s internal validation. They are generally more type safe and thus easier to implement.
Annotated pattern
Decorator
Here is an example of a validator performing a validation check, and returning the value unchanged.
from typing import Annotated
from pydantic import AfterValidator, BaseModel, ValidationError
def is_even(value: int) -> int:
  if value % 2 == 1:
      raise ValueError(f'{value} is not an even number')
  return value  # (1)
class Model(BaseModel):
  number: Annotated[int, AfterValidator(is_even)]
try:
  Model(number=1)
except ValidationError as err:
  print(err)
  """
  1 validation error for Model
  number
    Value error, 1 is not an even number [type=value_error, input_value=1, input_type=int]
  """
Note that it is important to return the validated value.
Here is an example of a validator performing a validation check, and returning the value unchanged,
this time using the
field_validator()
decorator.
from pydantic import BaseModel, ValidationError, field_validator
class Model(BaseModel):
  number: int
  @field_validator('number', mode='after')  # (1)
  @classmethod
  def is_even(cls, value: int) -> int:
      if value % 2 == 1:
          raise ValueError(f'{value} is not an even number')
      return value  # (2)
try:
  Model(number=1)
except ValidationError as err:
  print(err)
  """
  1 validation error for Model
  number
    Value error, 1 is not an even number [type=value_error, input_value=1, input_type=int]
  """
'after'
is the default mode for the decorator, and can be omitted.
Note that it is important to return the validated value.
Example mutating the value
Here is an example of a validator making changes to the validated value (no exception is raised).
Annotated pattern
Decorator
from typing import Annotated
from pydantic import AfterValidator, BaseModel
def double_number(value: int) -> int:
    return value * 2
class Model(BaseModel):
    number: Annotated[int, AfterValidator(double_number)]
print(Model(number=2))
#> number=4
from pydantic import BaseModel, field_validator
class Model(BaseModel):
  number: int
  @field_validator('number', mode='after')  # (1)
  @classmethod
  def double_number(cls, value: int) -> int:
      return value * 2
print(Model(number=2))
#> number=4
'after'
is the default mode for the decorator, and can be omitted.
Before
validators
: run before Pydantic’s internal parsing and validation (e.g. coercion of a
str
to an
int
).
These are more flexible than
after
validators
, but they also have to deal with the raw input, which
in theory could be any arbitrary object. You should also avoid mutating the value directly if you are raising a
validation error
later in your validator function, as the mutated value may be passed to other
validators if using
unions
.
The value returned from this callable is then validated against the provided type annotation by Pydantic.
Annotated pattern
Decorator
from typing import Annotated, Any
from pydantic import BaseModel, BeforeValidator, ValidationError
def ensure_list(value: Any) -> Any:  # (1)
  if not isinstance(value, list):  # (2)
      return [value]
  else:
      return value
class Model(BaseModel):
  numbers: Annotated[list[int], BeforeValidator(ensure_list)]
print(Model(numbers=2))
#> numbers=[2]
try:
  Model(numbers='str')
except ValidationError as err:
  print(err)  # (3)
  """
  1 validation error for Model
  numbers.0
    Input should be a valid integer, unable to parse string as an integer [type=int_parsing, input_value='str', input_type=str]
  """
Notice the use of
Any
as a type hint for
value
.
Before
validators take the raw input, which
can be anything.
Note that you might want to check for other sequence types (such as tuples) that would normally successfully
validate against the
list
type.
Before
validators give you more flexibility, but you have to account for
every possible case.
Pydantic still performs validation against the
int
type, no matter if our
ensure_list
validator
did operations on the original input type.
from typing import Any
from pydantic import BaseModel, ValidationError, field_validator
class Model(BaseModel):
  numbers: list[int]
  @field_validator('numbers', mode='before')
  @classmethod
  def ensure_list(cls, value: Any) -> Any:  # (1)
      if not isinstance(value, list):  # (2)
          return [value]
      else:
          return value
print(Model(numbers=2))
#> numbers=[2]
try:
  Model(numbers='str')
except ValidationError as err:
  print(err)  # (3)
  """
  1 validation error for Model
  numbers.0
    Input should be a valid integer, unable to parse string as an integer [type=int_parsing, input_value='str', input_type=str]
  """
Notice the use of
Any
as a type hint for
value
.
Before
validators take the raw input, which
can be anything.
Note that you might want to check for other sequence types (such as tuples) that would normally successfully
validate against the
list
type.
Before
validators give you more flexibility, but you have to account for
every possible case.
Pydantic still performs validation against the
int
type, no matter if our
ensure_list
validator
did operations on the original input type.
Plain
validators
: act similarly to
before
validators but they
terminate validation immediately
after returning,
so no further validators are called and Pydantic does not do any of its internal validation against the field type.
Annotated pattern
Decorator
from typing import Annotated, Any
from pydantic import BaseModel, PlainValidator
def val_number(value: Any) -> Any:
  if isinstance(value, int):
      return value * 2
  else:
      return value
class Model(BaseModel):
  number: Annotated[int, PlainValidator(val_number)]
print(Model(number=4))
#> number=8
print(Model(number='invalid'))  # (1)
#> number='invalid'
Although
'invalid'
shouldn't validate against the
int
type, Pydantic accepts the input.
from typing import Any
from pydantic import BaseModel, field_validator
class Model(BaseModel):
  number: int
  @field_validator('number', mode='plain')
  @classmethod
  def val_number(cls, value: Any) -> Any:
      if isinstance(value, int):
          return value * 2
      else:
          return value
print(Model(number=4))
#> number=8
print(Model(number='invalid'))  # (1)
#> number='invalid'
Although
'invalid'
shouldn't validate against the
int
type, Pydantic accepts the input.
Wrap
validators
: are the most flexible of all. You can run code before or after Pydantic and other validators
process the input, or you can terminate validation immediately, either by returning the value early or by raising an
error.
Such validators must be defined with a
mandatory
extra
handler
parameter: a callable taking the value to be validated
as an argument. Internally, this handler will delegate validation of the value to Pydantic. You are free to wrap the call
to the handler in a
try..except
block, or not call it at all.
Annotated pattern
Decorator
from typing import Any
from typing import Annotated
from pydantic import BaseModel, Field, ValidationError, ValidatorFunctionWrapHandler, WrapValidator
def truncate(value: Any, handler: ValidatorFunctionWrapHandler) -> str:
    try:
        return handler(value)
    except ValidationError as err:
        if err.errors()[0]['type'] == 'string_too_long':
            return handler(value[:5])
        else:
            raise
class Model(BaseModel):
    my_string: Annotated[str, Field(max_length=5), WrapValidator(truncate)]
print(Model(my_string='abcde'))
#> my_string='abcde'
print(Model(my_string='abcdef'))
#> my_string='abcde'
from typing import Any
from typing import Annotated
from pydantic import BaseModel, Field, ValidationError, ValidatorFunctionWrapHandler, field_validator
class Model(BaseModel):
    my_string: Annotated[str, Field(max_length=5)]
    @field_validator('my_string', mode='wrap')
    @classmethod
    def truncate(cls, value: Any, handler: ValidatorFunctionWrapHandler) -> str:
        try:
            return handler(value)
        except ValidationError as err:
            if err.errors()[0]['type'] == 'string_too_long':
                return handler(value[:5])
            else:
                raise

---

## Source: https://docs.pydantic.dev/latest/concepts/fields/

Fields | Pydantic Docs
Skip to content
Fields
API Documentation
pydantic.fields.Field
In this section, we will go through the available mechanisms to customize Pydantic model fields:
default values
,
JSON Schema metadata
,
constraints
, etc.
To do so, the
Field()
function is used a lot, and behaves the same way as
the standard library
field()
function for dataclasses – by assigning to the
annotated attribute:
from pydantic import BaseModel, Field
class Model(BaseModel):
    name: str = Field(frozen=True)
The annotated pattern
To apply constraints or attach
Field()
functions to a model field, Pydantic
also supports the
Annotated
typing construct to attach metadata to an annotation:
from typing import Annotated
from pydantic import BaseModel, Field, WithJsonSchema
class Model(BaseModel):
    name: Annotated[str, Field(strict=True), WithJsonSchema({'extra': 'data'})]
As far as static type checkers are concerned,
name
is still typed as
str
, but Pydantic leverages
the available metadata to add validation logic, type constraints, etc.
Using this pattern has some advantages:
Using the
f: <type> = Field(...)
form can be confusing and might trick users into thinking
f
has a default value, while in reality it is still required.
You can provide an arbitrary amount of metadata elements for a field. As shown in the example above,
the
Field()
function only supports a limited set of constraints/metadata,
and you may have to use different Pydantic utilities such as
WithJsonSchema
in some cases.
Types can be made reusable (see the documentation on
custom types
using this pattern).
However, note that certain arguments to the
Field()
function (namely,
default
,
default_factory
, and
alias
) are taken into account by static type checkers to synthesize a correct
__init__()
method. The annotated pattern is
not
understood by them, so you should use the normal
assignment form instead.
class Model(BaseModel):
  field_bad: Annotated[int, Field(deprecated=True)] | None = None  # (1)
  field_ok: Annotated[int | None, Field(deprecated=True)] = None  # (2)
The
Field()
function is applied to
int
type, hence the
deprecated
flag won't have any effect. While this may be confusing given that the name of
the
Field()
function would imply it should apply to the field,
the API was designed when this function was the only way to provide metadata. You can
alternatively make use of the
annotated_types
library which is now supported by Pydantic.
The
Field()
function is applied to the "top-level" union type,
hence the
deprecated
flag will be applied to the field.
Inspecting model fields
The fields of a model can be inspected using the
model_fields
class attribute
(or the
__pydantic_fields__
attribute for
Pydantic dataclasses
). It is a mapping of field names
to their definition (represented as
FieldInfo
instances).
from typing import Annotated
from pydantic import BaseModel, Field, WithJsonSchema
class Model(BaseModel):
    a: Annotated[
        int, Field(gt=1), WithJsonSchema({'extra': 'data'}), Field(alias='b')
    ] = 1
field_info = Model.model_fields['a']
print(field_info.annotation)
#> <class 'int'>
print(field_info.alias)
#> b
print(field_info.metadata)
#> [Gt(gt=1), WithJsonSchema(json_schema={'extra': 'data'}, mode=None)]
⚠
Deprecated in v2.11, removed in v3
model_fields
can only be accessed from the class object, not the instance.
Default values
Default values for fields can be provided using the normal assignment syntax or by providing a value
to the
default
argument:
from pydantic import BaseModel, Field
class User(BaseModel):
    # Both fields aren't required:
    name: str = 'John Doe'
    age: int = Field(default=20)
↻
Changed in v2
In Pydantic V1
, a type annotated as
Any
or wrapped by
Optional
would be given an implicit default of
None
even if no
default was explicitly specified. This is no longer the case in Pydantic V2.
You can also pass a callable to the
default_factory
argument that will be called to generate a default value:
from uuid import uuid4
from pydantic import BaseModel, Field
class User(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
The default factory can also take a single required argument, in which case the already validated data will be passed as a dictionary.
from pydantic import BaseModel, EmailStr, Field
class User(BaseModel):
    email: EmailStr
    username: str = Field(default_factory=lambda data: data['email'])
user = User(email='
[email protected]
')
print(user.username)
#>
[email protected]
The
data
argument will
only
contain the already validated data, based on the
order of model fields
(the above example would fail if
username
were to be defined before
email
).
✦
New in v2.10
Default factories can take already validated data as an argument.
✦
New in v2.13
Default factories for
private attributes
can take the validated data as an argument.
Validate default values
By default, Pydantic will
not
validate default values. The
validate_default
field parameter
(or the
validate_default
configuration value) can be used
to enable this behavior:
from pydantic import BaseModel, Field, ValidationError
class User(BaseModel):
    age: int = Field(default='twelve', validate_default=True)
try:
    user = User()
except ValidationError as e:
    print(e)
    """
    1 validation error for User
    age
      Input should be a valid integer, unable to parse string as an integer [type=int_parsing, input_value='twelve', input_type=str]
    """
Mutable default values
A common source of bugs in Python is to use a mutable object as a default value for a function or method argument,
as the same instance ends up being reused in each call.
The
dataclasses
module actually raises an error in this case, indicating that you should use
a
default factory
instead.
While the same thing can be done in Pydantic, it is not required. In the event that the default value is not hashable,
Pydantic will create a deep copy of the default value when creating each instance of the model:
from pydantic import BaseModel
class Model(BaseModel):
    item_counts: list[dict[str, int]] = [{}]
m1 = Model()
m1.item_counts[0]['a'] = 1
print(m1.item_counts)
#> [{'a': 1}]
m2 = Model()
print(m2.item_counts)
#> [{}]
Field aliases
For validation and serialization, you can define an alias for a field.
There are three ways to define an alias:
Field(alias='foo')
Field(validation_alias='foo')
Field(serialization_alias='foo')
The
alias
parameter is used for both validation
and
serialization. If you want to use
different
aliases for validation and serialization respectively, you can use the
validation_alias
and
serialization_alias
parameters, which will apply only in their respective use cases.
Here is an example of using the
alias
parameter:
from pydantic import BaseModel, Field
class User(BaseModel):
  name: str = Field(alias='username')
user = User(username='johndoe')  # (1)
print(user)
#> name='johndoe'
print(user.model_dump(by_alias=True))  # (2)
#> {'username': 'johndoe'}
The alias
'username'
is used for instance creation and validation.
We are using
model_dump()
to convert the model into a serializable format.
Note that the
by_alias
keyword argument defaults to
False
, and must be specified explicitly to dump
models using the field (serialization) aliases.
You can also use
ConfigDict.serialize_by_alias
to
configure this behavior at the model level.
When
by_alias=True
, the alias
'username'
used during serialization.
If you want to use an alias
only
for validation, you can use the
validation_alias
parameter:
from pydantic import BaseModel, Field
class User(BaseModel):
  name: str = Field(validation_alias='username')
user = User(username='johndoe')  # (1)
print(user)
#> name='johndoe'
print(user.model_dump(by_alias=True))  # (2)
#> {'name': 'johndoe'}
The validation alias
'username'
is used during validation.
The field name
'name'
is used during serialization.
If you only want to define an alias for
serialization
, you can use the
serialization_alias
parameter:
from pydantic import BaseModel, Field
class User(BaseModel):
  name: str = Field(serialization_alias='username')
user = User(name='johndoe')  # (1)
print(user)

---

