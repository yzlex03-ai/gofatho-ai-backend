#!/usr/bin/env python3
"""
Gofatho AI — Phase 5B: 1-Click Automated Hugging Face Spaces Cloud Deployer
===========================================================================
Creates or updates a free 16 GB RAM Docker Space on Hugging Face Spaces
(`https://<username>-gofatho-ai.hf.space`), uploads the complete FastAPI v3.1
server + `gofatho_ai_master.sqlite` database + `Dockerfile`, and optionally
injects `GEMINI_API_KEY` into the Space's encrypted secrets.
"""

import os
import shutil
import tempfile
import argparse
from typing import Optional


def deploy_gofatho_to_hf_space(
    hf_token: str,
    repo_root: str,
    space_name: str = "gofatho-ai",
    gemini_api_key: Optional[str] = None,
) -> str:
    from huggingface_hub import HfApi

    api = HfApi(token=hf_token.strip())
    user_info = api.whoami()
    username = user_info["name"]
    repo_id = f"{username}/{space_name}"
    live_url = f"https://{username.lower()}-{space_name.lower()}.hf.space"

    print(f"[1/4] Creating / verifying Docker Space: https://huggingface.co/spaces/{repo_id} ...")
    api.create_repo(
        repo_id=repo_id,
        repo_type="space",
        space_sdk="docker", space_hardware="cpu-basic",
        private=False,
        exist_ok=True,
    )

    if gemini_api_key and len(gemini_api_key.strip()) >= 10:
        print("[2/4] Setting encrypted Space Secret GEMINI_API_KEY...")
        api.add_space_secret(repo_id=repo_id, key="GEMINI_API_KEY", value=gemini_api_key.strip())
    else:
        print("[2/4] No default GEMINI_API_KEY passed (users can pass their own key in the app or add it in Space Settings).")

    with tempfile.TemporaryDirectory() as stage_dir:
        # Copy README with Hugging Face YAML frontmatter
        hf_readme = os.path.join(repo_root, "HuggingFace_Space_README.md")
        if os.path.exists(hf_readme):
            shutil.copy(hf_readme, os.path.join(stage_dir, "README.md"))
        shutil.copy(os.path.join(repo_root, "Dockerfile"), os.path.join(stage_dir, "Dockerfile"))
        shutil.copytree(os.path.join(repo_root, "backend"), os.path.join(stage_dir, "backend"))
        os.makedirs(os.path.join(stage_dir, "data"), exist_ok=True)

        db_src = os.path.join(repo_root, "data/gofatho_ai_master.sqlite")
        if not os.path.exists(db_src):
            db_src = os.path.join(repo_root, "flutter_app/assets/gofatho_ai_master.sqlite")
        shutil.copy(db_src, os.path.join(stage_dir, "data/gofatho_ai_master.sqlite"))

        print(f"[3/4] Uploading FastAPI v3.1 + gofatho_ai_master.sqlite to {repo_id}...")
        api.upload_folder(
            folder_path=stage_dir,
            repo_id=repo_id,
            repo_type="space",
            commit_message="Deploy Gofatho AI Hybrid RAG + Gemini 2.5 Flash + Gemination v3.1 Server",
        )

    print(f"[4/4] Deployment triggered! Live HTTPS API endpoint: {live_url}")
    print(f"      Health check URL: {live_url}/api/v1/health")
    print(f"      Interactive Swagger Docs: {live_url}/docs")
    return live_url


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="1-Click Deploy Gofatho AI to Hugging Face Spaces")
    parser.add_argument("--hf-token", required=True, help="Hugging Face Write Token (hf_...)")
    parser.add_argument("--repo-root", default="..", help="Path to Gofatho AI repository root")
    parser.add_argument("--space-name", default="gofatho-ai", help="Space name on Hugging Face")
    parser.add_argument("--gemini-key", default="", help="Optional Google AI Studio Gemini API Key")
    args = parser.parse_args()
    deploy_gofatho_to_hf_space(
        hf_token=args.hf_token,
        repo_root=args.repo_root,
        space_name=args.space_name,
        gemini_api_key=args.gemini_key,
    )
