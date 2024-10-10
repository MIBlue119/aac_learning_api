from pydantic import BaseModel
from typing import List

class ScoreLevelDescriptions(BaseModel):
    excellent_with_score_4: str  # 優良（4分）
    good_with_score_3: str  # 良好（3分）
    fair_with_score_2: str  # 尚可（2分）
    needs_improvement_with_score_1: str  # 待加強（1分）

class EvaluationItem(BaseModel):
    evaluation_item_title: str
    evaluation_metric: str
    score_descriptions: ScoreLevelDescriptions

class EvaluationAssetTable(BaseModel):
    evaluation_asset_title: str
    evaluation_items: List[EvaluationItem]
