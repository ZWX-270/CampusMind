import gradio as gr
from main import CampusMind
import json
import os
from datetime import datetime
import logging
import requests
from PIL import Image
import io
import base64
import time
import re

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 初始化CampusMind
logger.info("============================================================")
logger.info("🚀 正在启动 CampusMind Web 界面...")
logger.info("============================================================")

campusmind = CampusMind()

# 自定义CSS样式
custom_css = """
#chatbot {
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    overflow-y: auto;
}

.message {
    padding: 12px 16px;
    border-radius: 8px;
    margin: 8px 0;
    max-width: 80%;
}

.user-message {
    background-color: #e3f2fd;
    align-self: flex-end;
    margin-left: auto;
}

.assistant-message {
    background-color: #f5f5f5;
    align-self: flex-start;
}

.system-message {
    background-color: #fff3e0;
    align-self: center;
    text-align: center;
    font-style: italic;
}

.code-block {
    background-color: #f8f9fa;
    border-left: 4px solid #2196f3;
    padding: 12px;
    font-family: 'Courier New', monospace;
    border-radius: 4px;
    overflow-x: auto;
    white-space: pre-wrap;
    margin: 8px 0;
}

.status-indicator {
    display: flex;
    align-items: center;
    padding: 8px 12px;
    background-color: #f5f5f5;
    border-radius: 4px;
    margin: 8px 0;
    font-size: 14px;
}

.status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    margin-right: 8px;
}

.status-active {
    background-color: #4caf50;
    animation: pulse 1.5s infinite;
}

.status-inactive {
    background-color: #9e9e9e;
}

@keyframes pulse {
    0% { opacity: 1; }
    50% { opacity: 0.5; }
    100% { opacity: 1; }
}

.tab-content {
    padding: 20px;
}

.input-container {
    margin-top: 20px;
}

.upload-section {
    border: 2px dashed #e0e0e0;
    border-radius: 8px;
    padding: 20px;
    text-align: center;
    margin-bottom: 20px;
    transition: border-color 0.3s;
}

.upload-section:hover {
    border-color: #2196f3;
}

.upload-hint {
    color: #666;
    font-size: 12px;
    margin-top: 8px;
}

.progress-container {
    margin: 20px 0;
}

.progress-text {
    font-size: 12px;
    color: #666;
    margin-top: 4px;
}

.agent-selection {
    display: flex;
    gap: 10px;
    margin-bottom: 20px;
    flex-wrap: wrap;
}

.agent-btn {
    flex: 1;
    min-width: 120px;
    padding: 12px 20px;
    border: 2px solid #e0e0e0;
    border-radius: 8px;
    background: white;
    cursor: pointer;
    transition: all 0.3s;
    font-weight: 500;
    text-align: center;
}

.agent-btn:hover {
    border-color: #2196f3;
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(33, 150, 243, 0.1);
}

.agent-btn.selected {
    border-color: #2196f3;
    background-color: #e3f2fd;
    color: #2196f3;
}

.agent-icon {
    font-size: 20px;
    margin-bottom: 8px;
}

.agent-description {
    font-size: 12px;
    color: #666;
    margin-top: 4px;
}

.typing-indicator {
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 12px 16px;
    background-color: #f5f5f5;
    border-radius: 8px;
    margin: 8px 0;
    max-width: 60px;
}

.typing-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background-color: #9e9e9e;
    animation: typing 1.4s infinite;
}

.typing-dot:nth-child(2) { animation-delay: 0.2s; }
.typing-dot:nth-child(3) { animation-delay: 0.4s; }

@keyframes typing {
    0%, 60%, 100% { transform: translateY(0); }
    30% { transform: translateY(-8px); }
}

.quick-actions {
    display: flex;
    gap: 8px;
    margin: 12px 0;
    flex-wrap: wrap;
}

.quick-action-btn {
    padding: 6px 12px;
    border: 1px solid #e0e0e0;
    border-radius: 16px;
    background: white;
    cursor: pointer;
    transition: all 0.2s;
    font-size: 12px;
    color: #666;
}

.quick-action-btn:hover {
    background-color: #f5f5f5;
    border-color: #2196f3;
    color: #2196f3;
}
"""

# 初始消息
initial_messages = [
    {"role": "assistant", "content": "👋 你好！我是校园智能助手CampusMind，很高兴为你服务！"},
    {"role": "assistant", "content": "我可以帮你解答以下问题："},
    {"role": "assistant", "content": "📚 **学术相关** - 课程安排、选课建议、学习资源等"},
    {"role": "assistant", "content": "🎓 **教务相关** - 政策解读、申请流程、毕业要求等"},
    {"role": "assistant", "content": "🏫 **生活服务** - 住宿、餐饮、社团活动、校园设施等"},
    {"role": "assistant", "content": "💡 **质量评估** - 课程评价、教学质量、学习建议等"},
    {"role": "assistant", "content": "请选择下方的智能体类型，然后开始咨询吧！"}
]

