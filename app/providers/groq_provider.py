"""
Groq Cloud AI Provider.
Leverages Groq's ultra-fast LPU inference to generate high quality,
multi-channel marketing campaigns while strictly respecting ground truth.
Includes automatic fallback to MockProvider if network or rate limit issues occur.
"""
import os
import json
import logging
import requests
from typing import Dict, Any, List, Optional
from .base import BaseAIProvider
from .mock import MockProvider
from ..models import ProjectBrief

log = logging.getLogger(__name__)

class GroqProvider(BaseAIProvider):
    GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
    GROQ_MODELS_URL = "https://api.groq.com/openai/v1/models"

    def __init__(self, api_key: Optional[str] = None, model: str = "openai/gpt-oss-120b"):
        self.api_key = api_key or os.environ.get('GROQ_API_KEY', '')
        self.model = model or os.environ.get('GROQ_MODEL', 'openai/gpt-oss-120b')
        self.mock_fallback = MockProvider()

    def test_connection(self) -> tuple[bool, str]:
        """Tests connectivity with Groq API and validates the API key."""
        if not self.api_key:
            return False, "Groq API key is not configured."
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ProjectToReach/1.0"
            }
            res = requests.get(self.GROQ_MODELS_URL, headers=headers, timeout=8)
            if res.status_code == 200:
                data = res.json()
                models = [m.get('id') for m in data.get('data', [])]
                model_str = ", ".join(models[:4]) if models else "Connected"
                return True, f"Connected to Groq Cloud! Models: {model_str}"
            elif res.status_code == 401:
                return False, "Invalid Groq API key."
            else:
                return False, f"Groq API returned HTTP {res.status_code}: {res.text[:120]}"
        except Exception as e:
            return False, f"Could not connect to Groq API: {str(e)}"

    def _call_groq(self, messages: List[Dict[str, str]], temperature: float = 0.3, json_mode: bool = True) -> Optional[str]:
        """Executes a chat completion request to Groq."""
        if not self.api_key:
            log.warning("No Groq API key present, falling back to mock provider.")
            return None

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ProjectToReach/1.0"
        }
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 4096
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        try:
            res = requests.post(self.GROQ_API_URL, headers=headers, json=payload, timeout=25)
            if res.status_code == 200:
                result = res.json()
                return result['choices'][0]['message']['content'].strip()
            else:
                log.warning(f"Groq API error ({res.status_code}): {res.text[:200]}")
        except Exception as e:
            log.warning(f"Groq request exception: {e}")

        return None

    def analyze_project(self, project: Dict[str, Any], sources: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Uses Groq to analyze project inputs and extract a verified Project Brief."""
        name = project.get('name', 'Project')
        desc = project.get('description', '')

        # Build combined context from sources
        sources_text = ""
        source_refs = []
        for s in sources:
            stype = s.get('source_type', 'source')
            sname = s.get('file_name') or s.get('source_url') or stype
            source_refs.append(f"{stype}: {sname}")
            if s.get('content'):
                sources_text += f"\n--- {sname} ---\n" + s['content'][:3000]

        system_prompt = (
            "You are a senior product marketing architect. Your job is to extract a strictly verified project brief "
            "from the user's project description and documentation.\n"
            "CRITICAL RULES:\n"
            "1. NEVER invent features, user adoption numbers, speed benchmarks, or customer quotes.\n"
            "2. Identify unknown or unverified claims explicitly.\n"
            "3. Output MUST be valid JSON with keys:\n"
            "   - 'problem' (string)\n"
            "   - 'solution' (string)\n"
            "   - 'verified_features' (array of strings, 3-6 items)\n"
            "   - 'target_audience' (string)\n"
            "   - 'unique_value_proposition' (string)\n"
            "   - 'unknown_or_unverified_claims' (array of strings)\n"
        )

        user_content = f"Project Name: {name}\nDescription: {desc}\nSources & Documentation:\n{sources_text}"
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]

        response_text = self._call_groq(messages, temperature=0.2, json_mode=True)
        if response_text:
            try:
                start = response_text.find('{')
                end = response_text.rfind('}') + 1
                if start != -1 and end != -1:
                    data = json.loads(response_text[start:end])
                    brief = ProjectBrief(
                        name=name,
                        description=desc,
                        problem=data.get('problem', f"Workflow fragmentation around {desc[:100]}…"),
                        solution=data.get('solution', f"{name} streamlines this workflow directly."),
                        verified_features=data.get('verified_features', [desc]),
                        target_audience=data.get('target_audience', 'developers and early builders'),
                        unique_value_proposition=data.get('unique_value_proposition', f"A dedicated tool for {name}."),
                        website_url=project.get('website_url'),
                        repository_url=project.get('repository_url'),
                        evidence_and_sources=source_refs if source_refs else ["User project description"],
                        unknown_or_unverified_claims=data.get('unknown_or_unverified_claims', [
                            "User adoption metrics and active retention (unrecorded)"
                        ])
                    )
                    return brief.to_dict()
            except Exception as e:
                log.warning(f"Failed to parse Groq brief JSON: {e}")

        # Fallback to mock provider
        return self.mock_fallback.analyze_project(project, sources)

    def generate_campaign(
        self,
        project: Dict[str, Any],
        campaign: Dict[str, Any],
        brief: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Uses Groq to generate multi-angle, platform-specific campaign drafts."""
        name = project['name']
        description = project.get('description', '')
        link = project.get('website_url') or project.get('repository_url') or ''
        audience = campaign.get('audience') or (brief.get('target_audience') if brief else '') or 'people who build software'
        objective = campaign.get('objective', 'Get thoughtful feedback')
        tone = campaign.get('tone', 'Personal and useful')
        cta = campaign.get('cta', 'What would you improve first?')
        duration = int(campaign.get('duration_days', 7))

        selected_platforms = campaign.get('platforms') or ['LinkedIn', 'Instagram', 'Reddit']
        if isinstance(selected_platforms, str):
            try:
                selected_platforms = json.loads(selected_platforms)
            except Exception:
                selected_platforms = ['LinkedIn', 'Instagram', 'Reddit']

        features = (brief.get('verified_features') if brief else []) or [description]
        feat_list = "\n".join([f"- {f}" for f in features[:5]])

        system_prompt = (
            "You are an expert tech marketer and copywriter. Generate a multi-platform marketing campaign.\n"
            "CRITICAL RULES:\n"
            "1. NO fabricated stats, user numbers, testimonials, or fake hype.\n"
            "2. Adapt tone and format to each platform:\n"
            "   - LinkedIn: Founder building stories, transparent architecture trade-offs, engineering lessons.\n"
            "   - Instagram: Visual Reel scripts (scene-by-scene with timestamps), Carousel outlines.\n"
            "   - Reddit: Humble community feedback requests, technical build logs. Disclose author status.\n"
            "3. Output MUST be a JSON object with a single key 'assets', containing an array of objects:\n"
            "   - 'platform' ('LinkedIn', 'Instagram', or 'Reddit')\n"
            "   - 'format' (e.g. 'Founder story', 'Reel script · 25s', 'Feedback request', 'Technical lesson')\n"
            "   - 'hook' (punchy, authentic title/hook, max 150 chars)\n"
            "   - 'body' (structured copy ready for the platform)\n"
            "   - 'cta' (call to action)\n"
            "   - 'creative_brief' (visual instruction e.g. real screenshot, code capture, screen recording)\n"
            "   - 'verification_notes' (fact-checking notes for the user)\n"
            "   - 'scheduled_offset_days' (integer offset from 0 to duration-1)\n"
        )

        user_content = (
            f"Project: {name}\n"
            f"Description: {description}\n"
            f"Verified Features:\n{feat_list}\n"
            f"Target Audience: {audience}\n"
            f"Campaign Objective: {objective}\n"
            f"Tone: {tone}\n"
            f"Default CTA: {cta}\n"
            f"Campaign Duration: {duration} days\n"
            f"Requested Platforms: {', '.join(selected_platforms)}\n"
            f"Generate 1-2 distinct assets for each requested platform spread across {duration} days."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]

        response_text = self._call_groq(messages, temperature=0.4, json_mode=True)
        if response_text:
            try:
                start = response_text.find('{')
                end = response_text.rfind('}') + 1
                if start != -1 and end != -1:
                    data = json.loads(response_text[start:end])
                    assets = data.get('assets', [])
                    valid_assets = []
                    for a in assets:
                        if a.get('platform') in selected_platforms and a.get('hook') and a.get('body'):
                            valid_assets.append({
                                'platform': a['platform'],
                                'format': a.get('format', 'Draft Post'),
                                'hook': a['hook'].strip(),
                                'body': a['body'].strip(),
                                'cta': a.get('cta', cta),
                                'creative_brief': a.get('creative_brief', 'Real product screenshot'),
                                'project_link': link,
                                'verification_notes': a.get('verification_notes', 'Generated with Groq AI. Verify facts before sharing.'),
                                'scheduled_offset_days': min(int(a.get('scheduled_offset_days', 0)), duration - 1)
                            })
                    if valid_assets:
                        return valid_assets
            except Exception as e:
                log.warning(f"Failed to parse Groq campaign JSON: {e}")

        # Fallback to deterministic mock
        return self.mock_fallback.generate_campaign(project, campaign, brief)

    def regenerate_asset(
        self,
        project: Dict[str, Any],
        asset: Dict[str, Any],
        instruction: str
    ) -> Dict[str, Any]:
        """Rewrites an existing asset based on user instruction using Groq."""
        system_prompt = (
            "You are a marketing editor. Rewrite the provided marketing post incorporating the user's specific feedback.\n"
            "Rules: Do not invent false facts. Output JSON with keys 'hook', 'body', 'creative_brief'."
        )

        user_content = (
            f"Project: {project.get('name')}\n"
            f"Platform: {asset.get('platform')}\n"
            f"Format: {asset.get('format')}\n"
            f"Current Hook: {asset.get('hook')}\n"
            f"Current Body:\n{asset.get('body')}\n"
            f"User Feedback / Revision Instruction: {instruction}\n"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]

        response_text = self._call_groq(messages, temperature=0.3, json_mode=True)
        if response_text:
            try:
                start = response_text.find('{')
                end = response_text.rfind('}') + 1
                if start != -1 and end != -1:
                    data = json.loads(response_text[start:end])
                    if data.get('hook') and data.get('body'):
                        return {
                            'hook': data['hook'].strip(),
                            'body': data['body'].strip(),
                            'cta': asset.get('cta', ''),
                            'creative_brief': data.get('creative_brief', asset.get('creative_brief', '')),
                            'verification_notes': f"Regenerated via Groq ({self.model}) following: '{instruction}'."
                        }
            except Exception as e:
                log.warning(f"Failed to parse regenerated Groq asset JSON: {e}")

        return self.mock_fallback.regenerate_asset(project, asset, instruction)

    def generate_recommendations(self, metrics_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Uses Groq to synthesize evidence-based marketing insights from recorded data."""
        if not metrics_data:
            return self.mock_fallback.generate_recommendations(metrics_data)

        # Baseline factual recommendations
        base_recs = self.mock_fallback.generate_recommendations(metrics_data)

        # Format metrics summary for Groq
        summary_lines = []
        for m in metrics_data[:8]:
            summary_lines.append(
                f"- Platform: {m.get('platform')}, Format: {m.get('format')}, "
                f"Impressions: {m.get('impressions')}, Engagements: {m.get('engagements')}, Clicks: {m.get('clicks')}"
            )

        system_prompt = (
            "Analyze these marketing campaign performance metrics and provide 1-2 actionable, evidence-based recommendations.\n"
            "Distinguish measured facts from hypotheses. Output JSON with a single key 'recommendations' (array of objects with 'title', 'summary', 'actionable_step')."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Recorded Post Performance:\n" + "\n".join(summary_lines)}
        ]

        response_text = self._call_groq(messages, temperature=0.2, json_mode=True)
        if response_text:
            try:
                start = response_text.find('{')
                end = response_text.rfind('}') + 1
                if start != -1 and end != -1:
                    data = json.loads(response_text[start:end])
                    llm_recs = data.get('recommendations', [])
                    if llm_recs:
                        return llm_recs
            except Exception as e:
                log.warning(f"Failed to parse Groq recommendations JSON: {e}")

        return base_recs
