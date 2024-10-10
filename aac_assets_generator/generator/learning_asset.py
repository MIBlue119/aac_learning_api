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

from aac_assets_generator.learning_asset_models import LearningAsset, LessonPlan, WorksheetSection


class LearningAssetGenerator:
    """生成學習單/教案"""

    def __init__(self, client):
        self.client = client

    async def generate_learning_asset_async(
        self, case_info, learn_assets_contents, prompt, model="gpt-4o-mini"
    ):
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
            return response.choices[0].message.parsed
        except Exception as e:
            logger.error(f"生成學習單時發生錯誤: {str(e)}")
            return None

    def markdown_to_pdf(self,learning_asset: LearningAsset):
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
                leftIndent=20,  # Add this line to create indentation
            )
        )

        for style in styles.byName.values():
            style.fontName = "NotoSansTC"

        elements = []

        # Lesson Plan Title
        elements.append(Paragraph("教案", styles["Title"]))

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

        doc.build(elements)
        buffer.seek(0)
        return buffer
