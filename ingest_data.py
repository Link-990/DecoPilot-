import os
from knowledge_base import KnowledgeBaseService

def ingest_decoration_knowledge():
    file_path = "data/装修小知识.txt"
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    service = KnowledgeBaseService()
    print("Ingesting data...")
    result = service.upload_by_str(content, "装修小知识.txt")
    print(result)

if __name__ == "__main__":
    ingest_decoration_knowledge()
