from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any

@dataclass
class ProjectBrief:
    name: str
    description: str
    problem: str
    solution: str
    verified_features: List[str] = field(default_factory=list)
    target_audience: str = ""
    unique_value_proposition: str = ""
    website_url: Optional[str] = None
    repository_url: Optional[str] = None
    evidence_and_sources: List[str] = field(default_factory=list)
    unknown_or_unverified_claims: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class GeneratedAsset:
    platform: str
    format: str
    hook: str
    body: str
    cta: str
    creative_brief: str
    project_link: Optional[str] = None
    verification_notes: str = ""
    scheduled_offset_days: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
