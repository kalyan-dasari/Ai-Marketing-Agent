from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from ..models import ProjectBrief

class BaseAIProvider(ABC):
    """Abstract interface for all campaign AI providers."""

    @abstractmethod
    def analyze_project(self, project: Dict[str, Any], sources: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Extracts verified problem, solution, features, audience, UVP,
        and unknowns from project description and sources.
        Never invents features or testimonials.
        """
        pass

    @abstractmethod
    def generate_campaign(
        self,
        project: Dict[str, Any],
        campaign: Dict[str, Any],
        brief: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Generates platform-specific draft assets across requested angles and platforms.
        """
        pass

    @abstractmethod
    def regenerate_asset(
        self,
        project: Dict[str, Any],
        asset: Dict[str, Any],
        instruction: str
    ) -> Dict[str, Any]:
        """
        Regenerates an existing asset's hook, body, and creative brief
        following user feedback instruction without hallucinating.
        """
        pass

    @abstractmethod
    def generate_recommendations(self, metrics_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Generates evidence-based recommendations based on actual recorded metrics.
        """
        pass
