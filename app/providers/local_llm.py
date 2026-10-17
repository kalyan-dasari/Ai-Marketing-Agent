"""
Local LLM AI Provider supporting local Ollama or OpenAI-compatible server.
Provides local offline intelligence with zero paid API costs.
Falls back safely to MockProvider if local service is unavailable.
"""
import json
import logging
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional
from .base import BaseAIProvider
from .mock import MockProvider

log = logging.getLogger(__name__)

class LocalLLMProvider(BaseAIProvider):
    def __init__(self, endpoint_url: str = 'http://127.0.0.1:11434', model: str = 'llama3'):
        self.endpoint_url = endpoint_url.rstrip('/')
        self.model = model
        self.mock_fallback = MockProvider()

    def test_connection(self) -> tuple[bool, str]:
        """Tests if the local Ollama or LLM server is accessible."""
        try:
            # Check Ollama tags endpoint
            req = urllib.request.Request(f"{self.endpoint_url}/api/tags", headers={'User-Agent': 'ProjectToReach'})
            with urllib.request.urlopen(req, timeout=3) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode('utf-8'))
                    models = [m.get('name') for m in data.get('models', [])]
                    model_str = ", ".join(models[:4]) if models else "No models installed yet"
                    return True, f"Connected to Ollama! Available models: {model_str}"
        except Exception as e:
            # Check if it's an OpenAI-compatible /v1/models endpoint
            try:
                req = urllib.request.Request(f"{self.endpoint_url}/v1/models", headers={'User-Agent': 'ProjectToReach'})
                with urllib.request.urlopen(req, timeout=3) as resp:
                    if resp.status == 200:
                        return True, "Connected to OpenAI-compatible local server!"
            except Exception:
                pass
            return False, f"Could not connect to {self.endpoint_url}: {str(e)}"
        return False, "Could not reach local server."

    def _call_ollama(self, prompt: str, system: str = "") -> Optional[str]:
        """Calls Ollama HTTP API with timeout and error handling."""
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "system": system,
                "stream": False,
                "options": {"temperature": 0.3}
            }
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                f"{self.endpoint_url}/api/generate",
                data=data,
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                if resp.status == 200:
                    res_json = json.loads(resp.read().decode('utf-8'))
                    return res_json.get('response', '').strip()
        except Exception as e:
            log.warning(f"Local LLM call failed ({str(e)}), using deterministic fallback.")
        return None

    def analyze_project(self, project: Dict[str, Any], sources: List[Dict[str, Any]]) -> Dict[str, Any]:
        # Generate prompt for structured analysis
        prompt = f"""You are a product marketing analyst. Analyze this software project and produce a JSON object with keys:
"problem", "solution", "verified_features" (array of strings), "target_audience", "unique_value_proposition", "unknown_or_unverified_claims" (array of strings).
Rules: Do NOT invent features, numbers, or testimonials.
Project Name: {project.get('name')}
Description: {project.get('description')}
"""
        response = self._call_ollama(prompt, system="Output pure JSON only.")
        if response:
            try:
                # Find JSON block
                start = response.find('{')
                end = response.rfind('}') + 1
                if start != -1 and end != -1:
                    parsed = json.loads(response[start:end])
                    brief = self.mock_fallback.analyze_project(project, sources)
                    brief.update({
                        'problem': parsed.get('problem', brief['problem']),
                        'solution': parsed.get('solution', brief['solution']),
                        'verified_features': parsed.get('verified_features', brief['verified_features']),
                        'target_audience': parsed.get('target_audience', brief['target_audience']),
                        'unique_value_proposition': parsed.get('unique_value_proposition', brief['unique_value_proposition']),
                        'unknown_or_unverified_claims': parsed.get('unknown_or_unverified_claims', brief['unknown_or_unverified_claims'])
                    })
                    return brief
            except Exception as e:
                log.warning(f"Failed to parse LLM JSON: {e}")

        return self.mock_fallback.analyze_project(project, sources)

    def generate_campaign(
        self,
        project: Dict[str, Any],
        campaign: Dict[str, Any],
        brief: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        # Always obtain baseline drafts from mock to ensure reliability
        base_drafts = self.mock_fallback.generate_campaign(project, campaign, brief)
        return base_drafts

    def regenerate_asset(
        self,
        project: Dict[str, Any],
        asset: Dict[str, Any],
        instruction: str
    ) -> Dict[str, Any]:
        prompt = f"""Rewrite the following marketing content asset according to this instruction:
Instruction: {instruction}
Platform: {asset.get('platform')}
Current Hook: {asset.get('hook')}
Current Content: {asset.get('body')}

Output a JSON object with: "hook", "body", "creative_brief"."""
        response = self._call_ollama(prompt, system="Output pure JSON only. Never invent unsupported facts.")
        if response:
            try:
                start = response.find('{')
                end = response.rfind('}') + 1
                if start != -1 and end != -1:
                    data = json.loads(response[start:end])
                    if data.get('hook') and data.get('body'):
                        return {
                            'hook': data['hook'].strip(),
                            'body': data['body'].strip(),
                            'cta': asset.get('cta', ''),
                            'creative_brief': data.get('creative_brief', asset.get('creative_brief', '')),
                            'verification_notes': f"Regenerated with local LLM ({self.model}) following: '{instruction}'."
                        }
            except Exception as e:
                log.warning(f"Failed to parse regenerated LLM asset: {e}")

        return self.mock_fallback.regenerate_asset(project, asset, instruction)

    def generate_recommendations(self, metrics_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return self.mock_fallback.generate_recommendations(metrics_data)
