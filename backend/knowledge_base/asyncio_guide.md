# Asyncio Guide

> Auto-generated from 1 sources

## Source: https://docs.python.org/3/library/asyncio-task.html

Coroutines and tasks — Python 3.14.4 documentation
Navigation
index
modules
|
next
|
previous
|
Python
»
3.14.4 Documentation
»
The Python Standard Library
»
Networking and Interprocess Communication
»
asyncio
â Asynchronous I/O
»
Coroutines and tasks
|
Theme
Auto
Light
Dark
|
Coroutines and tasks
Â¶
This section outlines high-level asyncio APIs to work with coroutines
and Tasks.
Coroutines
Â¶
Source code:
Lib/asyncio/coroutines.py
Coroutines
declared with the async/await syntax is the
preferred way of writing asyncio applications.  For example, the following
snippet of code prints âhelloâ, waits 1 second,
and then prints âworldâ:
>>>
import
asyncio
>>>
async
def
main
():
...
print
(
'hello'
)
...
await
asyncio
.
sleep
(
1
)
...
print
(
'world'
)
>>>
asyncio
.
run
(
main
())
hello
world
Note that simply calling a coroutine will not schedule it to
be executed:
>>>
main
()
<coroutine object main at 0x1053bb7c8>
To actually run a coroutine, asyncio provides the following mechanisms:
The
asyncio.run()
function to run the top-level
entry point âmain()â function (see the above example.)
Awaiting on a coroutine.  The following snippet of code will
print âhelloâ after waiting for 1 second, and then print âworldâ
after waiting for
another
2 seconds:
import
asyncio
import
time
async
def
say_after
(
delay
,
what
):
await
asyncio
.
sleep
(
delay
)
print
(
what
)
async
def
main
():
print
(
f
"started at
{
time
.
strftime
(
'
%X
'
)
}
"
)
await
say_after
(
1
,
'hello'
)
await
say_after
(
2
,
'world'
)
print
(
f
"finished at
{
time
.
strftime
(
'
%X
'
)
}
"
)
asyncio
.
run
(
main
())
Expected output:
started
at
17
:
13
:
52
hello
world
finished
at
17
:
13
:
55
The
asyncio.create_task()
function to run coroutines
concurrently as asyncio
Tasks
.
Letâs modify the above example and run two
say_after
coroutines
concurrently
:
async
def
main
():
task1
=
asyncio
.
create_task
(
say_after
(
1
,
'hello'
))
task2
=
asyncio
.
create_task
(
say_after
(
2
,
'world'
))
print
(
f
"started at
{
time
.
strftime
(
'
%X
'
)
}
"
)
# Wait until both tasks are completed (should take
# around 2 seconds.)
await
task1
await
task2
print
(
f
"finished at
{
time
.
strftime
(
'
%X
'
)
}
"
)
Note that expected output now shows that the snippet runs
1 second faster than before:
started
at
17
:
14
:
32
hello
world
finished
at
17
:
14
:
34
The
asyncio.TaskGroup
class provides a more modern
alternative to
create_task()
.
Using this API, the last example becomes:
async
def
main
():
async
with
asyncio
.
TaskGroup
()
as

---

