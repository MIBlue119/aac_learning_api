import asyncio
import os

import aiohttp
import streamlit as st
from loguru import logger
from openai import AsyncOpenAI

from aac_assets_generator.generator.learning_asset import LearningAssetGenerator
from aac_assets_generator.learning_asset_models import LearningAsset
from aac_assets_generator.prompts import AAC_TUTORIAL_PROMPT
from aac_assets_generator.utils import (
    get_board_prompt_word_data_async,
    get_user_study_sheet_data_async,
    parse_user_data,
)

# Add this near the top of your script, after the imports
if "learning_asset" not in st.session_state:
    st.session_state.learning_asset = None

# 設置 logger
logger.add("app.log", rotation="500 MB")

# 初始化 AsyncOpenAI 客戶端
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
learningasset_generator = LearningAssetGenerator(client=client)


async def process_request(api_key, board_id):
    try:
        async with aiohttp.ClientSession() as session:
            user_data_task = asyncio.create_task(get_user_study_sheet_data_async(session, api_key))
            prompt_data_task = asyncio.create_task(
                get_board_prompt_word_data_async(session, api_key, board_id)
            )

            user_data, prompt_data = await asyncio.gather(user_data_task, prompt_data_task)

        info = parse_user_data(user_data)
        prompt = AAC_TUTORIAL_PROMPT  # + prompt_data['promptContent']

        learning_asset = await learningasset_generator.generate_learning_asset_async(
            info, prompt_data["promptContent"], prompt=prompt
        )

        return learning_asset
    except Exception as e:
        logger.error(f"處理請求時發生錯誤: {str(e)}")
        return None


def main():
    st.set_page_config(page_title="特教學習助手 - AI個性化學習單生成器", layout="wide")
    st.title("特教學習助手 - AI個性化學習單生成器")

    # 從URL獲取參數
    api_key = st.query_params.get("apiKey", "")
    board_id = st.query_params.get("boardId", "")

    if api_key and board_id:
        if st.session_state.learning_asset is None:
            with st.spinner("正在處理您的請求..."):
                learning_asset = asyncio.run(process_request(api_key, board_id))
                st.session_state.learning_asset = learning_asset
        else:
            learning_asset = st.session_state.learning_asset

        if isinstance(learning_asset, LearningAsset):
            st.success("學習單已生成!")
            # Export options
            st.subheader("匯出選項")
            pdf_buffer = learningasset_generator.markdown_to_pdf(learning_asset)
            st.download_button(
                label="下載 PDF",
                data=pdf_buffer,
                file_name="learning_asset.pdf",
                mime="application/pdf",
            )
            st.header("教案")

            lesson_plan_data = [
                ["教案名稱", learning_asset.lesson_plan.title],
                ["教學目標", learning_asset.lesson_plan.objectives],
                [
                    "教學內容",
                    "\n".join(
                        [
                            f"{i+1}. {content}"
                            for i, content in enumerate(learning_asset.lesson_plan.content)
                        ]
                    ),
                ],
                [
                    "教學方法",
                    "\n".join(
                        [
                            f"{i+1}. {method.title}: {method.explanation}"
                            for i, method in enumerate(learning_asset.lesson_plan.teaching_methods)
                        ]
                    ),
                ],
                [
                    "教學步驟",
                    "\n".join(
                        [
                            f"{i+1}. {step.title}: {step.explanation}"
                            for i, step in enumerate(learning_asset.lesson_plan.teaching_steps)
                        ]
                    ),
                ],
                [
                    "評量方式",
                    "\n".join(
                        [
                            f"{i+1}. {method.title}: {method.explanation}"
                            for i, method in enumerate(
                                learning_asset.lesson_plan.assessment_methods
                            )
                        ]
                    ),
                ],
            ]
            for row in lesson_plan_data:
                st.subheader(row[0])
                st.write(row[1])
                st.write("---")  # Add a separator line
            # Display Worksheet
            st.header("學習單")

            st.subheader("一、練習題")
            for i, question in enumerate(learning_asset.worksheet.practice_questions, 1):
                st.write(f"{i}. {question.question}")
            st.write("---")

            st.subheader("二、活動指導")
            for i, guide in enumerate(learning_asset.worksheet.activity_guides, 1):
                st.write(f"{i}. {guide.description}")
            st.write("---")

            st.subheader("三、反思問題")
            for i, question in enumerate(learning_asset.worksheet.reflection_questions, 1):
                st.write(f"{i}. {question.question}")
            st.write("---")

            st.subheader("四、評量題")
            for i, question in enumerate(learning_asset.worksheet.assessment_questions, 1):
                st.write(f"{i}. {question.question}")
            st.write("---")

            st.subheader("五、自我評估表")
            table_header = "| 評估項目 | 滿意(✓) | 需改進(✗) | 反思與改進方法 |"
            table_separator = "|------------|---------|------------|----------------|"
            table_rows = [
                f"| {item.item} | | | |" for item in learning_asset.worksheet.self_assessment_items
            ]
            table_markdown = "\n".join([table_header, table_separator] + table_rows)
            st.markdown(table_markdown)
            st.write("---")

            st.subheader("六、合作學習活動")
            st.write(learning_asset.worksheet.collaborative_learning_activity)

        else:
            st.error("生成學習單時發生錯誤，請檢查API密鑰和版面提示詞ID是否正確。")
    else:
        st.warning("請通過AAC好教材服務來訪問此頁面，並提供必要的API密鑰和版面提示詞ID。")


if __name__ == "__main__":
    main()
