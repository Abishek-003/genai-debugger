# Fastapi Errors

> Auto-generated from 5 sources

## Source: https://fastapi.tiangolo.com/tutorial/handling-errors/

Handling Errors - FastAPI
Skip to content
Handling Errors
¶
There are many situations in which you need to notify an error to a client that is using your API.
This client could be a browser with a frontend, a code from someone else, an IoT device, etc.
You could need to tell the client that:
The client doesn't have enough privileges for that operation.
The client doesn't have access to that resource.
The item the client was trying to access doesn't exist.
etc.
In these cases, you would normally return an
HTTP status code
in the range of
400
(from 400 to 499).
This is similar to the 200 HTTP status codes (from 200 to 299). Those "200" status codes mean that somehow there was a "success" in the request.
The status codes in the 400 range mean that there was an error from the client.
Remember all those
"404 Not Found"
errors (and jokes)?
Use
HTTPException
¶
To return HTTP responses with errors to the client you use
HTTPException
.
Import
HTTPException
¶
Python 3.10+
from
fastapi
import
FastAPI
,
HTTPException
app
=
FastAPI
()
items
=
{
"foo"
:
"The Foo Wrestlers"
}
@app
.
get
(
"/items/
{item_id}
"
)
async
def
read_item
(
item_id
:
str
):
if
item_id
not
in
items
:
raise
HTTPException
(
status_code
=
404
,
detail
=
"Item not found"
)
return
{
"item"
:
items
[
item_id
]}
Raise an
HTTPException
in your code
¶
HTTPException
is a normal Python exception with additional data relevant for APIs.
Because it's a Python exception, you don't
return
it, you
raise
it.
This also means that if you are inside a utility function that you are calling inside of your
path operation function
, and you raise the
HTTPException
from inside of that utility function, it won't run the rest of the code in the
path operation function
, it will terminate that request right away and send the HTTP error from the
HTTPException
to the client.
The benefit of raising an exception over returning a value will be more evident in the section about Dependencies and Security.
In this example, when the client requests an item by an ID that doesn't exist, raise an exception with a status code of
404
:
Python 3.10+
from
fastapi
import
FastAPI
,
HTTPException
app
=
FastAPI
()
items
=
{
"foo"
:
"The Foo Wrestlers"
}
@app
.
get
(
"/items/
{item_id}
"
)
async
def
read_item
(
item_id
:
str
):
if
item_id
not
in
items
:
raise
HTTPException
(
status_code
=
404
,
detail
=
"Item not found"
)
return
{
"item"
:
items
[
item_id
]}
The resulting response
¶
If the client requests
http://example.com/items/foo
(an
item_id
"foo"
), that client will receive an HTTP status code of 200, and a JSON response of:
{
"item"
:
"The Foo Wrestlers"
}
But if the client requests
http://example.com/items/bar
(a non-existent
item_id
"bar"
), that client will receive an HTTP status code of 404 (the "not found" error), and a JSON response of:
{
"detail"
:
"Item not found"
}
Tip
When raising an
HTTPException
, you can pass any value that can be converted to JSON as the parameter
detail
, not only
str
.
You could pass a
dict
, a
list
, etc.
They are handled automatically by
FastAPI
and converted to JSON.
Add custom headers
¶
There are some situations in where it's useful to be able to add custom headers to the HTTP error. For example, for some types of security.
You probably won't need to use it directly in your code.
But in case you needed it for an advanced scenario, you can add custom headers:
Python 3.10+
from
fastapi
import
FastAPI
,
HTTPException
app
=
FastAPI
()
items
=
{
"foo"
:
"The Foo Wrestlers"
}
@app
.
get
(
"/items-header/
{item_id}
"
)
async
def
read_item_header
(
item_id
:
str
):
if
item_id
not
in
items
:
raise
HTTPException
(
status_code
=
404
,
detail
=
"Item not found"
,
headers
=
{
"X-Error"
:
"There goes my error"
},
)
return
{
"item"
:
items
[
item_id
]}
Install custom exception handlers
¶
You can add custom exception handlers with
the same exception utilities from Starlette
.
Let's say you have a custom exception
UnicornException
that you (or a library you use) might
raise
.
And you want to handle this exception globally with FastAPI.
You could add a custom exception handler with
@app.exception_handler()
:
Python 3.10+
from

