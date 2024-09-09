import streamlit as st
import requests
from openai import OpenAI
import io

import io
import os

import markdown
from bs4 import BeautifulSoup
from PIL import Image
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Table, TableStyle
from streamlit import session_state as state


from loguru import logger
import json

# OpenAI client setup (假設您已經將API密鑰設置為環境變量)
client = OpenAI()

def get_user_study_sheet_data(api_key):
    url = "https://aaclearningbackend.azurewebsites.net/api/WebAAC/GetUserStudySheetData"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"GetUserStudySheetData API調用失敗,狀態碼 {response.status_code}")

def get_board_prompt_word_data(api_key, board_id):
    url = "https://aaclearningbackend.azurewebsites.net/api/WebAAC/GetBoardPromptWordData"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    # 将board_id放入请求体
    data = {"ID": board_id}
    
    # 使用GET方法，但将data作为参数传递给requests.get()
    response = requests.get(url, headers=headers, data=json.dumps(data))
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"GetBoardPromptWordData API调用失败，状态码 {response.status_code}")

def generate_learning_asset(case_info, learn_assets_contents, prompt, model="gpt-4o-mini"):
    full_prompt = prompt.replace("<case_info>", case_info)
    full_prompt = full_prompt.replace("<learn_assets_contents>", learn_assets_contents)
    logger.info(f"full_prompt:{full_prompt}")
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": full_prompt},
        ],
    )
    return response.choices[0].message.content

def markdown_to_pdf(markdown_text):
    # Convert Markdown to HTML
    html = markdown.markdown(markdown_text, extensions=["tables"], output_format="html5")
    print(html)
    # Parse HTML
    soup = BeautifulSoup(html, "html.parser", from_encoding="utf-8")

    # Create PDF
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)

    # Register fonts
    pdfmetrics.registerFont(TTFont("NotoSansTC", "NotoSansTC-Regular.ttf"))

    # Create styles
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="CustomStyle", fontName="NotoSansTC", fontSize=12, leading=14, encoding="utf-8"
        )
    )

    # Update default styles to use the Chinese font
    for style in styles.byName.values():
        style.fontName = "NotoSansTC"

    # Convert HTML elements to ReportLab elements
    elements = []
    for element in soup.find_all(["p", "h1", "h2", "h3", "ul", "ol", "li", "table"]):
        if element.name in ["p", "h1", "h2", "h3"]:
            style = (
                "Heading1"
                if element.name == "h1"
                else (
                    "Heading2"
                    if element.name == "h2"
                    else "Heading3" if element.name == "h3" else "CustomStyle"
                )
            )
            elements.append(Paragraph(element.text, styles[style]))
        elif element.name in ["ul", "ol"]:
            for li in element.find_all("li"):
                bullet = "• " if element.name == "ul" else f"{len(elements)+1}. "
                elements.append(Paragraph(f"{bullet}{li.text}", styles["CustomStyle"]))
        elif element.name == "table":
            data = []
            for row in element.find_all("tr"):
                data.append(
                    [
                        Paragraph(cell.text, styles["CustomStyle"])
                        for cell in row.find_all(["th", "td"])
                    ]
                )
            table = Table(data)
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("FONTNAME", (0, 0), (-1, -1), "NotoSansTC"),
                        ("FONTSIZE", (0, 0), (-1, -1), 12),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                        ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                        ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ]
                )
            )
            elements.append(table)

    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer

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

def main():

    
    st.title("AAC好教材 - AI學習單生成器")

    # 從URL獲取參數
    api_key = st.query_params.get("apiKey", "")
    logger.info(f"API key: {api_key}")
    board_id = st.query_params.get("boardId", "")
    logger.info(f"board_id:{board_id}")

    if api_key and board_id:
        try:
            with st.spinner("正在獲取數據..."):
                user_data = get_user_study_sheet_data(api_key)
                logger.info(f"user_data:{user_data}")
                # user_data:{'id': 1, 'name': '["王小明\u200b"]', 'gender': '["女"]', 'disability': '["視覺障礙","肢體障礙","情緒行為障礙"]', 'communication_Issues': None, 'communication_Methods': None, 'strengths': None, 'weaknesses': None, 'teaching_Time': None, 'learn_Assets_Class': None, 'learn_Assets_Contents': None, 'userAccount': 'yGJZs5kAjECY'}
                prompt_data = get_board_prompt_word_data(api_key, board_id)
                logger.info(f"prompt_data:{prompt_data}")

            st.success("成功獲取用戶數據和提示詞!")

            info = parse_user_data(user_data)

            prompt = SYSTEM_PROMPT + prompt_data['promptContent']
            with st.spinner("正在生成學習單..."):
                learning_asset = generate_learning_asset(
                    info,
                    prompt_data['promptContent'],
                    prompt=prompt
                )

            st.success("學習單已生成!")
            st.markdown(learning_asset)

            # 匯出選項
            st.subheader("導出選項")
            pdf_buffer = markdown_to_pdf(learning_asset)
            st.download_button(
                label="下載 PDF",
                data=pdf_buffer,
                file_name="learning_asset.pdf",
                mime="application/pdf",
            )

        except Exception as e:
            st.error(f"發生錯誤: {str(e)}")
    else:
        st.warning("請通過AAC好教材服務來訪問此頁面,以提供必要的API密鑰和版面提示詞ID。")

if __name__ == "__main__":
    main()