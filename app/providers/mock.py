"""
Deterministic, offline campaign provider.
Operates with zero budget and zero external API dependencies.
Strictly relies on user-provided inputs and never fabricates unsupported results or metrics.
"""
import re
from typing import Dict, Any, List, Optional
from .base import BaseAIProvider
from ..models import ProjectBrief

class MockProvider(BaseAIProvider):
    """Deterministic, rule-based AI provider for offline development and testing."""

    def analyze_project(self, project: Dict[str, Any], sources: List[Dict[str, Any]]) -> Dict[str, Any]:
        name = project.get('name', 'Project')
        desc = project.get('description', '').strip()
        
        # Combine text from all sources
        all_text = desc
        source_refs = []
        for s in sources:
            stype = s.get('source_type', 'source')
            sname = s.get('file_name') or s.get('source_url') or stype
            source_refs.append(f"{stype}: {sname}")
            if s.get('content'):
                all_text += "\n" + s['content']
                
        # Extract potential feature bullet points from text
        feature_matches = re.findall(r'^[*-]\s+(.+)$', all_text, re.MULTILINE)
        if not feature_matches:
            # Fallback to key phrases
            sentences = [s.strip() for s in desc.split('.') if len(s.strip()) > 15]
            feature_matches = sentences[:4] if sentences else [desc]

        verified_features = [f.strip()[:180] for f in feature_matches[:6]]

        # Determine audience from keywords
        audience = "developers, builders, and early adopters"
        if any(w in all_text.lower() for w in ['student', 'campus', 'academic', 'college']):
            audience = "students, educators, and campus communities"
        elif any(w in all_text.lower() for w in ['designer', 'creative', 'marketing']):
            audience = "creatives, marketers, and product teams"
        elif any(w in all_text.lower() for w in ['business', 'founder', 'sales', 'b2b']):
            audience = "founders, operators, and small business teams"

        # Formulate brief
        brief = ProjectBrief(
            name=name,
            description=desc,
            problem=f"Existing workflows around this problem are often fragmented, manual, or difficult to coordinate: {desc[:140]}…",
            solution=f"{name} provides a focused, dedicated platform to streamline this directly.",
            verified_features=verified_features,
            target_audience=audience,
            unique_value_proposition=f"A targeted, purpose-built tool designed specifically for {audience}.",
            website_url=project.get('website_url'),
            repository_url=project.get('repository_url'),
            evidence_and_sources=source_refs if source_refs else ["User project description"],
            unknown_or_unverified_claims=[
                "User adoption numbers, retention metrics, and growth figures (unrecorded)",
                "External third-party benchmark speeds or comparative claims (unverified)"
            ]
        )
        return brief.to_dict()

    def generate_campaign(
        self,
        project: Dict[str, Any],
        campaign: Dict[str, Any],
        brief: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        name = project['name']
        description = project.get('description', '').strip()
        link = project.get('website_url') or project.get('repository_url') or ''
        audience = campaign.get('audience') or (brief.get('target_audience') if brief else None) or 'people building software'
        objective = campaign.get('objective') or 'Get thoughtful feedback'
        tone = campaign.get('tone') or 'Personal and useful'
        cta = campaign.get('cta') or 'What would you improve or try first?'
        duration = int(campaign.get('duration_days', 7))

        selected_platforms = campaign.get('platforms') or ['LinkedIn', 'Instagram', 'Reddit']
        if isinstance(selected_platforms, str):
            import json
            try:
                selected_platforms = json.loads(selected_platforms)
            except Exception:
                selected_platforms = ['LinkedIn', 'Instagram', 'Reddit']

        features = (brief.get('verified_features') if brief else []) or [
            "Focused workflow without clutter",
            "Direct and transparent interaction",
            "Built with open tools and straightforward setup"
        ]
        feat_str = "\n".join([f"• {f}" for f in features[:3]])

        assets = []
        day_step = max(1, duration // 4)
        offset = 0

        # 1. LinkedIn: Founder Story
        if 'LinkedIn' in selected_platforms:
            assets.append({
                'platform': 'LinkedIn',
                'format': 'Founder story',
                'hook': f"I spent the last few weeks building {name} to solve a real friction I kept running into.",
                'body': f"Here is the problem: {description}\n\nMost tools in this space either feel overly complicated or miss the practical details. So I decided to build {name}.\n\nKey focus areas so far:\n{feat_str}\n\nThis is an early build, and I'm sharing the journey openly. I would really appreciate candid feedback from {audience}.\n\nWhat is your biggest pain point when dealing with this today?",
                'cta': cta,
                'creative_brief': 'Clean screenshot of the application interface or terminal output. Avoid stock imagery or inflated claims.',
                'project_link': link,
                'verification_notes': 'Derived strictly from your provided project description and features. Verify that the problem statement accurately captures your personal experience.',
                'scheduled_offset_days': offset
            })
            offset += day_step

        # 2. LinkedIn: Technical Lessons & Architecture
        if 'LinkedIn' in selected_platforms and duration >= 7:
            assets.append({
                'platform': 'LinkedIn',
                'format': 'Technical lesson',
                'hook': f"3 engineering trade-offs I made while architecting {name}.",
                'body': f"Building {name} ({description[:90]}…) forced some interesting technical decisions:\n\n1. Simplicity over premature scaling: kept the core architecture lean and modular.\n2. Strict input validation and security from day one.\n3. Offline and zero-budget first: ensuring core utility works reliably without paid API gates.\n\nTo other engineers building in public: what architectural choices do you prioritize when launching v1?",
                'cta': 'What architectural trade-off have you found most worthwhile in your recent projects?',
                'creative_brief': 'Code snippet screenshot or simple system architecture diagram showing the modular data flow.',
                'project_link': project.get('repository_url') or link,
                'verification_notes': 'Technical takeaways are structured prompts. Customize the 3 decisions to match your exact technology stack.',
                'scheduled_offset_days': min(offset, duration - 1)
            })
            offset += day_step

        # 3. Instagram: Reel script & Demo Walkthrough
        if 'Instagram' in selected_platforms:
            assets.append({
                'platform': 'Instagram',
                'format': 'Reel script · 25 seconds',
                'hook': f"How I built a tool for {audience} in my spare time. Meet {name}.",
                'body': f"Hook (0-3s): Quick text-on-screen: 'Tired of this workflow? Here is how {name} fixes it.'\n\nProblem (3-7s): Show the frustration: {description[:80]}…\n\nWalkthrough (7-18s): Screen capture highlighting the main feature in action:\n{feat_str}\n\nCall to Action (18-25s): 'Drop a comment with your thoughts or test the project link in bio.'",
                'cta': 'Comment your thoughts below or check the link in bio to test it out!',
                'creative_brief': 'Vertical 9:16 screen recording. High contrast captions, no artificial hype. Show actual UI interactions.',
                'project_link': link,
                'verification_notes': 'Demo steps are an outline. Ensure the screen recording showcases actual working features and avoids mockups.',
                'scheduled_offset_days': min(offset, duration - 1)
            })
            offset += day_step

        # 4. Instagram: Carousel Outline / Problem & Solution
        if 'Instagram' in selected_platforms and duration >= 10:
            assets.append({
                'platform': 'Instagram',
                'format': 'Carousel outline · 5 slides',
                'hook': f"Why most workflows for {audience} break down (and what we built instead).",
                'body': f"Slide 1 (Cover): The biggest barrier {audience} face right now.\nSlide 2 (The Friction): {description}\nSlide 3 (The Approach): How {name} structures the solution.\nSlide 4 (Core Capabilities):\n{feat_str}\nSlide 5 (Next Step): Try it out and let me know what feature you'd build next.",
                'cta': 'Save this post for reference and share your thoughts in the comments.',
                'creative_brief': 'Carousel graphics with minimal aesthetic, high readability typography, and dark or neutral backgrounds.',
                'project_link': link,
                'verification_notes': 'Verify each slide content before generating graphics. Do not claim verified user outcomes.',
                'scheduled_offset_days': min(offset, duration - 1)
            })
            offset += day_step

        # 5. Reddit: Authentic Feedback Request
        if 'Reddit' in selected_platforms:
            assets.append({
                'platform': 'Reddit',
                'format': 'Feedback request',
                'hook': f"I built an open tool for {name.lower()} and would value community feedback on the approach",
                'body': f"Hi r/community,\n\nI’ve been building {name} because I noticed: {description}\n\nRather than assuming I know what’s best, I wanted to bring the prototype to people who deal with this directly. The current build focuses on:\n{feat_str}\n\nI’m keen to learn:\n1. Is this a genuine pain point for your day-to-day workflow?\n2. What critical capability is missing from this first version?\n\nI am happy to answer questions or share the codebase/link if it complies with the community rules. Thanks for your time!",
                'cta': 'How do you currently handle this, and what would make a tool like this genuinely useful to you?',
                'creative_brief': 'No images required. Maintain conversational, humble markdown format. Always check subreddit rules before sharing.',
                'verification_notes': 'Strictly manual submission! Disclose that you are the author. Remove links if the subreddit disallows self-promotion.',
                'scheduled_offset_days': min(offset, duration - 1)
            })
            offset += day_step

        # 6. Reddit: Technical Build Log
        if 'Reddit' in selected_platforms and duration >= 14:
            assets.append({
                'platform': 'Reddit',
                'format': 'Build log & Discussion',
                'hook': f"Building {name}: What worked, what failed, and architecture takeaways",
                'body': f"Hey everyone,\n\nI wanted to share a transparent build log for {name} ({description[:100]}…).\n\nWhen starting, the main goal was zero-dependency overhead and rock-solid local reliability. Here are three things I learned:\n\n- Keeping data local by default removes latency and security worries.\n- Designing modular provider layers makes future extension straightforward.\n- Feedback-driven iteration beats building features in isolation.\n\nCode and details are in the repo for anyone interested in the implementation.\n\nOpen to code reviews, critique, and suggestions!",
                'cta': 'Looking forward to hearing your critiques and technical suggestions.',
                'creative_brief': 'Text-only discussion. Provide GitHub repository link only in comments or where explicitly requested.',
                'project_link': project.get('repository_url') or link,
                'verification_notes': 'Review against target subreddit rules regarding project showcase flair and self-promotion policies.',
                'scheduled_offset_days': min(offset, duration - 1)
            })

        return assets

    def regenerate_asset(
        self,
        project: Dict[str, Any],
        asset: Dict[str, Any],
        instruction: str
    ) -> Dict[str, Any]:
        """Regenerates an asset incorporating specific user feedback."""
        instruction_lower = instruction.lower()
        name = project['name']
        desc = project.get('description', '')
        link = project.get('website_url') or project.get('repository_url') or ''
        platform = asset['platform']
        fmt = asset['format']

        # Determine adjustments based on instruction
        more_technical = any(w in instruction_lower for w in ['tech', 'code', 'engineer', 'arch', 'stack'])
        more_concise = any(w in instruction_lower for w in ['short', 'concise', 'brief', 'bullet', 'punchy'])
        student_focus = any(w in instruction_lower for w in ['student', 'campus', 'college', 'academic'])

        if platform == 'LinkedIn':
            if more_technical:
                hook = f"The engineering behind {name}: solving {desc[:60]} at the architecture level."
                body = f"When building {name}, the priority was building an extensible, decoupled engine.\n\nStack & Implementation highlights:\n• Python backend with clean modular abstractions\n• Zero-dependency local persistence for complete privacy\n• State-machine workflow for controlled approvals\n\nCheck out the implementation: {link}\n\nFeedback on the architecture is welcome."
            elif more_concise:
                hook = f"Why I built {name} in one sentence: {desc[:90]}."
                body = f"Here is what {name} does:\n• Directly tackles: {desc}\n• Keeps workflows simple, verified, and accessible\n• Zero hype, just working software.\n\nTry it: {link}\n\nWhat would you like to see next?"
            elif student_focus:
                hook = f"Can student services and peer collaboration be dramatically simplified? Introducing {name}."
                body = f"Students often juggle fragmented groups, informal chats, and unorganized requests. {name} is built to give students a dedicated, legitimate space to offer services and connect.\n\nCurrently testing early workflows. If you’re a student or educator, I’d love your take:\n{link}"
            else:
                hook = f"Refined perspective on {name}: {instruction[:80]}."
                body = f"Following up on the build of {name} ({desc}):\n\n{instruction}\n\nI’m actively shaping this project based on real community feedback. Test the live build here: {link}"
            creative_brief = "Screenshot of the active code or product interface with high-contrast text overlay."

        elif platform == 'Instagram':
            if more_concise:
                hook = f"15-second teardown of {name}."
                body = f"Hook (0-2s): Stop doing this manually.\nFeature (2-10s): How {name} automates the workflow in 3 clicks.\nOutro (10-15s): Tap the link in bio to try it yourself."
            else:
                hook = f"Behind the scenes of building {name} for { 'students' if student_focus else 'creators' }."
                body = f"Scene 1: The everyday problem ({desc[:70]})\nScene 2: Opening {name} and setting up the workflow\nScene 3: Real result in seconds\nScene 4: Question for viewers: '{instruction[:60] if instruction else 'What do you think?'}'"
            creative_brief = "Vertical mobile video showing screen recording with clear text subtitles and smooth transitions."

        else:  # Reddit
            if more_technical:
                hook = f"[Showcase] Built {name} – technical design and lessons learned"
                body = f"Hey everyone,\n\nI put together {name} ({desc}).\n\nAdjusted based on feedback: {instruction}\n\nArchitecture details and repo: {link}\n\nWould appreciate technical feedback on the codebase and design choices."
            else:
                hook = f"Update on {name}: iterating based on community feedback ({instruction[:50]})"
                body = f"Hi everyone,\n\nTaking your suggestions into account for {name} ({desc}).\n\nSpecifically focusing on: {instruction}\n\nHow does this align with how you handle this problem today?"
            creative_brief = "Text-only post tailored to subreddit rules. Respect community self-promotion policies."

        return {
            'hook': hook,
            'body': body,
            'cta': asset.get('cta', 'What are your thoughts?'),
            'creative_brief': creative_brief,
            'verification_notes': f"Regenerated according to instruction: '{instruction}'. Verify facts before publishing."
        }

    def generate_recommendations(self, metrics_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyzes recorded campaign performance and outputs factual recommendations."""
        if not metrics_data:
            return [{
                'type': 'observation',
                'title': 'No performance data recorded yet',
                'summary': 'Record reach, impressions, and engagement metrics for your published posts to unlock evidence-based recommendations.',
                'actionable_step': 'Go to Content Studio or Distribution Tracker and log metrics after sharing your posts.'
            }]

        total_impressions = sum(m.get('impressions', 0) for m in metrics_data)
        total_engagements = sum(m.get('engagements', 0) for m in metrics_data)
        total_clicks = sum(m.get('clicks', 0) for m in metrics_data)
        
        # Calculate rates
        overall_eng_rate = (total_engagements / total_impressions * 100) if total_impressions > 0 else 0
        overall_ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0

        # Group by platform
        platform_metrics: Dict[str, Dict[str, int]] = {}
        for m in metrics_data:
            p = m.get('platform', 'Unknown')
            if p not in platform_metrics:
                platform_metrics[p] = {'impressions': 0, 'engagements': 0, 'clicks': 0}
            platform_metrics[p]['impressions'] += m.get('impressions', 0)
            platform_metrics[p]['engagements'] += m.get('engagements', 0)
            platform_metrics[p]['clicks'] += m.get('clicks', 0)

        recommendations = []

        # Top platform recommendation
        best_platform = None
        best_rate = -1.0
        for p, data in platform_metrics.items():
            if data['impressions'] > 0:
                rate = (data['engagements'] / data['impressions']) * 100
                if rate > best_rate:
                    best_rate = rate
                    best_platform = p

        if best_platform and best_rate > 0:
            recommendations.append({
                'type': 'channel_focus',
                'title': f'{best_platform} generated your highest engagement rate ({best_rate:.1f}%)',
                'summary': f'Recorded {platform_metrics[best_platform]["engagements"]} engagements across {platform_metrics[best_platform]["impressions"]} impressions on {best_platform}.',
                'actionable_step': f'Prioritize {best_platform} for your next campaign milestone and double down on interactive formats.'
            })

        # Click-through insight
        if total_clicks > 0:
            recommendations.append({
                'type': 'traffic_driver',
                'title': f'Recorded {total_clicks} link visits across campaigns ({overall_ctr:.1f}% CTR)',
                'summary': f'Direct calls to action with project URLs converted at {overall_ctr:.1f}% click-through rate.',
                'actionable_step': 'Keep your primary project link clear in the post copy or comments without adding multiple conflicting links.'
            })
        else:
            recommendations.append({
                'type': 'traffic_opportunity',
                'title': 'High impressions but low click-through to repository/website',
                'summary': 'Viewers engaged with content but may need a more explicit reason to visit the live project.',
                'actionable_step': 'Test a more direct CTA such as "Try the live prototype at [link]" or "Star the repo if you build with Python".'
            })

        return recommendations