---

## Source: https://fastapi.tiangolo.com/tutorial/body/

Request Body - FastAPI
Skip to content
Request Body
¶
When you need to send data from a client (let's say, a browser) to your API, you send it as a
request body
.
A
request
body is data sent by the client to your API. A
response
body is the data your API sends to the client.
Your API almost always has to send a
response
body. But clients don't necessarily need to send
request bodies
all the time, sometimes they only request a path, maybe with some query parameters, but don't send a body.
To declare a
request
body, you use
Pydantic
models with all their power and benefits.
Info
To send data, you should use one of:
POST
(the more common),
PUT
,
DELETE
or
PATCH
.
Sending a body with a
GET
request has an undefined behavior in the specifications, nevertheless, it is supported by FastAPI, only for very complex/extreme use cases.
As it is discouraged, the interactive docs with Swagger UI won't show the documentation for the body when using
GET
, and proxies in the middle might not support it.
Import Pydantic's
BaseModel
¶
First, you need to import
BaseModel
from
pydantic
:
Python 3.10+
from
fastapi
import
FastAPI
from
pydantic
import
BaseModel
class
Item
(
BaseModel
):
name
:
str
description
:
str
|
None
=
None
price
:
float
tax
:
float
|
None
=
None
app
=
FastAPI
()
@app
.
post
(
"/items/"
)
async
def
create_item
(
item
:
Item
):
return
item
Create your data model
¶
Then you declare your data model as a class that inherits from
BaseModel
.
Use standard Python types for all the attributes:
Python 3.10+
from
fastapi
import
FastAPI
from
pydantic
import
BaseModel
class
Item
(
BaseModel
):
name
:
str
description
:
str
|
None
=
None
price
:
float
tax
:
float
|
None
=
None
app
=
FastAPI
()
@app
.
post
(
"/items/"
)
async
def
create_item
(
item
:
Item
):
return
item
The same as when declaring query parameters, when a model attribute has a default value, it is not required. Otherwise, it is required. Use
None
to make it just optional.
For example, this model above declares a JSON "
object
" (or Python
dict
) like:
{
"name"
:
"Foo"
,
"description"
:
"An optional description"
,
"price"
:
45.2
,
"tax"
:
3.5
}
...as
description
and
tax
are optional (with a default value of
None
), this JSON "
object
" would also be valid:
{
"name"
:
"Foo"
,
"price"
:
45.2
}
Declare it as a parameter
¶
To add it to your
path operation
, declare it the same way you declared path and query parameters:
Python 3.10+
from
fastapi
import
FastAPI
from
pydantic
import
BaseModel
class
Item
(
BaseModel
):
name
:
str
description
:
str
|
None
=
None
price
:
float
tax
:
float
|
None
=
None
app
=
FastAPI
()
@app
.
post
(
"/items/"
)
async
def
create_item
(
item
:
Item
):
return
item
...and declare its type as the model you created,
Item
.
Results
¶
With just that Python type declaration,
FastAPI
will:
Read the body of the request as JSON.
Convert the corresponding types (if needed).
Validate the data.
If the data is invalid, it will return a nice and clear error, indicating exactly where and what was the incorrect data.
Give you the received data in the parameter
item
.
As you declared it in the function to be of type
Item
, you will also have all the editor support (completion, etc) for all of the attributes and their types.
Generate
JSON Schema
definitions for your model, you can also use them anywhere else you like if it makes sense for your project.
Those schemas will be part of the generated OpenAPI schema, and used by the automatic documentation
UIs
.
Automatic docs
¶
The JSON Schemas of your models will be part of your OpenAPI generated schema, and will be shown in the interactive API docs:
And will also be used in the API docs inside each
path operation
that needs them:
Editor support
¶
In your editor, inside your function you will get type hints and completion everywhere (this wouldn't happen if you received a
dict
instead of a Pydantic model):
You also get error checks for incorrect type operations:
This is not by chance, the whole framework was built around that design.
And it was thoroughly tested at the design phase, before any implementation, to ensure it would work with all the editors.

