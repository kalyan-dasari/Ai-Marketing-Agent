"""Deterministic, offline campaign provider. Never claims unsupported results."""
class MockProvider:
    def generate_campaign(self, project, campaign):
        name = project['name']
        description = project['description'].strip()
        link = project.get('website_url') or project.get('repository_url') or ''
        audience = campaign.get('audience') or 'people who build and use software'
        objective = campaign.get('objective') or 'Get thoughtful feedback'
        cta = campaign.get('cta') or 'What would you improve first?'
        return [
            {'platform':'LinkedIn','format':'Founder story','hook':f'I built {name} to explore a problem worth solving.', 'body':f"I kept thinking about this: {description}\n\nSo I started building {name}. The current version is an experiment, and I’m sharing the process while I learn what is useful to {audience}.\n\nI’d value an honest perspective from people who have run into this problem.", 'cta':cta, 'creative_brief':'Pair the post with a real screenshot of the current product. Avoid performance claims.', 'verification_notes':'Uses only the project description supplied by you; confirm the framing reflects your experience.'},
            {'platform':'Instagram','format':'Reel script · 20 seconds','hook':f'Can a small tool make this workflow simpler? Meet {name}.', 'body':f"Scene 1 (0–3s): Show the problem in one sentence: “{description}”\nScene 2 (3–8s): Show the current interface.\nScene 3 (8–15s): Walk through one real workflow in {name}.\nScene 4 (15–20s): Invite viewers to try the idea and share feedback.", 'cta':cta, 'creative_brief':'Vertical screen recording with readable captions. Show only working features; use a real screen capture.', 'verification_notes':'Demo steps are a structure, not verified product capabilities. Replace with an accurate walkthrough.'},
            {'platform':'Reddit','format':'Feedback request','hook':f'I’m working on {name} and would appreciate feedback on the approach', 'body':f"Hi everyone — I’m building {name}. The problem I’m exploring is: {description}\n\nI’m trying to understand whether this is a real pain point for people here and what a useful first version should do. If this fits the community rules, I’d love to hear how you currently handle it and what I’m missing.\n\nI’m happy to share more context or answer technical questions. I’ll include a link only if the subreddit permits project links.", 'cta':'How do you handle this today, and what would make a solution useful?', 'creative_brief':'Adapt the title and detail to the specific community. Read its rules first; submit manually and remove any link where promotion is restricted.', 'verification_notes':'Manual sharing only. Check subreddit rules and disclose that you built the project.'}
        ]
