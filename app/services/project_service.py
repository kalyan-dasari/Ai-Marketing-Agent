import re
import json
import logging
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional
from ..db import get_db
from ..providers.factory import get_ai_provider
from .security import is_safe_url, is_allowed_file, sanitize_text, MAX_REMOTE_FETCH_SIZE, REQUEST_TIMEOUT

log = logging.getLogger(__name__)

class ProjectService:
    @staticmethod
    def get_all_projects() -> List[Dict[str, Any]]:
        db = get_db()
        rows = db.execute("SELECT * FROM projects ORDER BY created_at DESC").fetchall()
        projects = []
        for r in rows:
            p = dict(r)
            if p.get('brief_json'):
                try:
                    p['brief'] = json.loads(p['brief_json'])
                except Exception:
                    p['brief'] = None
            else:
                p['brief'] = None
            projects.append(p)
        return projects

    @staticmethod
    def get_project_by_id(project_id: int) -> Optional[Dict[str, Any]]:
        db = get_db()
        row = db.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
        if not row:
            return None
        p = dict(row)
        if p.get('brief_json'):
            try:
                p['brief'] = json.loads(p['brief_json'])
            except Exception:
                p['brief'] = None
        else:
            p['brief'] = None

        # Fetch associated sources
        src_rows = db.execute("SELECT * FROM project_sources WHERE project_id = ? ORDER BY created_at DESC", (project_id,)).fetchall()
        p['sources'] = [dict(s) for s in src_rows]
        return p

    @staticmethod
    def create_project(name: str, description: str, website_url: Optional[str] = None, repository_url: Optional[str] = None) -> Dict[str, Any]:
        name = (name or '').strip()
        description = (description or '').strip()
        website_url = (website_url or '').strip() or None
        repository_url = (repository_url or '').strip() or None

        if not name or not description:
            raise ValueError("Project name and description are required.")
        if len(name) > 120:
            raise ValueError("Project name must be 120 characters or fewer.")
        if len(description) > 5000:
            raise ValueError("Description must be 5000 characters or fewer.")

        db = get_db()
        cur = db.execute(
            "INSERT INTO projects (name, description, website_url, repository_url) VALUES (?, ?, ?, ?)",
            (name, description, website_url, repository_url)
        )
        project_id = cur.lastrowid
        db.execute(
            "INSERT INTO audit_events (entity_type, entity_id, action, details) VALUES (?, ?, ?, ?)",
            ('project', project_id, 'created', f'Created project: {name}')
        )
        db.commit()

        # If repo or website provided, trigger initial async-safe extraction
        if repository_url and 'github.com' in repository_url:
            try:
                ProjectService.fetch_github_readme(project_id, repository_url)
            except Exception as e:
                log.info(f"Initial GitHub fetch skipped or failed: {e}")

        # Generate initial project brief automatically
        try:
            ProjectService.generate_project_brief(project_id)
        except Exception as e:
            log.warning(f"Initial brief generation failed: {e}")

        return ProjectService.get_project_by_id(project_id)

    @staticmethod
    def add_uploaded_file(project_id: int, filename: str, content: str) -> Dict[str, Any]:
        if not is_allowed_file(filename):
            raise ValueError("Only markdown (.md, .markdown) or text (.txt, .rst) files are allowed.")
        
        sanitized_content = sanitize_text(content, max_chars=50000)
        if not sanitized_content:
            raise ValueError("Uploaded file content cannot be empty.")

        db = get_db()
        cur = db.execute(
            "INSERT INTO project_sources (project_id, source_type, file_name, content) VALUES (?, ?, ?, ?)",
            (project_id, 'file_upload', filename[:120], sanitized_content)
        )
        source_id = cur.lastrowid
        db.execute(
            "INSERT INTO audit_events (entity_type, entity_id, action, details) VALUES (?, ?, ?, ?)",
            ('project_source', source_id, 'uploaded_file', f"Uploaded file: {filename}")
        )
        db.commit()

        # Update brief with new source
        ProjectService.generate_project_brief(project_id)
        return {"id": source_id, "file_name": filename, "source_type": "file_upload"}

    @staticmethod
    def fetch_github_readme(project_id: int, github_url: str) -> Dict[str, Any]:
        """Fetches README from public GitHub repository without requiring authentication."""
        safe, reason = is_safe_url(github_url)
        if not safe:
            raise ValueError(f"Invalid repository URL: {reason}")

        # Parse owner and repo from https://github.com/owner/repo
        match = re.search(r'github\.com/([^/]+)/([^/#?]+)', github_url)
        if not match:
            raise ValueError("URL is not a recognized GitHub repository format (https://github.com/owner/repo).")
            
        owner, repo = match.group(1), match.group(2).rstrip('.git')
        
        # Try raw.githubusercontent.com for HEAD, main, and master
        branches = ['HEAD', 'main', 'master']
        readme_content = None
        fetched_branch = None

        for branch in branches:
            raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/README.md"
            safe_raw, _ = is_safe_url(raw_url)
            if not safe_raw:
                continue

            try:
                req = urllib.request.Request(
                    raw_url,
                    headers={'User-Agent': 'Project-to-Reach-Bot'}
                )
                with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
                    if resp.status == 200:
                        raw_data = resp.read(MAX_REMOTE_FETCH_SIZE).decode('utf-8', errors='replace')
                        readme_content = sanitize_text(raw_data, max_chars=30000)
                        fetched_branch = branch
                        break
            except Exception:
                continue

        if not readme_content:
            raise ValueError(f"Could not retrieve public README.md from GitHub repository '{owner}/{repo}'. Ensure repository is public.")

        db = get_db()
        cur = db.execute(
            "INSERT INTO project_sources (project_id, source_type, source_url, file_name, content) VALUES (?, ?, ?, ?, ?)",
            (project_id, 'github_readme', github_url, f"README.md ({fetched_branch})", readme_content)
        )
        source_id = cur.lastrowid
        db.execute(
            "INSERT INTO audit_events (entity_type, entity_id, action, details) VALUES (?, ?, ?, ?)",
            ('project_source', source_id, 'github_readme_fetched', f"Fetched README from {github_url}")
        )
        db.commit()

        # Refresh project brief
        ProjectService.generate_project_brief(project_id)
        return {
            "id": source_id,
            "source_type": "github_readme",
            "file_name": f"README.md ({fetched_branch})",
            "preview": readme_content[:200]
        }

    @staticmethod
    def generate_project_brief(project_id: int) -> Dict[str, Any]:
        """Analyzes all available project inputs and creates a normalized brief."""
        db = get_db()
        project = db.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
        if not project:
            raise ValueError("Project not found.")

        sources = db.execute("SELECT * FROM project_sources WHERE project_id = ?", (project_id,)).fetchall()
        source_dicts = [dict(s) for s in sources]

        provider = get_ai_provider()
        brief_data = provider.analyze_project(dict(project), source_dicts)

        db.execute(
            "UPDATE projects SET brief_json = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (json.dumps(brief_data), project_id)
        )
        db.execute(
            "INSERT INTO audit_events (entity_type, entity_id, action, details) VALUES (?, ?, ?, ?)",
            ('project', project_id, 'brief_analyzed', f"Generated normalized brief using {provider.__class__.__name__}")
        )
        db.commit()
        return brief_data