---

## Source: https://fastapi.tiangolo.com/tutorial/response-model/

Response Model - Return Type - FastAPI
Skip to content
Response Model - Return Type
¶
You can declare the type used for the response by annotating the
path operation function
return type
.
You can use
type annotations
the same way you would for input data in function
parameters
, you can use Pydantic models, lists, dictionaries, scalar values like integers, booleans, etc.
Python 3.10+
from
fastapi
import
FastAPI
from
pydantic
import
BaseModel
app
=
FastAPI
()
class
Item
(
BaseModel
):
name
:
str
description
:
str
|
None
=
None
price
:
float
tax
:
float
|
None
=
None
tags
:
list
[
str
]
=
[]
@app
.
post
(
"/items/"
)
async
def
create_item
(
item
:
Item
)
->
Item
:
return
item
@app
.
get
(
"/items/"
)
async
def
read_items
()
->
list
[
Item
]:
return
[
Item
(
name
=
"Portal Gun"
,
price
=
42.0
),
Item
(
name
=
"Plumbus"
,
price
=
32.0
),
]
FastAPI will use this return type to:
Validate
the returned data.
If the data is invalid (e.g. you are missing a field), it means that
your
app code is broken, not returning what it should, and it will return a server error instead of returning incorrect data. This way you and your clients can be certain that they will receive the data and the data shape expected.
Add a
JSON Schema
for the response, in the OpenAPI
path operation
.
This will be used by the
automatic docs
.
It will also be used by automatic client code generation tools.
Serialize
the returned data to JSON using Pydantic, which is written in
Rust
, so it will be
much faster
.
But most importantly:
It will
limit and filter
the output data to what is defined in the return type.
This is particularly important for
security
, we'll see more of that below.
response_model
Parameter
¶
There are some cases where you need or want to return some data that is not exactly what the type declares.
For example, you could want to
return a dictionary
or a database object, but
declare it as a Pydantic model
. This way the Pydantic model would do all the data documentation, validation, etc. for the object that you returned (e.g. a dictionary or database object).
If you added the return type annotation, tools and editors would complain with a (correct) error telling you that your function is returning a type (e.g. a dict) that is different from what you declared (e.g. a Pydantic model).
In those cases, you can use the
path operation decorator
parameter
response_model
instead of the return type.
You can use the
response_model
parameter in any of the
path operations
:
@app.get()
@app.post()
@app.put()
@app.delete()
etc.
Python 3.10+
from
typing
import
Any
from
fastapi
import
FastAPI
from
pydantic
import
BaseModel
app
=
FastAPI
()
class
Item
(
BaseModel
):
name
:
str
description
:
str
|
None
=
None
price
:
float
tax
:
float
|
None
=
None
tags
:
list
[
str
]
=
[]
@app
.
post
(
"/items/"
,
response_model
=
Item
)
async
def
create_item
(
item
:
Item
)
->
Any
:
return
item
@app
.
get
(
"/items/"
,
response_model
=
list
[
Item
])
async
def
read_items
()
->
Any
:
return
[
{
"name"
:
"Portal Gun"
,
"price"
:
42.0
},
{
"name"
:
"Plumbus"
,
"price"
:
32.0
},
]
Note
Notice that
response_model
is a parameter of the "decorator" method (
get
,
post
, etc). Not of your
path operation function
, like all the parameters and body.
response_model
receives the same type you would declare for a Pydantic model field, so, it can be a Pydantic model, but it can also be, e.g. a
list
of Pydantic models, like
List[Item]
.
FastAPI will use this
response_model

---

## Source: https://fastapi.tiangolo.com/tutorial/middleware/

