"""
In-Memory Artifact Downloader and Extractor.

Downloads ZIP artifact payloads from GitHub Actions workflow runs and unpacks `ast.json`
and `codeql_structural.json` directly into RAM via byte streams (`io.BytesIO`).
"""

import io
import zipfile
import json
from typing import Dict, Any, List
from core.github_client import GitHubClient

class ArtifactDownloader:
    """
    Handles downloading and extracting workflow ZIP artifacts in memory without writing to disk.
    """

    def __init__(self, client: GitHubClient):
        """Initializes the ArtifactDownloader with a GitHubClient instance."""
        self.client = client

    def fetch_artifacts(self, owner: str, repo: str, run_id: int) -> Dict[str, Any]:
        """
        Downloads and extracts AST and CodeQL structural JSON artifacts for a specific run ID.

        Args:
            owner (str): Repository owner.
            repo (str): Repository name.
            run_id (int): GitHub Actions run ID.

        Returns:
            Dict[str, Any]: Dictionary containing extracted 'ast' and 'structural' JSON data.
        """
        print(f"Fetching artifacts for run {run_id}...")

        artifacts_info = self.client.get_run_artifacts(owner, repo, run_id)
        
        ast_data = {}
        structural_data = {}

        for artifact in artifacts_info.get("artifacts", []):
            name = artifact["name"]
            if name == "ast-results":
                print("  Downloading AST artifact...")
                zip_bytes = self.client.download_artifact(owner, repo, artifact["id"])
                ast_data = self._extract_json_from_zip(zip_bytes, "ast.json")
            elif name == "codeql-structural":
                print("  Downloading CodeQL structural artifact...")
                zip_bytes = self.client.download_artifact(owner, repo, artifact["id"])
                structural_data = self._extract_json_from_zip(zip_bytes, "codeql_structural.json")
                
        return {
            "ast": ast_data,
            "structural": structural_data
        }

    def _extract_json_from_zip(self, zip_bytes: bytes, filename: str) -> Dict:
        try:
            with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
                if filename in z.namelist():
                    with z.open(filename) as f:
                        return json.load(f)
        except Exception as e:
            print(f"  Error extracting {filename}: {e}")
        return {}
