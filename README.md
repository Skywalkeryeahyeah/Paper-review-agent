add an .env to /backend
such as:


LLM_API_KEY=Your API Key
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL=qwen3.7-plus

EMBEDDING_MODEL=text-embedding-v4
EMBEDDING_DIMENSIONS=1024

RAG_CHUNK_SIZE=1800
RAG_CHUNK_OVERLAP=250
RAG_TOP_K=6


then add an /venv to /backend

start with start.ipynb
