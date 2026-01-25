import os
import glob
from knowledge_base import KnowledgeBaseService

def ingest_decoration_knowledge():
    # 获取 data 目录下所有的 txt 文件
    data_dir = "data"
    txt_files = glob.glob(os.path.join(data_dir, "*.txt"))
    
    if not txt_files:
        print(f"No .txt files found in {data_dir}")
        return

    service = KnowledgeBaseService()
    
    for file_path in txt_files:
        print(f"Processing: {file_path}")
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            file_name = os.path.basename(file_path)
            print(f"Ingesting {file_name}...")
            result = service.upload_by_str(content, file_name)
            print(result)
        except Exception as e:
            print(f"Error processing {file_path}: {str(e)}")

if __name__ == "__main__":
    ingest_decoration_knowledge()