Middleware - FastAPI
Skip to content
Middleware
¶
You can add middleware to
FastAPI
applications.
A "middleware" is a function that works with every
request
before it is processed by any specific
path operation
. And also with every
response
before returning it.
It takes each
request
that comes to your application.
It can then do something to that
request
or run any needed code.
Then it passes the
request
to be processed by the rest of the application (by some
path operation
).
It then takes the
response
generated by the application (by some
path operation
).
It can do something to that
response
or run any needed code.
Then it returns the
response
.
Technical Details
If you have dependencies with
yield
, the exit code will run
after
the middleware.
If there were any background tasks (covered in the
Background Tasks
section, you will see it later), they will run
after
all the middleware.
Create a middleware
¶
To create a middleware you use the decorator
@app.middleware("http")
on top of a function.
The middleware function receives:
The
request
.
A function
call_next
that will receive the
request
as a parameter.
This function will pass the
request
to the corresponding
path operation
.
Then it returns the
response
generated by the corresponding
path operation
.
You can then further modify the
response
before returning it.
Python 3.10+
import
time
from
fastapi
import
FastAPI
,
Request
app
=
FastAPI
()
@app
.
middleware
(
"http"
)
async
def
add_process_time_header
(
request
:
Request
,
call_next
):
start_time
=
time
.
perf_counter
()
response
=
await
call_next
(
request
)
process_time
=
time
.
perf_counter
()
-
start_time
response
.
headers
[
"X-Process-Time"
]
=
str
(
process_time
)
return
response
Tip
Keep in mind that custom proprietary headers can be added
using the
X-
prefix
.
But if you have custom headers that you want a client in a browser to be able to see, you need to add them to your CORS configurations (
CORS (Cross-Origin Resource Sharing)
) using the parameter
expose_headers
documented in
Starlette's CORS docs
.
Technical Details
You could also use
from starlette.requests import Request
.
FastAPI
provides it as a convenience for you, the developer. But it comes directly from Starlette.
Before and after the
response
¶
You can add code to be run with the
request
,  before any
path operation
receives it.
And also after the
response
is generated, before returning it.
For example, you could add a custom header
X-Process-Time
containing the time in seconds that it took to process the request and generate a response:
Python 3.10+
import
time
from
fastapi
import
FastAPI
,
Request
app
=
FastAPI
()
@app
.
middleware
(
"http"
)
async
def
add_process_time_header
(
request
:
Request
,
call_next
):
start_time
=
time
.
perf_counter
()
response
=
await
call_next
(
request
)
process_time
=
time
.
perf_counter
()
-
start_time
response
.
headers
[
"X-Process-Time"
]
=
str
(
process_time
)
return
response
Tip
Here we use
time.perf_counter()
instead of
time.time()
because it can be more precise for these use cases. 🤓
Multiple middleware execution order
¶
When you add multiple middlewares using either
@app.middleware()
decorator or
app.add_middleware()
method, each new middleware wraps the application, forming a stack. The last middleware added is the
outermost
, and the first is the
innermost
.
On the request path, the
outermost
middleware runs first.
On the response path, it runs last.
For example:
app
.
add_middleware
(
MiddlewareA
)
app
.
add_middleware
(
MiddlewareB
)
This results in the following execution order:
Request
: MiddlewareB → MiddlewareA → route
Response
: route → MiddlewareA → MiddlewareB
This stacking behavior ensures that middlewares are executed in a predictable and controllable order.
Other middlewares
¶
You can later read more about other middlewares in the
Advanced User Guide: Advanced Middleware
.
You will read about how to handle
CORS
with a middleware in the next section.
Back to top

---

## Source: https://fastapi.tiangolo.com/tutorial/cors/

