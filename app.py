import streamlit as st
import asyncio
import aiohttp
import json
import io
import os
from loguru import logger
from openai import AsyncOpenAI
import markdown
from bs4 import BeautifulSoup
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Table, TableStyle
from reportlab.platypus import PageBreak
from reportlab.lib.units import cm
from learning_asset_models import LearningAsset, LessonPlan, WorksheetSection
from PIL import Image
from io import BytesIO

# Add this near the top of your script, after the imports
if 'learning_asset' not in st.session_state:
    st.session_state.learning_asset = None

# 設置 logger
logger.add("app.log", rotation="500 MB")

# 初始化 AsyncOpenAI 客戶端
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

async def get_user_study_sheet_data_async(session, api_key):
    url = "https://aaclearningbackend.azurewebsites.net/api/WebAAC/GetUserStudySheetData"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    async with session.get(url, headers=headers) as response:
        if response.status == 200:
            return await response.json()
        else:
            raise Exception(f"GetUserStudySheetData API 調用失敗，狀態碼 {response.status}")

async def get_board_prompt_word_data_async(session, api_key, board_id):
    url = "https://aaclearningbackend.azurewebsites.net/api/WebAAC/GetBoardPromptWordData"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {"ID": board_id}
    async with session.get(url, headers=headers, data=json.dumps(data)) as response:
        if response.status == 200:
            return await response.json()
        else:
            raise Exception(f"GetBoardPromptWordData API 調用失敗，狀態碼 {response.status}")

async def generate_learning_asset_async(case_info, learn_assets_contents, prompt, model="gpt-4o-mini"):
    full_prompt = prompt.replace("<case_info>", case_info)
    full_prompt = full_prompt.replace("<learn_assets_contents>", learn_assets_contents)
    logger.info(f"full_prompt:{full_prompt}")
    
    try:
        response = await client.beta.chat.completions.parse(
            model=model,
            messages=[
                {"role": "system", "content": full_prompt},
        ],
        response_format=LearningAsset,
        )
        logger.info(f"response:{response}")
        return response.choices[0].message.parsed
    except Exception as e:
        logger.error(f"生成學習單時發生錯誤: {str(e)}")
        return None

def parse_user_data(user_data):
    def parse_json_field(field):
        if field:
            try:
                return ', '.join(json.loads(field))
            except json.JSONDecodeError:
                return field
        return '未提供'

    name = parse_json_field(user_data.get('name', '未提供'))
    gender = parse_json_field(user_data.get('gender', '未提供'))
    disability = parse_json_field(user_data.get('disability', '未提供'))
    communication_issues = parse_json_field(user_data.get('communication_Issues', '未提供'))
    communication_methods = parse_json_field(user_data.get('communication_Methods', '未提供'))
    strengths = parse_json_field(user_data.get('strengths', '未提供'))
    weaknesses = parse_json_field(user_data.get('weaknesses', '未提供'))
    teaching_time = parse_json_field(user_data.get('teaching_Time', '未提供'))

    case_info = f"""
    姓名: {name}
    性別: {gender}
    障礙類別: {disability}
    溝通問題: {communication_issues}
    溝通方式: {communication_methods}
    優勢能力: {strengths}
    弱勢能力: {weaknesses}
    預計教學時間: {teaching_time} 分鐘
    """

    return case_info

