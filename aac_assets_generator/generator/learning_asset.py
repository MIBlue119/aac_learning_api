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
from reportlab.platypus import Spacer

from aac_assets_generator.learning_asset_models import LearningAsset, LessonPlan, WorksheetSection
import streamlit as st

class LearningAssetGenerator:
    """生成學習單/教案"""

    def __init__(self, client):
        self.client = client

    async def generate_learning_asset_async(
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
                response_format=LearningAsset,
            )
            logger.info(f"response:{response}")
            return response.choices[0].message.parsed, case_info
        except Exception as e:
            logger.error(f"生成學習單時發生錯誤: {str(e)}")
            return None, case_info

    def markdown_to_pdf(self,learning_asset: LearningAsset, main_title, sub_title, case_info):

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

        elements.append(Paragraph(f"{main_title}-{sub_title}", styles["Title"]))
        # Lesson Plan Title 
        elements.append(Paragraph("教案", styles["Title"]))
        elements.append(Paragraph("個案基本資料", styles["Heading2"]))
        for line in case_info.split('\n'):
            elements.append(Paragraph(line.strip(), styles["CustomStyle"]))          
        elements.append(Spacer(1, 12))
        # Lesson Plan Table
        lesson_plan_data = [
            ["教案名稱", Paragraph(learning_asset.lesson_plan.title, styles["CustomStyle"])],
            [
                "教學目標",
                Paragraph(" ".join(learning_asset.lesson_plan.objectives), styles["CustomStyle"]),
            ],
            # ["教學內容", Paragraph(learning_asset.lesson_plan.content, styles["CustomStyle"])],
            [
                "教學內容",
                Paragraph(
                    "<br/><br/>".join(
                        f"{i+1}. {content}"
                        for i, content in enumerate(learning_asset.lesson_plan.content)
                    ),
                    styles["CustomStyle"],
                ),
            ],
            [
                "教學方法",
                Paragraph(
                    "<br/><br/>".join(
                        [
                            f"{i+1}. {method.title}: {method.explanation}"
                            for i, method in enumerate(learning_asset.lesson_plan.teaching_methods)
                        ]
                    ),
                    styles["CustomStyle"],
                ),
            ],
            [
                "教學步驟",
                Paragraph(
                    "<br/><br/>".join(
                        [
                            f"{i+1}. {step.title}: {step.explanation}"
                            for i, step in enumerate(learning_asset.lesson_plan.teaching_steps)
                        ]
                    ),
                    styles["CustomStyle"],
                ),
            ],
            [
                "評量方式",
                Paragraph(
                    "<br/><br/>".join(
                        [
                            f"{i+1}. {method.title}: {method.explanation}"
                            for i, method in enumerate(
                                learning_asset.lesson_plan.assessment_methods
                            )
                        ]
                    ),
                    styles["CustomStyle"],
                ),
            ],
        ]

        lesson_plan_table = Table(lesson_plan_data, colWidths=[3 * cm, 15 * cm])
        lesson_plan_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
                    ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (-1, -1), "NotoSansTC"),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ]
            )
        )
        elements.append(lesson_plan_table)

        # Add page break
        elements.append(PageBreak())
        # Worksheet
        elements.append(Paragraph("學習單", styles["Title"]))

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
        assessment_table = Table(assessment_data, colWidths=[8 * cm, 3 * cm, 3 * cm, 4 * cm])
        assessment_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, -1), "NotoSansTC"),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ]
            )
        )
        elements.append(assessment_table)

        # Collaborative learning activity

        elements.append(Paragraph("六、合作學習活動", styles["Heading2"]))
        elements.append(
            Paragraph(
                learning_asset.worksheet.collaborative_learning_activity, styles["CustomStyle"]
            )
        )      
        elements.append(PageBreak())
        return elements



    def render_at_streamlit(self, learning_asset, case_info):
        st.success("學習單已生成!")
        st.header("教案")
        st.subheader("個案基本資料")
        # Split the case_info string by newlines and display each line
        for line in case_info.split('\n'):
            st.write(line.strip())
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