FastAPI Server
==============

FastAPI with Basic Example


## Basic Example

```
uvicorn main:app --port 8000
```


## Using Depends and others

```
uvicorn main_extra:app --port 8000
```


## Handling disconnections and multiple clients

```
uvicorn main_with_multiple_client:app --port 8000
```