# 快速回复选项
quick_replies = [
    "最近的考试安排是什么？",
    "如何申请转专业？",
    "图书馆开放时间？",
    "有哪些热门社团？",
    "选课有什么建议？"
]

# 定义智能体类型
AGENT_TYPES = [
    {"id": "academic", "name": "📚 学术助手", "description": "解答课程、学习相关问题"},
    {"id": "administrative", "name": "🎓 教务助手", "description": "解答政策、申请相关问题"},
    {"id": "life", "name": "🏫 生活助手", "description": "解答生活、服务相关问题"},
    {"id": "quality", "name": "💡 质量助手", "description": "解答评价、建议相关问题"}
]


def create_interface():
    """创建Gradio界面"""

    with gr.Blocks() as demo:
        # 标题
        gr.Markdown("# 🎓 CampusMind - 校园智能助手")
        gr.Markdown("### 🤖 基于RAG技术的多智能体问答系统")

        # 智能体选择区域
        agent_buttons = []
        with gr.Row() as agent_row:
            for agent in AGENT_TYPES:
                with gr.Column(min_width=120):
                    btn = gr.Button(
                        value=agent["name"],
                        variant="secondary",
                        elem_classes="agent-btn"
                    )
                    gr.Markdown(f"<div class='agent-description'>{agent['description']}</div>",
                                elem_classes="agent-description")
                    agent_buttons.append(btn)

        # 聊天区域
        chatbot = gr.Chatbot(
            value=initial_messages,
            elem_id="chatbot",
            height=600
        )

        # 快速回复区域
        quick_action_buttons = []
        with gr.Row():
            gr.Markdown("**快速提问：**", elem_classes="quick-actions-label")
            with gr.Row(elem_classes="quick-actions") as quick_action_group:
                for reply in quick_replies:
                    quick_btn = gr.Button(
                        reply,
                        size="sm",
                        variant="secondary",
                        elem_classes="quick-action-btn"
                    )
                    quick_action_buttons.append(quick_btn)

        # 输入区域
        with gr.Row():
            with gr.Column(scale=9):
                msg = gr.Textbox(
                    placeholder="请输入您的问题... (支持中英文)",
                    show_label=False,
                    container=False
                )
            with gr.Column(scale=1):
                submit_btn = gr.Button("发送", variant="primary")
                clear_btn = gr.Button("清空", variant="secondary")

        # 文件上传区域
        with gr.Accordion("📁 上传文档添加到知识库", open=False):
            with gr.Row():
                file_input = gr.File(
                    label="上传文档",
                    file_types=[".txt", ".pdf", ".docx", ".md"],
                    file_count="multiple"
                )
            with gr.Row():
                upload_btn = gr.Button("上传并处理", variant="primary")
                process_status = gr.Markdown("")

        # 知识库管理区域
        with gr.Accordion("🔧 知识库管理", open=False):
            with gr.Row():
                refresh_btn = gr.Button("🔄 刷新知识库")
                clear_kb_btn = gr.Button("🗑️ 清空知识库", variant="stop")
            with gr.Row():
                kb_status = gr.Markdown("")

        # 系统信息区域
        with gr.Accordion("ℹ️ 系统信息", open=False):
            with gr.Row():
                with gr.Column():
                    gr.Markdown(f"**模型信息：**")
                    # 使用固定的模型名称，避免访问不存在的属性
                    gr.Markdown(f"- 嵌入模型: sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
                    # 修改这里：通过方法获取文档数量，而不是直接访问属性
                    try:
                        document_count = campusmind.get_knowledge_base_status()['document_count']
                        gr.Markdown(f"- 知识库文档数: {document_count}")
                    except:
                        gr.Markdown(f"- 知识库文档数: 正在加载中...")
                with gr.Column():
                    gr.Markdown(f"**系统状态：**")
                    gr.Markdown(f"- 智能体数量: 4")
                    gr.Markdown(f"- 知识库状态: 已加载")
                    gr.Markdown(f"- 最后更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # 历史记录变量
        current_agent = gr.State("academic")
        conversation_history = gr.State(initial_messages.copy())

        def select_agent(agent_id, history):
            """选择智能体"""
            agent_info = next(a for a in AGENT_TYPES if a["id"] == agent_id)
            new_message = {"role": "assistant", "content": f"✅ 已切换到 **{agent_info['name']}** 模式"}
            history.append(new_message)
            return agent_id, history, history

        def respond(message, agent_id, history):
            """处理用户消息并返回响应"""
            if not message.strip():
                return "", history, history

            # 添加用户消息
            user_msg = {"role": "user", "content": message}
            history.append(user_msg)

            # 根据智能体类型选择回答函数
            if agent_id == "academic":
                response = campusmind.academic_agent.ask(message)
            elif agent_id == "administrative":
                response = campusmind.administrative_agent.ask(message)
            elif agent_id == "life":
                response = campusmind.life_agent.ask(message)
            elif agent_id == "quality":
                response = campusmind.quality_agent.ask(message)
            else:
                response = campusmind.academic_agent.ask(message)

            # 添加助手响应
            assistant_msg = {"role": "assistant", "content": response}
            history.append(assistant_msg)

            return "", history, history

        def clear_chat():
            """清空聊天历史"""
            return initial_messages.copy(), initial_messages.copy()

        def upload_files(files, history):
            """处理上传的文件"""
            if not files:
                return "请先选择文件", history

            try:
                file_paths = [f.name for f in files]
                result = campusmind.add_documents(file_paths)

                new_message = {
                    "role": "assistant",
                    "content": f"✅ 已成功处理 {len(files)} 个文件，添加到知识库！\n\n**处理结果：**\n{result}"
                }
                history.append(new_message)

                return f"✅ 文件处理完成！新增文档已添加到知识库。", history
            except Exception as e:
                error_msg = f"❌ 文件处理失败：{str(e)}"
                new_message = {"role": "assistant", "content": error_msg}
                history.append(new_message)
                return error_msg, history

        def refresh_knowledge_base():
            """刷新知识库状态"""
            status = campusmind.get_knowledge_base_status()
            return f"**知识库状态**\n- 文档数量: {status['document_count']}\n- 集合名称: {status['collection_name']}\n- 存储路径: {status['persist_directory']}"

        def clear_knowledge_base(history):
            """清空知识库"""
            try:
                campusmind.clear_knowledge_base()
                new_message = {
                    "role": "assistant",
                    "content": "✅ 知识库已清空！所有文档已被移除。"
                }
                history.append(new_message)
                return "✅ 知识库已清空！", history
            except Exception as e:
                error_msg = f"❌ 清空知识库失败：{str(e)}"
                new_message = {"role": "assistant", "content": error_msg}
                history.append(new_message)
                return error_msg, history

        def quick_respond(reply_text, agent_id, history):
            """快速回复处理"""
            return respond(reply_text, agent_id, history)

        # 绑定事件 - 修复这里的代码
        for i, (btn, agent) in enumerate(zip(agent_buttons, AGENT_TYPES)):
            btn.click(
                fn=lambda a=agent["id"], h=conversation_history: select_agent(a, h),
                inputs=[],
                outputs=[current_agent, conversation_history, chatbot]
            )

        # 绑定消息发送
        msg.submit(
            fn=respond,
            inputs=[msg, current_agent, conversation_history],
            outputs=[msg, conversation_history, chatbot]
        )
        submit_btn.click(
            fn=respond,
            inputs=[msg, current_agent, conversation_history],
            outputs=[msg, conversation_history, chatbot]
        )

        # 绑定快速回复按钮
        for i, quick_btn in enumerate(quick_action_buttons):
            quick_btn.click(
                fn=lambda rt=quick_replies[i], ca=current_agent, ch=conversation_history:
                quick_respond(rt, ca.value, ch) if hasattr(ca, 'value') else quick_respond(rt, "academic", ch),
                inputs=[],
                outputs=[msg, conversation_history, chatbot]
            )

        # 绑定其他按钮
        clear_btn.click(
            fn=clear_chat,
            inputs=[],
            outputs=[conversation_history, chatbot]
        )

        upload_btn.click(
            fn=upload_files,
            inputs=[file_input, conversation_history],
            outputs=[process_status, conversation_history]
        )

        refresh_btn.click(
            fn=refresh_knowledge_base,
            inputs=[],
            outputs=[kb_status]
        )

        clear_kb_btn.click(
            fn=clear_knowledge_base,
            inputs=[conversation_history],
            outputs=[kb_status, conversation_history]
        )

    return demo


def main():
    """主函数"""
    try:
        # 创建界面
        demo = create_interface()

        # 启动服务
        logger.info("🌐 正在启动Web服务器...")
        logger.info("📱 请在浏览器中打开: http://localhost:7860")
        logger.info("============================================================")

        demo.launch(
            server_name="0.0.0.0",
            server_port=7860,
            share=False,
            theme=gr.themes.Soft(),
            css=custom_css
        )

    except Exception as e:
        logger.error(f"启动失败: {e}")
        raise


if __name__ == "__main__":
    main()