def markdown_to_pdf(learning_asset: LearningAsset):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)

    pdfmetrics.registerFont(TTFont("NotoSansTC", "NotoSansTC-Regular.ttf"))

    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="CustomStyle", 
            fontName="NotoSansTC", 
            fontSize=12, 
            leading=14, 
            encoding="utf-8",
            leftIndent=20  # Add this line to create indentation
        )
    )

    for style in styles.byName.values():
        style.fontName = "NotoSansTC"

    elements = []

    # # Lesson Plan
    # elements.append(Paragraph("教案", styles["Heading1"]))
    # elements.append(Paragraph(f"教案名稱: {learning_asset.lesson_plan.title}", styles["Heading2"]))
    
    # elements.append(Paragraph("教學目標", styles["Heading2"]))
    # for objective in learning_asset.lesson_plan.objectives:
    #     elements.append(Paragraph(f"• {objective}", styles["CustomStyle"]))
    
    # elements.append(Paragraph("教學內容", styles["Heading2"]))
    # elements.append(Paragraph(learning_asset.lesson_plan.content, styles["CustomStyle"]))
    
    # elements.append(Paragraph("教學方法", styles["Heading2"]))
    # for method in learning_asset.lesson_plan.teaching_methods:
    #     elements.append(Paragraph(f"{method.title}: {method.explanation}", styles["CustomStyle"]))
    
    # elements.append(Paragraph("教學步驟", styles["Heading2"]))
    # for step in learning_asset.lesson_plan.teaching_steps:
    #     elements.append(Paragraph(f"{step.title}: {step.explanation}", styles["CustomStyle"]))
    
    # elements.append(Paragraph("評量方式", styles["Heading2"]))
    # for method in learning_asset.lesson_plan.assessment_methods:
    #     elements.append(Paragraph(f"{method.title}: {method.explanation}", styles["CustomStyle"]))
    
    # Lesson Plan Title
    elements.append(Paragraph("教案", styles["Title"]))

    # Lesson Plan Table
    lesson_plan_data = [
        ["教案名稱", Paragraph(learning_asset.lesson_plan.title, styles["CustomStyle"])],
        ["教學目標", Paragraph(" ".join(learning_asset.lesson_plan.objectives), styles["CustomStyle"])],
        #["教學內容", Paragraph(learning_asset.lesson_plan.content, styles["CustomStyle"])],
        ["教學內容", Paragraph("<br/><br/>".join(f"{i+1}. {content}" for i, content in enumerate(learning_asset.lesson_plan.content)), styles["CustomStyle"])],
        ["教學方法", Paragraph("<br/><br/>".join([f"{i+1}. {method.title}: {method.explanation}" for i, method in enumerate(learning_asset.lesson_plan.teaching_methods)]), styles["CustomStyle"])],
        ["教學步驟", Paragraph("<br/><br/>".join([f"{i+1}. {step.title}: {step.explanation}" for i, step in enumerate(learning_asset.lesson_plan.teaching_steps)]), styles["CustomStyle"])],
        ["評量方式", Paragraph("<br/><br/>".join([f"{i+1}. {method.title}: {method.explanation}" for i, method in enumerate(learning_asset.lesson_plan.assessment_methods)]), styles["CustomStyle"])]
    ]

    lesson_plan_table = Table(lesson_plan_data, colWidths=[3*cm, 15*cm])
    lesson_plan_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'NotoSansTC'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(lesson_plan_table)

    # Add page break
    elements.append(PageBreak())
    # Worksheet
    elements.append(Paragraph("學習單", styles["Heading1"]))
    
    elements.append(Paragraph("一、練習題", styles["Heading2"]))
    for count, question in enumerate(learning_asset.worksheet.practice_questions):
        elements.append(Paragraph(f"{count+1}. {question.question}", styles["CustomStyle"]))
    
    elements.append(Paragraph("二、活動指導", styles["Heading2"]))
    for count, guide in enumerate(learning_asset.worksheet.activity_guides):
        elements.append(Paragraph(f"{count+1}. {guide.description}", styles["CustomStyle"]))
    
    elements.append(Paragraph("三、反思問題", styles["Heading2"]))
    for count, question in enumerate(learning_asset.worksheet.reflection_questions):
        elements.append(Paragraph(f"{count+1}. {question.question}", styles["CustomStyle"]))
    
    elements.append(Paragraph("四、評量題", styles["Heading2"]))
    for count, question in enumerate(learning_asset.worksheet.assessment_questions):
        elements.append(Paragraph(f"{count+1}. {question.question}", styles["CustomStyle"]))
    
    # Self-assessment table
    elements.append(Paragraph("五、自我評估表", styles["Heading2"]))
    assessment_data = [["評估項目", "滿意(V)", "需改進(X)", "反思與改進方法"]]
    for item in learning_asset.worksheet.self_assessment_items:
        assessment_data.append([item.item, "", "", ""])
    assessment_table = Table(assessment_data, colWidths=[8*cm, 3*cm, 3*cm, 4*cm])
    assessment_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), 'NotoSansTC'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(assessment_table)

    # Collaborative learning activity
    
    elements.append(Paragraph("六、合作學習活動", styles["Heading2"]))
    elements.append(Paragraph(learning_asset.worksheet.collaborative_learning_activity, styles["CustomStyle"]))

    doc.build(elements)
    buffer.seek(0)
    return buffer

