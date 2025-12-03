from typing import Dict, Any
from urllib.parse import urlparse
import re
import os

from biz.gitlab.webhook_handler import filter_changes as gitlab_filter_changes, slugify_url
from biz.github.webhook_handler import filter_changes as github_filter_changes
from biz.gitea.webhook_handler import filter_changes as gitea_filter_changes

# 定义一个通用的事件结构，方便后续处理
class WebhookEvent:
    def __init__(self, provider: str, event_type: str, payload: Dict[str, Any], token: str, url: str, url_slug: str):
        self.provider = provider
        self.event_type = event_type
        self.payload = payload
        self.token = token
        self.url = url
        self.url_slug = url_slug


def gitlab_parser(data: Dict[str, Any], token: str, gitlab_url: str) -> WebhookEvent:
    object_kind = data.get("object_kind")

    if not gitlab_url:
        repository = data.get('repository')
        if not repository:
            raise ValueError('Missing GitLab URL')
        homepage = repository.get("homepage")
        if not homepage:
            raise ValueError('Missing GitLab URL')
        try:
            parsed_url = urlparse(homepage)
            gitlab_url = f"{parsed_url.scheme}://{parsed_url.netloc}/"
        except Exception as e:
            raise ValueError(f"Failed to parse homepage URL: {str(e)}")

    gitlab_url_slug = slugify_url(gitlab_url)

    return WebhookEvent("gitlab", object_kind, data, token, gitlab_url, gitlab_url_slug)


def github_parser(data: Dict[str, Any], token: str, github_url: str, event_type: str) -> WebhookEvent:
    if not github_url:
        github_url = os.getenv('GITHUB_URL') or 'https://github.com'

    github_url_slug = slugify_url(github_url)

    return WebhookEvent("github", event_type, data, token, github_url, github_url_slug)


def gitea_parser(data: Dict[str, Any], token: str, gitea_url: str, event_type: str) -> WebhookEvent:
    if not gitea_url:
        gitea_url = os.getenv('GITEA_URL') or 'https://gitea.com'

    gitea_url_slug = slugify_url(gitea_url)

    return WebhookEvent("gitea", event_type, data, token, gitea_url, gitea_url_slug)


def coding_parser(data: Dict[str, Any], token: str, coding_url: str, event_type: str) -> WebhookEvent:
    # Coding 的 URL 可能需要从 payload 中提取，或者从环境变量中获取
    if not coding_url:
        # 尝试从 payload 中获取项目 URL，这取决于 Coding webhook 的具体结构
        # 假设 Coding 的 push 事件 payload 中有 repository.web_url
        repository_url = data.get("repository", {}).get("html_url")
        if repository_url:
            parsed_url = urlparse(repository_url)
            coding_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        else:
            coding_url = os.getenv('CODING_URL') or 'https://coding.net' # 默认值

    coding_url_slug = slugify_url(coding_url)

    return WebhookEvent("coding", event_type, data, token, coding_url, coding_url_slug)
