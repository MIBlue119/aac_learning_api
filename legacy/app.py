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
    
    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": full_prompt},
        ]
    )
    return response.choices[0].message.content

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
    teaching_time = user_data.get('teaching_Time', '未提供')

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

def markdown_to_pdf(markdown_text):
    html = markdown.markdown(markdown_text, extensions=["tables"], output_format="html5")
    soup = BeautifulSoup(html, "html.parser", from_encoding="utf-8")

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)

    pdfmetrics.registerFont(TTFont("NotoSansTC", "NotoSansTC-Regular.ttf"))

    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="CustomStyle", fontName="NotoSansTC", fontSize=12, leading=14, encoding="utf-8"
        )
    )

    for style in styles.byName.values():
        style.fontName = "NotoSansTC"

    elements = []
    for element in soup.find_all(["p", "h1", "h2", "h3", "ul", "ol", "li", "table"]):
        if element.name in ["p", "h1", "h2", "h3"]:
            style = "Heading1" if element.name == "h1" else ("Heading2" if element.name == "h2" else "Heading3" if element.name == "h3" else "CustomStyle")
            elements.append(Paragraph(element.text, styles[style]))
        elif element.name in ["ul", "ol"]:
            for li in element.find_all("li"):
                bullet = "• " if element.name == "ul" else f"{len(elements)+1}. "
                elements.append(Paragraph(f"{bullet}{li.text}", styles["CustomStyle"]))
        elif element.name == "table":
            data = [[Paragraph(cell.text, styles["CustomStyle"]) for cell in row.find_all(["th", "td"])] for row in element.find_all("tr")]
            table = Table(data)
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, -1), "NotoSansTC"),
                ("FONTSIZE", (0, 0), (-1, -1), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
            ]))
            elements.append(table)

    doc.build(elements)
    buffer.seek(0)
    return buffer

SYSTEM_PROMPT = """
你是一位經驗豐富的特殊教育專家，擁有20年以上的教學經驗和多項特教認證。
你的任務是根據提供的<個案資料>/<學習單類型> 和<學習單內容>，生成高質量、專業的教案和學習單，格式要與提供的範例結構極為相似。

請嚴格按照以下結構和要求生成內容：

# 教案

## 教案名稱
[請根據學習單內容提供簡潔明確的教案名稱]

## 教學目標
[列出1-3個具體、可衡量的學習目標]

## 教學內容
[簡要描述本次教學的主要內容，應與教學目標直接相關，若需列點請列點]

## 教學方法
[列出2-4種將要使用的教學方法，如示範教學、遊戲教學等，每種方法包含標題和簡短解釋]

## 教學步驟
[詳細列出5-10個具體的教學步驟，包括如廁過程中的每個關鍵動作，每個步驟包含簡短標題和擴充解釋]

## 評量方式
[列出2-3種評量學生學習成效的方法，每個方式包含簡短標題和擴充解釋]

# 學習單：[主題] - [具體技能]

## 一、練習題
1. [與主題相關的具體問題或任務]
2. [另一個相關問題或任務]

## 二、活動指導
1. [具體的活動說明，如「實踐活動」]
2. [另一個活動說明，如「觀察活動」]

## 三、反思問題
1. [促進學生思考的開放式問題]
2. [另一個反思性問題]

## 四、評量題
1. [評估學習成效的具體問題]
2. [另一個評量問題]

## 五、自我評估表

| 評估項目 | 滿意(✓) | 需改進(✗) | 反思與改進方法 |
|----------|---------|-----------|----------------|
| [具體的評估項目，如「我能夠正確完成每個如廁步驟」] |         |           |                |
| [另一個評估項目] |         |           |                |
| [第三個評估項目] |         |           |                |

## 六、合作學習活動
[描述一個促進學生互動和合作的小組活動]

特別注意事項：
- 確保所有內容都嚴格對應<個案資料>中描述的學生特點和能力水平。
- 教案中的每個步驟都應該詳細且具體，特別是針對如廁這樣的生活技能。
- 學習單的每個部分都應該有明確的指示和足夠的空間讓學生填寫。
- 自我評估表應包含與學生個人目標直接相關的具體項目。
- 所有內容都應該使用正面、鼓勵性的語言。

<個案資料>:
<case_info>

<學習單內容>:
<learn_assets_contents>

請確保生成的內容完全符合特殊教育的專業標準，並與提供的範例在格式和深度上保持一致。使用適當的Markdown語法來構建內容，包括標題、列表、表格等。你的回覆應該只包含Markdown格式的教案和學習單內容，無需任何額外解釋或評論。
"""

async def process_request(api_key, board_id):
    try:
        async with aiohttp.ClientSession() as session:
            user_data_task = asyncio.create_task(get_user_study_sheet_data_async(session, api_key))
            prompt_data_task = asyncio.create_task(get_board_prompt_word_data_async(session, api_key, board_id))
            
            user_data, prompt_data = await asyncio.gather(user_data_task, prompt_data_task)

        info = parse_user_data(user_data)
        prompt = SYSTEM_PROMPT + prompt_data['promptContent']
        
        learning_asset = await generate_learning_asset_async(info, prompt_data['promptContent'], prompt=prompt)
        
        return learning_asset
    except Exception as e:
        logger.error(f"處理請求時發生錯誤: {str(e)}")
        return None

def main():
    st.title("AAC好教材 - AI學習單生成器")

    # 從URL獲取參數
    api_key = st.query_params.get("apiKey", "")
    board_id = st.query_params.get("boardId", "")

    if api_key and board_id:
        with st.spinner("正在處理您的請求..."):
            learning_asset = asyncio.run(process_request(api_key, board_id))
            
            if learning_asset:
                st.success("學習單已生成!")
                st.markdown(learning_asset)

                # 匯出選項
                st.subheader("匯出選項")
                pdf_buffer = markdown_to_pdf(learning_asset)
                st.download_button(
                    label="下載 PDF",
                    data=pdf_buffer,
                    file_name="learning_asset.pdf",
                    mime="application/pdf",
                )
            else:
                st.error("生成學習單時發生錯誤，請檢查API密鑰和版面提示詞ID是否正確。")
    else:
        st.warning("請通過AAC好教材服務來訪問此頁面，並提供必要的API密鑰和版面提示詞ID。")

if __name__ == "__main__":
    main()