
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

md5_path = "./md5.text"

# Runtime environment
ENV = os.getenv("ENV", "development")
ALLOW_DEV_AUTH_BYPASS = os.getenv("ALLOW_DEV_AUTH_BYPASS", "false").lower() == "true"

# Upload limits
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(10 * 1024 * 1024)))

# Protocol
PROTOCOL_VERSION = os.getenv("PROTOCOL_VERSION", "1.0")

# Retention
CHAT_HISTORY_RETENTION_DAYS = int(os.getenv("CHAT_HISTORY_RETENTION_DAYS", "30"))
MEMORY_RETENTION_DAYS = int(os.getenv("MEMORY_RETENTION_DAYS", "180"))

# Storage dirs
CHAT_HISTORY_DIR = os.getenv("CHAT_HISTORY_DIR", "./chat_history")
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")


# DashScope API Key
dashscope_api_key = os.getenv("DASHSCOPE_API_KEY", "")
if dashscope_api_key:
    os.environ["DASHSCOPE_API_KEY"] = dashscope_api_key

# Chroma - 多集合配置
persist_directory = CHROMA_PERSIST_DIR
default_collection_name = "rag"  # 默认集合（向后兼容）
collection_name = default_collection_name  # 别名，供旧代码兼容

# 多集合架构配置
COLLECTIONS = {
    "decoration_general": {
        "name": "decoration_general",
        "description": "装修风格、材料、施工知识",
        "target_user": "both",
    },
    "smart_home": {
        "name": "smart_home",
        "description": "智能家居选购和配置",
        "target_user": "both",
    },
    "dongju_c_end": {
        "name": "dongju_c_end",
        "description": "补贴政策、使用流程、逛店指南",
        "target_user": "c_end",
    },
    "dongju_b_end": {
        "name": "dongju_b_end",
        "description": "入驻指南、数据产品、经营分析",
        "target_user": "b_end",
    },
    "merchant_info": {
        "name": "merchant_info",
        "description": "商家信息、品类、评价",
        "target_user": "both",
    },
}

# 用户类型到集合的映射
USER_TYPE_COLLECTIONS = {
    "c_end": ["decoration_general", "smart_home", "dongju_c_end", "merchant_info"],
    "b_end": ["decoration_general", "smart_home", "dongju_b_end", "merchant_info"],
    "both": list(COLLECTIONS.keys()),
}

# spliter
chunk_size = 1000
chunk_overlap = 100
separators = ["\n\n", "\n", ".", "!", "?", "。", "！", "？", " ", ""]
max_split_char_number = 1000        # 文本分割的阈值

#
similarity_threshold = 4            # 检索返回匹配的文档数量
search_score_threshold = 0.8        # 混合检索阈值 (L2距离)：高于此值视为不相关，将触发联网搜索


embedding_model_name = "text-embedding-v4"
chat_model_name = "qwen3-max"

session_config = {
        "configurable": {
            "session_id": "user_001",
        }
    }

# API配置
API_RATE_LIMIT = "60/minute"  # 限流配置
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# 生产环境启动校验
if ENV == "production":
    if JWT_SECRET_KEY == "your-secret-key-change-in-production":
        raise RuntimeError("生产环境必须配置 JWT_SECRET_KEY 环境变量，不能使用默认值")
    if len(JWT_SECRET_KEY) < 32:
        raise RuntimeError("生产环境 JWT_SECRET_KEY 长度不得少于 32 字符")
    if not dashscope_api_key:
        raise RuntimeError("生产环境必须配置 DASHSCOPE_API_KEY 环境变量")