CORS (Cross-Origin Resource Sharing) - FastAPI
Skip to content
CORS (Cross-Origin Resource Sharing)
¶
CORS or "Cross-Origin Resource Sharing"
refers to the situations when a frontend running in a browser has JavaScript code that communicates with a backend, and the backend is in a different "origin" than the frontend.
Origin
¶
An origin is the combination of protocol (
http
,
https
), domain (
myapp.com
,
localhost
,
localhost.tiangolo.com
), and port (
80
,
443
,
8080
).
So, all these are different origins:
http://localhost
https://localhost
http://localhost:8080
Even if they are all in
localhost
, they use different protocols or ports, so, they are different "origins".
Steps
¶
So, let's say you have a frontend running in your browser at
http://localhost:8080
, and its JavaScript is trying to communicate with a backend running at
http://localhost
(because we don't specify a port, the browser will assume the default port
80
).
Then, the browser will send an HTTP
OPTIONS
request to the
:80
-backend, and if the backend sends the appropriate headers authorizing the communication from this different origin (
http://localhost:8080
) then the
:8080
-browser will let the JavaScript in the frontend send its request to the
:80
-backend.
To achieve this, the
:80
-backend must have a list of "allowed origins".
In this case, the list would have to include
http://localhost:8080
for the
:8080
-frontend to work correctly.
Wildcards
¶
It's also possible to declare the list as
"*"
(a "wildcard") to say that all are allowed.
But that will only allow certain types of communication, excluding everything that involves credentials: Cookies, Authorization headers like those used with Bearer Tokens, etc.
So, for everything to work correctly, it's better to specify explicitly the allowed origins.
Use
CORSMiddleware
¶
You can configure it in your
FastAPI
application using the
CORSMiddleware
.
Import
CORSMiddleware
.
Create a list of allowed origins (as strings).
Add it as a "middleware" to your
FastAPI
application.
You can also specify whether your backend allows:
Credentials (Authorization headers, Cookies, etc).
Specific HTTP methods (
POST
,
PUT
) or all of them with the wildcard
"*"
.
Specific HTTP headers or all of them with the wildcard
"*"
.
Python 3.10+
from
fastapi
import
FastAPI
from
fastapi.middleware.cors
import
CORSMiddleware
app
=
FastAPI
()
origins
=
[
"http://localhost.tiangolo.com"
,
"https://localhost.tiangolo.com"
,
"http://localhost"
,
"http://localhost:8080"
,
]
app
.
add_middleware
(
CORSMiddleware
,
allow_origins
=
origins
,
allow_credentials
=
True
,
allow_methods
=
[
"*"
],
allow_headers
=
[
"*"
],
)
@app
.
get
(
"/"
)
async
def
main
():
return
{
"message"
:
"Hello World"
}
The default parameters used by the
CORSMiddleware
implementation are restrictive by default, so you'll need to explicitly enable particular origins, methods, or headers, in order for browsers to be permitted to use them in a Cross-Domain context.
The following arguments are supported:
allow_origins
- A list of origins that should be permitted to make cross-origin requests. E.g.
['https://example.org', 'https://www.example.org']
. You can use
['*']
to allow any origin.
allow_origin_regex
- A regex string to match against origins that should be permitted to make cross-origin requests. e.g.
'https://.*\.example\.org'
.
allow_methods
- A list of HTTP methods that should be allowed for cross-origin requests. Defaults to
['GET']
. You can use
['*']
to allow all standard methods.
allow_headers
- A list of HTTP request headers that should be supported for cross-origin requests. Defaults to
[]
. You can use
['*']
to allow all headers. The
Accept
,
Accept-Language
,
Content-Language
and
Content-Type
headers are always allowed for
simple CORS requests
.
allow_credentials
- Indicate that cookies should be supported for cross-origin requests. Defaults to
False
.
None of
allow_origins
,
allow_methods
and
allow_headers
can be set to
['*']
if
allow_credentials
is set to
True
. All of them must be
explicitly specified
.
expose_headers
- Indicate any response headers that should be made accessible to the browser. Defaults to
[]
.
max_age
- Sets a maximum time in seconds for browsers to cache CORS responses. Defaults to
600
.
The middleware responds to two particular types of HTTP request...
CORS preflight requests
¶
These are any
OPTIONS
request with
Origin
and
Access-Control-Request-Method
headers.
In this case the middleware will intercept the incoming request and respond with appropriate CORS headers, and either a
200
or
400
response for informational purposes.
Simple requests
¶
Any request with an
Origin
header. In this case the middleware will pass the request through as normal, but will include appropriate CORS headers on the response.
More info
¶
For more info about
CORS
, check the
Mozilla CORS documentation
.
Technical Details
You could also use
from starlette.middleware.cors import CORSMiddleware
.
FastAPI
provides several middlewares in
fastapi.middleware
just as a convenience for you, the developer. But most of the available middlewares come directly from Starlette.
Back to top

---