SYSTEM_PROMPT = """
你是一位經驗豐富的特殊教育專家，擁有20年以上的教學經驗和多項特教認證。
你的任務是根據提供的<個案資料>/<學習單類型> 和<學習單內容>，生成高質量、專業的教案和學習單，格式要與提供的結構嚴格一致。

在開始之前，請仔細分析<個案資料>中的以下要點：

1. 學生的障礙類別和具體表現
2. 學生的溝通問題和溝通方式
3. 學生的優勢能力和弱勢能力
4. 預計的教學時間

根據這些資訊，調整你的教案和學習單，確保它們：

1. 充分利用學生的優勢能力
2. 針對性地改善學生的弱勢能力
3. 採用適合學生溝通方式的教學策略
4. 考慮到學生的注意力持續時間和學習節奏

請嚴格按照以下結構和要求生成內容：

# 教案

- 教案名稱: [請根據學習單內容提供簡潔明確的教案名稱]
- 教學目標: [列出1個具體、可衡量的學習目標]
- 教學內容: [簡要列舉幾個描述本次教學的主要內容，應與教學目標直接相關]
- 教學方法: [列出2-4種將要使用的教學方法，每種方法包含標題和簡短解釋]
- 教學步驟: [詳細列出5-10個具體的教學步驟，包括如廁過程中的每個關鍵動作，每個步驟包含簡短標題和擴充解釋]
- 評量方式: [列出2-3種評量學生學習成效的方法，每個方式包含簡短標題和擴充解釋]

# 學習單

- 練習題: [列出2-3個與主題相關的具體問題或任務]
- 活動指導: [提供2-3個具體的活動說明，如「實踐活動」或「觀察活動」]
- 反思問題: [列出2-3個促進學生思考的開放式問題]
- 評量題: [提供2-3個評估學習成效的具體問題]
- 自我評估項目: [列出3-5個具體的評估項目，如「我能夠正確完成每個如廁步驟」]
- 合作學習活動: [描述一個促進學生互動和合作的小組活動]

特別注意事項：
- 確保所有內容都嚴格對應<個案資料>中描述的學生特點和能力水平。
- 根據學生的障礙類別，調整教學策略和材料的呈現方式。
- 考慮學生的優勢能力，設計能夠展現其長處的活動。
- 針對學生的弱勢能力，提供適當的支持和漸進式的挑戰。
- 確保教學步驟和活動設計符合預計的教學時間。
- 使用學生熟悉的溝通方式來呈現指示和問題。
- 所有內容都應該使用正面、鼓勵性的語言，增強學生的自信心。

<個案資料>:
<case_info>

<學習單內容>:
<learn_assets_contents>

請確保生成的內容完全符合特殊教育的專業標準，高度個人化，並與提供的結構嚴格一致。你的回覆應該只包含教案和學習單的結構化內容，無需任何額外解釋或評論。
"""

async def process_request(api_key, board_id):
    try:
        async with aiohttp.ClientSession() as session:
            user_data_task = asyncio.create_task(get_user_study_sheet_data_async(session, api_key))
            prompt_data_task = asyncio.create_task(get_board_prompt_word_data_async(session, api_key, board_id))
            
            user_data, prompt_data = await asyncio.gather(user_data_task, prompt_data_task)

        info = parse_user_data(user_data)
        prompt = SYSTEM_PROMPT #+ prompt_data['promptContent']
        
        learning_asset = await generate_learning_asset_async(info, prompt_data['promptContent'], prompt=prompt)
        
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
            pdf_buffer = markdown_to_pdf(learning_asset)
            st.download_button(
                label="下載 PDF",
                data=pdf_buffer,
                file_name="learning_asset.pdf",
                mime="application/pdf",
            )
            # Export as JSON
            # json_str = learning_asset.json(ensure_ascii=False, indent=2)
            # json_bytes = json_str.encode('utf-8')
            # st.download_button(
            #     label="下載 JSON",
            #     data=BytesIO(json_bytes),
            #     file_name="learning_asset.json",
            #     mime="application/json",
            # )
            # Display Lesson Plan
            st.header("教案")
            
            lesson_plan_data = [
                ["教案名稱", learning_asset.lesson_plan.title],
                ["教學目標", learning_asset.lesson_plan.objectives],
                ["教學內容", "\n".join([f"{i+1}. {content}" for i, content in enumerate(learning_asset.lesson_plan.content)])],
                ["教學方法", "\n".join([f"{i+1}. {method.title}: {method.explanation}" for i, method in enumerate(learning_asset.lesson_plan.teaching_methods)])],
                ["教學步驟", "\n".join([f"{i+1}. {step.title}: {step.explanation}" for i, step in enumerate(learning_asset.lesson_plan.teaching_steps)])],
                ["評量方式", "\n".join([f"{i+1}. {method.title}: {method.explanation}" for i, method in enumerate(learning_asset.lesson_plan.assessment_methods)])]
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
            table_rows = [f"| {item.item} | | | |" for item in learning_asset.worksheet.self_assessment_items]
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