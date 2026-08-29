add an .env to /backend
such as:


LLM_API_KEY=Your API Key
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL=qwen3.7-plus

EMBEDDING_MODEL=text-embedding-v4
EMBEDDING_DIMENSIONS=1024

# 每个论文片段大概1800个字符
RAG_CHUNK_SIZE=1800
# 相邻 Chunk 保留 250 字符重叠，避免一句关键内容刚好被切断
RAG_CHUNK_OVERLAP=250
# 每条 Reviewer Comment 最终找最相关的 6 个论文片段
RAG_TOP_K=6


then add an /venv to /backend

start with start.ipynb
