from pydantic import BaseModel
from typing import List

class TeachingMethod(BaseModel):
    title: str
    explanation: str

class TeachingStep(BaseModel):
    title: str
    explanation: str

class AssessmentMethod(BaseModel):
    title: str
    explanation: str

class PracticeQuestion(BaseModel):
    question: str

class ActivityGuide(BaseModel):
    description: str

class ReflectionQuestion(BaseModel):
    question: str

class AssessmentQuestion(BaseModel):
    question: str

class SelfAssessmentItem(BaseModel):
    item: str

class LessonPlan(BaseModel):
    title: str
    objectives: str
    content: List[str]
    teaching_methods: List[TeachingMethod]
    teaching_steps: List[TeachingStep]
    assessment_methods: List[AssessmentMethod]

class WorksheetSection(BaseModel):
    practice_questions: List[PracticeQuestion]
    activity_guides: List[ActivityGuide]
    reflection_questions: List[ReflectionQuestion]
    assessment_questions: List[AssessmentQuestion]
    self_assessment_items: List[SelfAssessmentItem]
    collaborative_learning_activity: str

class LearningAsset(BaseModel):
    lesson_plan: LessonPlan
    worksheet: WorksheetSection