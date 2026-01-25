import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import json
import asyncio
import os
from rag import RagService

app = FastAPI()

# 允许跨域 (方便前端开发时调试)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化 RAG 服务
rag_service = RagService()

@app.post("/chat_stream")
async def chat_stream(request: Request):
    data = await request.json()
    message = data.get("message")
    
    # 更新 RAG 配置
    rag_service.enable_search = data.get("enable_search", True)
    rag_service.show_thinking = data.get("show_thinking", True)

    async def event_generator():
        session_config = {"configurable": {"session_id": "user_react_001"}}
        input_data = {"input": message}
        
        try:
            # 使用 astream_events 监听所有事件
            async for event in rag_service.chain.astream_events(input_data, session_config, version="v1"):
                kind = event["event"]
                
                # 1. 捕获检索结束事件 (获取思考过程)
                if kind == "on_retriever_end":
                    # event["data"]["output"] 是 Document 列表
                    if "output" in event["data"]:
                        docs = event["data"]["output"]
                        if docs:
                            # 检查是否有 thinking_log
                            first_doc = docs[0]
                            if hasattr(first_doc, "metadata") and "thinking_log" in first_doc.metadata:
                                logs = first_doc.metadata["thinking_log"]
                                yield json.dumps({"type": "thinking", "content": logs}, ensure_ascii=False) + "\n"
                            
                # 2. 捕获模型生成的答案流
                elif kind == "on_chat_model_stream":
                    chunk = event["data"]["chunk"]
                    if hasattr(chunk, "content") and chunk.content:
                        yield json.dumps({"type": "answer", "content": chunk.content}, ensure_ascii=False) + "\n"
        except Exception as e:
            yield json.dumps({"type": "error", "content": str(e)}, ensure_ascii=False) + "\n"

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")

if __name__ == "__main__":
    print("Server running at http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
