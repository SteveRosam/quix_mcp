# MCP Hello World (FastAPI)

## Run Locally
```
pip install -r requirements.txt
uvicorn main:app --reload
```

## Run with Docker
```
docker build -t mcp-server .
docker run -p 8000:8000 mcp-server
```

Then visit: http://localhost:8000/
