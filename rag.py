import os
import datetime
# Load env for DashScope
from dotenv import load_dotenv
load_dotenv()

from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser

from langchain_core.runnables import RunnablePassthrough, RunnableWithMessageHistory, RunnableLambda
from file_history_store import get_history
from vector_stores import VectorStoreService
from langchain_community.embeddings import DashScopeEmbeddings
import config_data as config
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_community.chat_models.tongyi import ChatTongyi
from langchain_community.tools import DuckDuckGoSearchRun


def print_prompt(prompt):
    print("="*20)

    print(prompt.to_string())
    print("="*20)

    return prompt


class RagService(object):
    def __init__(self):
        # Ensure env var is set from config if not already
        if not os.environ.get("DASHSCOPE_API_KEY") and config.dashscope_api_key:
            os.environ["DASHSCOPE_API_KEY"] = config.dashscope_api_key

        self.vector_service = VectorStoreService(
            embedding=DashScopeEmbeddings(model=config.embedding_model_name)
        )


        self.prompt_template = ChatPromptTemplate.from_messages(
            [
                ("system", "你是一个专业的装修顾问。请基于以下参考资料回答用户的问题。\n"
                 "当前时间: {current_time}\n"
                 "参考资料包含本地知识库和互联网搜索结果。\n"
                 "如果参考资料中有相关信息，请依据资料回答；如果没有，请说明无法回答。\n"
                 "参考资料:{context}。"),
                ("system", "并且我提供用户的对话历史记录，如下："),
                MessagesPlaceholder("history"),
                ("user", "请回答用户提问：{input}")
            ]
        )

        self.chat_model = ChatTongyi(model=config.chat_model_name)
        self.search_tool = DuckDuckGoSearchRun()
        
        # UI Control Flags
        self.enable_search = True
        self.show_thinking = True

        self.chain = self.__get_chain()

    def __hybrid_retriever(self, query: str) -> list[Document]:
        """混合检索策略：
        1. 先检索本地向量数据库
        2. 检查匹配分数 (L2距离)
        3. 如果所有文档的分数都高于阈值(search_score_threshold)，则触发联网搜索
        4. 否则仅使用本地文档
        """
        logs = []
        logs.append(f"正在检索: {query}")
        print(f"正在检索: {query}")
        
        # 1. 本地检索 (带分数)
        # similarity_search_with_score 返回 List[(Document, score)]
        # Chroma L2 距离：越小越相关
        local_results = self.vector_service.vector_store.similarity_search_with_score(
            query, 
            k=config.similarity_threshold
        )
        
        relevant_docs = []
        best_score = float('inf')
        
        for doc, score in local_results:
            best_score = min(best_score, score)
            if score <= config.search_score_threshold:
                relevant_docs.append(doc)
                
        log_msg = f"本地检索结果: {len(relevant_docs)} 个相关文档 (最佳分数: {best_score:.4f}, 阈值: {config.search_score_threshold})"
        logs.append(log_msg)
        print(log_msg)

        # 2. 判断是否需要联网
        # 如果没有相关文档，或者最佳分数都太差
        if not relevant_docs:
            if self.enable_search:
                logs.append("本地知识库无相关内容，触发联网搜索...")
                print("本地知识库无相关内容，触发联网搜索...")
                try:
                    search_result = self.search_tool.invoke(query)
                    logs.append("联网搜索完成")
                    print("联网搜索完成")
                    relevant_docs = [Document(page_content=f"【联网搜索结果】\n{search_result}", metadata={"source": "internet"})]
                except Exception as e:
                    logs.append(f"联网搜索失败: {e}")
                    print(f"联网搜索失败: {e}")
                    relevant_docs = [Document(page_content="无法连接到互联网获取更多信息。", metadata={"source": "error"})]
            else:
                logs.append("本地无相关内容，且联网搜索已禁用。")
                print("本地无相关内容，且联网搜索已禁用。")
                relevant_docs = [Document(page_content="知识库中未找到相关信息，且未启用联网搜索。", metadata={"source": "none"})]
        
        # 将思考过程（logs）附加到第一个文档的元数据中，以便后续步骤获取
        if relevant_docs:
            if "thinking_log" not in relevant_docs[0].metadata:
                relevant_docs[0].metadata["thinking_log"] = []
            relevant_docs[0].metadata["thinking_log"].extend(logs)
        else:
            # 极端情况：没有任何文档，创建一个空文档携带日志
            relevant_docs = [Document(page_content="无相关信息", metadata={"thinking_log": logs, "source": "none"})]

        return relevant_docs

    def __get_chain(self):
        """获取最终的执行链"""
        
        # 使用自定义的混合检索器
        retriever = RunnableLambda(self.__hybrid_retriever)

        def format_document(docs: list[Document]):
            if not docs:
                return "无相关参考资料"

            formatted_str = ""
            for doc in docs:
                source = doc.metadata.get("source", "local")
                formatted_str += f"[{source}] 文档片段：{doc.page_content}\n\n"

            return formatted_str

        def format_for_retriever(value: dict) -> str:
            return value["input"]

        def format_for_prompt_template(value):
            # {input, context, history}
            new_value = {}
            new_value["input"] = value["input"]["input"]
            new_value["context"] = value["context"]
            new_value["history"] = value["input"]["history"]
            new_value["current_time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            return new_value

        # 生成链 (Answer Generation)
        gen_chain = (
            RunnableLambda(format_for_prompt_template) 
            | self.prompt_template 
            | print_prompt 
            | self.chat_model 
            | StrOutputParser()
        )

        # 主链：同时返回检索到的文档（包含思考过程）和生成的答案
        chain = (
            {
                "input": RunnablePassthrough(),
                "retrieved_docs": RunnableLambda(format_for_retriever) | retriever,
            }
            | RunnablePassthrough.assign(context=lambda x: format_document(x["retrieved_docs"]))
            | RunnablePassthrough.assign(answer=gen_chain)
        )

        conversation_chain = RunnableWithMessageHistory(
            chain,
            get_history,
            input_messages_key="input",
            history_messages_key="history",
            output_messages_key="answer", # 指明历史记录中保存的是 answer 字段
        )

        return conversation_chain


if __name__ == '__main__':
    # session id 配置
    session_config = {
        "configurable": {
            "session_id": "user_001",
        }
    }

    res = RagService().chain.invoke({"input": "针织毛衣如何保养？"}, session_config)
    print(res)

