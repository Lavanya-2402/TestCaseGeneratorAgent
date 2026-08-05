#!/usr/bin/env python3
"""
GitHub API client with rate limit handling and retry logic.
"""
import time
import requests
from typing import Dict, Optional


class GitHubClient:
    """
    HTTP Client wrapper for the GitHub REST API (v2022-11-28).

    Handles authentication via Personal Access Token (PAT), automatic rate limit retries (429 handling),
    repository content management, workflow dispatches, commit comparisons, and artifact downloads.
    """

    BASE_URL = "https://api.github.com"

    def __init__(self, pat: str):
        """
        Initializes the GitHub Client with a Personal Access Token.

        Args:
            pat (str): GitHub Personal Access Token (PAT).
        """
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {pat}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        })

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        """Internal HTTP request wrapper with automatic 429 rate limit backoff."""
        url = f"{self.BASE_URL}{path}"
        response = self.session.request(method, url, **kwargs)

        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 60))
            print(f"  Rate limited — waiting {retry_after}s...")
            time.sleep(retry_after)
            return self._request(method, path, **kwargs)

        return response

    def get(self, path: str, params: Dict = None) -> Dict:
        """Performs a GET request against the GitHub API and returns parsed JSON data."""
        r = self._request("GET", path, params=params)
        r.raise_for_status()
        return r.json()

    def post(self, path: str, json: Dict = None) -> requests.Response:
        """Performs a POST request against the GitHub API and returns raw HTTP Response."""
        return self._request("POST", path, json=json)

    def put(self, path: str, json: Dict = None) -> Dict:
        """Performs a PUT request against the GitHub API and returns parsed JSON data."""
        r = self._request("PUT", path, json=json)
        r.raise_for_status()
        return r.json()

    def download_zip(self, path: str) -> bytes:
        """
        Downloads a binary ZIP file artifact from GitHub, following HTTP redirects.

        Args:
            path (str): Relative API path to the ZIP resource.

        Returns:
            bytes: Raw binary content of the downloaded ZIP archive.
        """
        url = f"{self.BASE_URL}{path}"
        r = self.session.get(url, allow_redirects=True)
        r.raise_for_status()
        return r.content

    # ── Repo ──────────────────────────────────────────────

    def get_repo(self, owner: str, repo: str) -> Dict:
        """Fetches metadata for a specified repository."""
        return self.get(f"/repos/{owner}/{repo}")

    def get_languages(self, owner: str, repo: str) -> Dict:
        """Fetches the programming language breakdown for a repository."""
        return self.get(f"/repos/{owner}/{repo}/languages")

    def get_latest_commit(self, owner: str, repo: str, branch: str = "main") -> str:
        """
        Fetches the latest commit SHA for a specified branch.

        Args:
            owner (str): Repository owner.
            repo (str): Repository name.
            branch (str): Target branch (default: "main").

        Returns:
            str: Full SHA string of the latest commit.
        """
        data = self.get(f"/repos/{owner}/{repo}/commits/{branch}")
        return data["sha"]

    def compare_commits(self, owner: str, repo: str, base_sha: str, head_sha: str) -> list:
        """
        Compares two commits and returns a list of file paths added, modified, or renamed.

        Args:
            owner (str): Repository owner.
            repo (str): Repository name.
            base_sha (str): Base commit SHA.
            head_sha (str): Target commit SHA.

        Returns:
            list: List of changed relative file paths.
        """
        data = self.get(f"/repos/{owner}/{repo}/compare/{base_sha}...{head_sha}")
        changed_files = []
        for file in data.get("files", []):
            if file.get("status") in ["added", "modified", "renamed"]:
                changed_files.append(file["filename"])
        return changed_files

    def get_file(self, owner: str, repo: str, path: str) -> Optional[Dict]:
        """Fetches file metadata and content from a target repository path, or None if missing."""
        try:
            return self.get(f"/repos/{owner}/{repo}/contents/{path}")
        except Exception:
            return None

    def commit_file(self, owner: str, repo: str, path: str,
                    content_b64: str, message: str,
                    sha: Optional[str] = None) -> Dict:
        """
        Creates or updates a file in a remote repository via Git commit.

        Args:
            owner (str): Repository owner.
            repo (str): Repository name.
            path (str): Target relative file path in repository.
            content_b64 (str): Base64 encoded file content.
            message (str): Commit message.
            sha (str, optional): Existing file SHA (required if updating).

        Returns:
            Dict: API response containing commit metadata.
        """
        body = {"message": message, "content": content_b64}
        if sha:
            body["sha"] = sha
        return self.put(f"/repos/{owner}/{repo}/contents/{path}", json=body)

    # ── Actions ───────────────────────────────────────────

    def trigger_workflow(self, owner: str, repo: str,
                         workflow_file: str, ref: str,
                         inputs: Dict = None) -> bool:
        """
        Dispatches a manual GitHub Actions workflow (`workflow_dispatch`).

        Returns:
            bool: True if trigger accepted (HTTP 204), False otherwise.
        """
        body = {"ref": ref}
        if inputs:
            body["inputs"] = inputs
        r = self.post(
            f"/repos/{owner}/{repo}/actions/workflows/{workflow_file}/dispatches",
            json=body,
        )
        return r.status_code == 204

    def get_workflow_runs(self, owner: str, repo: str,
                          event: str = None) -> Dict:
        """Fetches workflow runs for a repository, optionally filtered by event type."""
        params = {}
        if event:
            params["event"] = event
        return self.get(f"/repos/{owner}/{repo}/actions/runs", params=params)

    def get_run(self, owner: str, repo: str, run_id: int) -> Dict:
        """Fetches detailed status of a specific GitHub Actions workflow run."""
        return self.get(f"/repos/{owner}/{repo}/actions/runs/{run_id}")

    def get_run_artifacts(self, owner: str, repo: str, run_id: int) -> Dict:
        """Fetches the list of generated artifacts for a workflow run."""
        return self.get(f"/repos/{owner}/{repo}/actions/runs/{run_id}/artifacts")

    def download_artifact(self, owner: str, repo: str,
                          artifact_id: int) -> bytes:
        """Downloads the raw ZIP byte payload for a workflow artifact."""
        return self.download_zip(
            f"/repos/{owner}/{repo}/actions/artifacts/{artifact_id}/zip"
        )

