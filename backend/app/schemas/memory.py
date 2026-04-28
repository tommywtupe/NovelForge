from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.schemas.entity import (
	ConceptCard,
	ItemCard,
	OrganizationCardMemory,
	SceneCardMemory,
	UpdateDynamicInfo,
)
from app.schemas.relation_extract import RelationExtraction


class ParticipantTyped(BaseModel):
	name: str
	type: str


class QueryRequest(BaseModel):
	project_id: int
	participants: Optional[List[str]] = None
	radius: int = 2


class QueryResponse(BaseModel):
	nodes: List[Dict[str, Any]]
	edges: List[Dict[str, Any]]
	fact_summaries: List[str]
	relation_summaries: List[Dict[str, Any]]


class IngestRelationsLLMRequest(BaseModel):
	project_id: int
	text: str
	participants: Optional[List[ParticipantTyped]] = None
	llm_config_id: int = 1
	temperature: Optional[float] = None
	max_tokens: Optional[int] = None
	timeout: Optional[float] = None
	volume_number: Optional[int] = None
	chapter_number: Optional[int] = None


class IngestRelationsLLMResponse(BaseModel):
	written: int


class ExtractRelationsRequest(BaseModel):
	text: str
	participants: Optional[List[ParticipantTyped]] = None
	llm_config_id: int = 1
	temperature: Optional[float] = None
	max_tokens: Optional[int] = None
	timeout: Optional[float] = None
	volume_number: Optional[int] = None
	chapter_number: Optional[int] = None


class IngestRelationsFromPreviewRequest(BaseModel):
	project_id: int
	data: RelationExtraction
	volume_number: Optional[int] = None
	chapter_number: Optional[int] = None


class IngestRelationsFromPreviewResponse(BaseModel):
	written: int


class ExtractDynamicInfoRequest(BaseModel):
	project_id: int
	text: str
	participants: Optional[List[ParticipantTyped]] = None
	llm_config_id: int = 1
	temperature: Optional[float] = None
	max_tokens: Optional[int] = None
	timeout: Optional[float] = None
	extra_context: Optional[str] = None


class ExtractOnlyRequest(BaseModel):
	project_id: Optional[int] = None
	text: str
	participants: Optional[List[ParticipantTyped]] = None
	llm_config_id: int = 1
	temperature: Optional[float] = None
	max_tokens: Optional[int] = None
	timeout: Optional[float] = None
	extra_context: Optional[str] = None


class UpdateDynamicInfoRequest(BaseModel):
	project_id: int
	data: UpdateDynamicInfo
	queue_size: Optional[int] = 5


class UpdateDynamicInfoResponse(BaseModel):
	success: bool
	updated_card_count: int


class MemoryExtractorInfo(BaseModel):
	code: str
	name: str
	target: str
	preview_supported: bool = True


class MemoryExtractorListResponse(BaseModel):
	items: List[MemoryExtractorInfo]


class ExtractPreviewRequest(BaseModel):
	project_id: Optional[int] = None
	extractor_code: str
	text: str
	participants: Optional[List[ParticipantTyped]] = None
	llm_config_id: int = 1
	temperature: Optional[float] = None
	max_tokens: Optional[int] = None
	timeout: Optional[float] = None
	extra_context: Optional[str] = None
	volume_number: Optional[int] = None
	chapter_number: Optional[int] = None
	# 是否自动写入数据库（默认 False，保持原有行为）
	auto_apply: bool = False


class ExtractPreviewResponse(BaseModel):
	extractor_code: str
	preview_data: Dict[str, Any]
	affected_targets: List[Dict[str, Any]] = Field(default_factory=list)
	# 以下字段在 auto_apply=true 时返回
	written: Optional[int] = Field(default=None)
	updated_card_count: Optional[int] = Field(default=None)


class ApplyPreviewRequest(BaseModel):
	project_id: int
	extractor_code: str
	data: Dict[str, Any]
	options: Optional[Dict[str, Any]] = None
	participants: Optional[List[ParticipantTyped]] = None
	volume_number: Optional[int] = None
	chapter_number: Optional[int] = None


class ApplyPreviewResponse(BaseModel):
	success: bool
	written: int = 0
	updated_card_count: int = 0
	updated_relation_count: int = 0
	affected_targets: List[Dict[str, Any]] = Field(default_factory=list)
	raw_result: Dict[str, Any] = Field(default_factory=dict)


class ItemStateExtraction(BaseModel):
	items: List[ItemCard] = Field(default_factory=list)


class ConceptStateExtraction(BaseModel):
	concepts: List[ConceptCard] = Field(default_factory=list)


class SceneStateExtraction(BaseModel):
	scenes: List[SceneCardMemory] = Field(default_factory=list)


class OrganizationStateExtraction(BaseModel):
	organizations: List[OrganizationCardMemory] = Field(default_factory=list)


# 一站式记忆提取请求
class ExtractAllRequest(BaseModel):
	project_id: Optional[int] = None
	text: str
	participants: Optional[List[ParticipantTyped]] = None
	llm_config_id: int = 1
	temperature: Optional[float] = None
	max_tokens: Optional[int] = None
	timeout: Optional[float] = None
	extra_context: Optional[str] = None
	volume_number: Optional[int] = None
	chapter_number: Optional[int] = None
	# 是否直接写入数据库（默认 False，返回预览）
	auto_apply: bool = False


class TaskResult(BaseModel):
	"""单个提取任务的结果"""
	task: str  # 任务代码
	name: str  # 任务名称
	success: bool
	message: str = ""
	preview_data: Dict[str, Any] = Field(default_factory=dict)
	written: int = 0
	updated_card_count: int = 0
	updated_relation_count: int = 0


class ExtractAllResponse(BaseModel):
	"""一站式记忆提取响应"""
	results: List[TaskResult] = Field(default_factory=list)
	total_written: int = 0
	total_updated_cards: int = 0
	total_updated_relations: int = 0


class ApplyAllRequest(BaseModel):
	"""应用修改后的一站式提取结果"""
	project_id: int
	results: List[TaskResult] = Field(default_factory=list)
	volume_number: Optional[int] = None
	chapter_number: Optional[int] = None
