import asyncio
import os

import aiohttp
import streamlit as st
from loguru import logger
from openai import AsyncOpenAI

from aac_assets_generator.generator.learning_asset import LearningAssetGenerator
from aac_assets_generator.generator.learning_evaluate import LearningEvaluateGenerator
from aac_assets_generator.learning_asset_models import LearningAsset
from aac_assets_generator.learning_evaluation_models import EvaluationAssetTable
from aac_assets_generator.prompts import AAC_TUTORIAL_PROMPT, AAC_EVALUATION_PROMPT
from aac_assets_generator.utils import (
    get_board_prompt_word_data_async,
    get_user_study_sheet_data_async,
    parse_user_data,
    combine_pdf_buffers,
    export_assets_pdf,
    generate_combined_docx,
    export_asset_docx,
    render_streamlit_interface,
    extract_main_title
)

# Add this near the top of your script, after the imports
if "learning_asset" not in st.session_state:
    st.session_state.learning_asset = None

if "learning_evaluate" not in st.session_state:
    st.session_state.learning_evaluate = None

if "main_title" not in st.session_state:
     st.session_state.main_title = None

if "sub_title" not in st.session_state:
     st.session_state.sub_title = None

if 'pdf_buffer' not in st.session_state:
        st.session_state.pdf_buffer = None
if 'docx_buffer' not in st.session_state:
        st.session_state.docx_buffer = None
if 'rendered' not in st.session_state:
        st.session_state.rendered = False
if 'case_info' not in st.session_state:
        st.session_state.case_info = None

# 設置 logger
logger.add("app.log", rotation="500 MB")

# 初始化 AsyncOpenAI 客戶端
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
learningasset_generator = LearningAssetGenerator(client=client)
learningevaluate_generator = LearningEvaluateGenerator(client=client)


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

        learning_asset, case_info = await learningasset_generator.generate_learning_asset_async(
            info, prompt_data["promptContent"], prompt=prompt
        )

        prompt = AAC_EVALUATION_PROMPT
        learning_evaluate, case_info = await learningevaluate_generator.generate_learning_evaluate_async(
            info, prompt_data["promptContent"], prompt=prompt
        )
        main_title = extract_main_title(prompt_data['promptContent'])
        sub_title = prompt_data['promptTitle']

        return learning_asset, learning_evaluate, main_title, sub_title, case_info
    except Exception as e:
        logger.error(f"處理請求時發生錯誤: {str(e)}")
        return None, None, None, None, None, None


def main():
    st.set_page_config(page_title="特教學習助手 - AI個性化學習單生成器", layout="wide")
    st.title("特教學習助手 - AI個性化學習單生成器")

    # 從URL獲取參數
    api_key = st.query_params.get("apiKey", "")
    board_id = st.query_params.get("boardId", "")

    if api_key and board_id:
        if st.session_state.learning_asset is None and st.session_state.learning_evaluate is None and st.session_state.main_title is None and st.session_state.sub_title is None and st.session_state.case_info is None:
            with st.spinner("正在處理您的請求..."):
                learning_asset, learning_evaluate, main_title, sub_title, case_info = asyncio.run(process_request(api_key, board_id))
                st.session_state.learning_asset = learning_asset
                st.session_state.learning_evaluate = learning_evaluate
                st.session_state.main_title = main_title
                st.session_state.sub_title = sub_title
                st.session_state.case_info = case_info
        else:
            learning_asset = st.session_state.learning_asset
            learning_evaluate = st.session_state.learning_evaluate
            main_title = st.session_state.main_title
            sub_title = st.session_state.sub_title
            case_info = st.session_state.case_info
        if isinstance(st.session_state.learning_asset, LearningAsset) and isinstance(st.session_state.learning_evaluate, EvaluationAssetTable) and isinstance(st.session_state.main_title, str) and isinstance(st.session_state.sub_title, str):
            # 生成 PDF
            if st.session_state.pdf_buffer is None:
                asset_elements = learningasset_generator.markdown_to_pdf(learning_asset, main_title, sub_title, case_info)
                evaluate_elements= learningevaluate_generator.markdown_to_pdf(learning_evaluate)

                st.session_state.pdf_buffer = combine_pdf_buffers(
                    asset_elements,
                    evaluate_elements
                )

            # 生成 DOCX
            if st.session_state.docx_buffer is None:
                st.session_state.docx_buffer = generate_combined_docx(learning_asset, learning_evaluate, main_title, sub_title, case_info)


            #st.subheader("下載 PDF 版本")
            export_assets_pdf(st.session_state.pdf_buffer, main_title, sub_title)

            #st.subheader("下載 Word 版本")
            export_asset_docx(st.session_state.docx_buffer,  main_title, sub_title)
       
        if isinstance(learning_asset, LearningAsset):
            learningasset_generator.render_at_streamlit(learning_asset, case_info)
        else:
            st.error("生成學習單時發生錯誤，請檢查API密鑰和版面提示詞ID是否正確。")

        if isinstance(learning_evaluate, EvaluationAssetTable):
            learningevaluate_generator.render_at_streamlit(learning_evaluate)
        else:
            st.error("生成評估表時發生錯誤，請檢查API密鑰和版面提示詞ID是否正確。")
    else:
        st.warning("請通過AAC好教材服務來訪問此頁面，並提供必要的API密鑰和版面提示詞ID。")


if __name__ == "__main__":
    main()
