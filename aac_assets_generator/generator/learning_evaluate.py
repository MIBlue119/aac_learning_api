import io

from loguru import logger
from openai import AsyncOpenAI
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Table, TableStyle

from aac_assets_generator.learning_evaluation_models import EvaluationAssetTable
import streamlit as st

class LearningEvaluateGenerator:
    """生成學習單/教案"""

    def __init__(self, client):
        self.client = client

    async def generate_learning_evaluate_async(
        self, case_info, learn_assets_contents, prompt, model="o3"
    ):
        logger.info(f"use model:{model}")
        full_prompt = prompt.replace("<case_info>", case_info)
        full_prompt = full_prompt.replace("<learn_assets_contents>", learn_assets_contents)
        logger.info(f"full_prompt:{full_prompt}")

        try:
            response = await self.client.beta.chat.completions.parse(
                model=model,
                messages=[
                    {"role": "system", "content": full_prompt},
                ],
                response_format=EvaluationAssetTable,
            )
            logger.info(f"response:{response}")
            return response.choices[0].message.parsed
        except Exception as e:
            logger.error(f"生成學習單時發生錯誤: {str(e)}")
            return None
        
    def markdown_to_pdf(self,learning_evaluate: EvaluationAssetTable):
        pdfmetrics.registerFont(TTFont("NotoSansTC", "NotoSansTC-Regular.ttf"))
        styles = getSampleStyleSheet()
        styles.add(
            ParagraphStyle(
                name="CustomStyle",
                fontName="NotoSansTC",
                fontSize=12,
                leading=14,
                encoding="utf-8",
                leftIndent=20,  # Add this line to create indentation
            )
        )
        for style in styles.byName.values():
            style.fontName = "NotoSansTC"
        elements = []
        # Lesson evaluate Title
        elements.append(Paragraph("評估表", styles["Title"]))
        elements.append(Paragraph(f"{learning_evaluate.evaluation_asset_title}", styles["Heading1"]))


        # Define a paragraph style for wrapping text
        wrap_style = ParagraphStyle(
            name='WrappedStyle',
            fontName='NotoSansTC',
            fontSize=10,
            leading=12,
            wordWrap='CJK'
        )
        
        # Lesson evaluate Table
        lesson_evaluate_data = [
            [
                Paragraph("評量項目", wrap_style),
                Paragraph("評量指標", wrap_style),
                Paragraph("優良（4分）", wrap_style),
                Paragraph("良好（3分）", wrap_style),
                Paragraph("尚可（2分）", wrap_style),
                Paragraph("待加強（1分）", wrap_style)
            ]
        ]
        
        for item in learning_evaluate.evaluation_items:
            lesson_evaluate_data.append([
                Paragraph(f"{item.evaluation_item_title}", wrap_style),
                Paragraph(f"{item.evaluation_metric}", wrap_style),
                Paragraph(f"{item.score_descriptions.excellent_with_score_4}", wrap_style),
                Paragraph(f"{item.score_descriptions.good_with_score_3}", wrap_style),
                Paragraph(f"{item.score_descriptions.fair_with_score_2}", wrap_style),
                Paragraph(f"{item.score_descriptions.needs_improvement_with_score_1}", wrap_style)
            ])
        
        lesson_evaluate_table = Table(lesson_evaluate_data, colWidths=[3 * cm, 3 * cm, 3 * cm, 3 * cm, 3 * cm, 3 * cm])
        lesson_evaluate_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
                    ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("FONTNAME", (0, 0), (-1, -1), "NotoSansTC"),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("LEFTPADDING", (0, 0), (-1, -1), 3),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ]
            )
        )        
        elements.append(lesson_evaluate_table)
        elements.append(Paragraph("評分標準", styles["Heading1"]))

        number_of_evaluation_items = len(learning_evaluate.evaluation_items)
        
        elements.append(Paragraph(f"- 優良: {3*(number_of_evaluation_items-1)}-{4*number_of_evaluation_items} 分,  表示學生能充分掌握技巧並理解其重要性。", styles["CustomStyle"]))
        elements.append(Paragraph(f"- 良好: {2*(number_of_evaluation_items)}-{3*(number_of_evaluation_items-1)} 分,  表示學生能較好地完成步驟，但仍有待改進的部分。", styles["CustomStyle"]))
        elements.append(Paragraph(f"- 尚可: {1*(number_of_evaluation_items)}-{2*(number_of_evaluation_items-1)} 分,  表示學生能完成部分步驟，但正確性和時間效率需加強。", styles["CustomStyle"]))
        elements.append(Paragraph(f"- 待加強: {1*(number_of_evaluation_items-1)} 分,  表示學生需更多練習和輔助以掌握技巧。", styles["CustomStyle"]))
        return elements

    def render_at_streamlit(self, learning_evaluate):
        st.success("評估表已生成!")
        st.header("評估表")
        lesson_plan_data = [
            ["評估主題", learning_evaluate.evaluation_asset_title],
        ]
        for row in lesson_plan_data:
            st.subheader(row[0])
            st.write(row[1])
            st.write("---")  # Add a separator line

        st.subheader("評估表格")
        table_header = "| 評量項目 | 評量指標 | 優良(4分) | 良好(3分) | 尚可(2分) | 待加強(1分) |"
        table_separator = "|------------|---------|------------|----------------|----------------|----------------|"
        table_rows = [
            f"| {item.evaluation_item_title} | {item.evaluation_metric}| {item.score_descriptions.excellent_with_score_4} | {item.score_descriptions.good_with_score_3} | {item.score_descriptions.fair_with_score_2}|  {item.score_descriptions.needs_improvement_with_score_1}|" for item in learning_evaluate.evaluation_items
        ]
        table_markdown = "\n".join([table_header, table_separator] + table_rows)
        st.markdown(table_markdown)
        st.write("---")
        st.subheader("評估標準")

        number_of_evaluation_items = len(learning_evaluate.evaluation_items)
        st.write(f"⏹︎  優良: {3*(number_of_evaluation_items-1)}-{4*number_of_evaluation_items} 分,  表示學生能充分掌握技巧並理解其重要性。")
        st.write(f"⏹︎  良好: {2*(number_of_evaluation_items)}-{3*(number_of_evaluation_items-1)} 分,  表示學生能較好地完成步驟，但仍有待改進的部分。")
        st.write(f"⏹︎  尚可: {1*(number_of_evaluation_items)}-{2*(number_of_evaluation_items-1)} 分,  表示學生能完成部分步驟，但正確性和時間效率需加強。")
        st.write(f"⏹︎  待加強: {1*(number_of_evaluation_items-1)} 分,  表示學生需更多練習和輔助以掌握技巧。")
