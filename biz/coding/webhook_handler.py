import os
import re
import time
from datetime import datetime
from urllib.parse import urljoin, urlparse
import fnmatch
import requests
import traceback

from biz.utils.log import logger
from biz.entity.review_entity import MergeRequestReviewEntity, PushReviewEntity
from biz.service.review_service import ReviewService
from biz.utils.code_reviewer import CodeReviewer
from biz.event.event_manager import event_manager

def filter_changes(changes: list):
    '''
    过滤数据，只保留支持的文件类型以及必要的字段信息
    '''
    supported_extensions = os.getenv('SUPPORTED_EXTENSIONS', '.java,.py,.php').split(',')

    filter_deleted_files_changes = [change for change in changes if not change.get("deleted_file")]

    filtered_changes = [
        {
            'diff': item.get('diff', ''),
            'new_path': item['new_path'],
            'additions': item.get('additions', 0),
            'deletions': item.get('deletions', 0),
        }
        for item in filter_deleted_files_changes
        if any(item.get('new_path', '').endswith(ext) for ext in supported_extensions)
    ]
    logger.info(f"After filtering by extension: {filtered_changes}")
    return filtered_changes

def slugify_url(original_url: str) -> str:
    """
    将原始URL转换为适合作为文件名的字符串，其中非字母或数字的字符会被替换为下划线，举例：
    slugify_url("http://example.com/path/to/repo/") => example_com_path_to_repo
    slugify_url("https://coding.net/user/repo.git") => coding_net_user_repo_git
    """
    original_url = re.sub(r'^https?://', '', original_url)
    target = re.sub(r'[^a-zA-Z0-9]', '_', original_url)
    target = target.rstrip('_')
    return target

def _get_diff_content_from_url(diff_url: str, token: str) -> str:
    """
    通过 URL 获取差异内容。
    """
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3.diff" # 某些平台可能需要特定的Accept头
    }
    try:
        response = requests.get(diff_url, headers=headers)
        response.raise_for_status() # 如果请求失败，抛出HTTPError
        return response.text
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to get diff from URL {diff_url}: {e}")
        raise



def handle_coding_pull_request_event(data: dict, coding_token: str, coding_url: str, coding_url_slug: str):
    logger.info(f"Handling Coding Pull Request event for URL: {coding_url}")

    try:
        # 提取关键信息
        project_name = data.get("repository", {}).get("name")
        repo_id = data.get("repository", {}).get("id")
        pull_request_id = data.get("mergeRequest", {}).get("number")
        title = data.get("mergeRequest", {}).get("title")
        description = data.get("mergeRequest", {}).get("body")
        source_branch = data.get("mergeRequest", {}).get("head", {}).get("ref")
        target_branch = data.get("mergeRequest", {}).get("base", {}).get("ref")
        author_name = data.get("mergeRequest", {}).get("user", {}).get("name")
        author_email = data.get("mergeRequest", {}).get("user", {}).get("email") # pull_request.json中没有email字段，可能为None
        web_url = data.get("mergeRequest", {}).get("html_url")
        diff_url = data.get("mergeRequest", {}).get("diff_url")
        action = data.get("action") # 从顶层获取action

        if not diff_url:
            logger.error("Missing diff_url in Coding PR payload.")
            return

        # 检查action是否为'create'或'update'
        if action not in ['create', 'update', 'synchronize']:
            logger.info(f"Coding Pull Request event, action={action}, ignored.")
            return

        # 检查last_commit_id是否已经存在，如果存在则跳过处理
        last_commit_id = data.get("mergeRequest", {}).get("merge_commit_sha", '') # 使用merge_commit_sha作为last_commit_id
        if last_commit_id:
            if ReviewService.check_mr_last_commit_id_exists(project_name, source_branch, target_branch, last_commit_id):
                logger.info(f"Merge Request with last_commit_id {last_commit_id} already exists, skipping review for {project_name}.")
                return

        diff_content = _get_diff_content_from_url(diff_url, coding_token)

        # 统计本次新增、删除的代码总数
        additions = data.get("mergeRequest", {}).get("additions", 0)
        deletions = data.get("mergeRequest", {}).get("deletions", 0)

        # review 代码
        # 对于commits_text，暂时使用title，因为pull_request.json示例未提供提交消息列表
        commits_text = title
        review_result = CodeReviewer().review_and_strip_code(diff_content, commits_text)
        commits = [{
            'message': commits_text,
            'author': author_name,
            'email': author_email,
        }]
        # 构造 MergeRequestReviewEntity
        entity = MergeRequestReviewEntity(
                project_name=project_name,
                author=author_name,
                source_branch=source_branch,
                target_branch=target_branch,
                updated_at=int(datetime.now().timestamp()),
                commits=commits,
                score=CodeReviewer.parse_review_score(review_text=review_result),
                url=web_url,
                review_result=review_result,
                url_slug=coding_url_slug,
                webhook_data=data,
                additions=additions,
                deletions=deletions,
                last_commit_id=last_commit_id,
            )
        # 触发事件
        # dispatch merge_request_reviewed event
        event_manager['merge_request_reviewed'].send(entity)
        logger.info(f"Coding Pull Request event {pull_request_id} triggered for review.")

    except Exception as e:
        error_message = f"AI Code Review 服务出现未知错误: {str(e)} \n{traceback.format_exc()}"
        # notifier.send_notification(content=error_message) # 如果需要通知，可以取消注释
        logger.error(f"Error processing Coding PR {pull_request_id}: {error_message}")
        return

def handle_coding_push_event(data: dict, coding_token: str, coding_url: str, coding_url_slug: str):
    logger.info(f"Handling Coding Push event for URL: {coding_url}")

    push_review_enabled = os.environ.get('PUSH_REVIEW_ENABLED', '0') == '1'

    try:
        # 提取关键信息
        project_name = data.get("repository", {}).get("name")
        repo_id = data.get("repository", {}).get("id")
        after_sha = data.get("after")
        before_sha = data.get("before")
        ref = data.get("ref")
        branch_name = ref.split('/')[-1]
        pusher_name = data.get("pusher", {}).get("name")
        pusher_email = data.get("pusher", {}).get("email")
        web_url = data.get("repository", {}).get("web_url")

        if not push_review_enabled:
            logger.info("Push review is disabled, ignoring push event.")
            return

        # 获取 commit 列表和 diff
        commits = data.get("commits", [])
        all_diff_content = ""
        commits_text = ';'.join(commit['message'] for commit in commits) # 提取所有commit的message

        # 假设我们通过比较 before_sha 和 after_sha 来获取整个 push 的 diff
        # 这需要调用 Coding 的 Compare API
        compare_url = f"{coding_url}/api/v3/projects/{project_name}/git/repositories/{repo_id}/compare/{before_sha}...{after_sha}"
        headers = {"Authorization": f"token {coding_token}"}
        try:
            compare_response = requests.get(compare_url, headers=headers)
            compare_response.raise_for_status()
            compare_data = compare_response.json()
            # 假设 compare_data 中包含 diff 信息，例如 files 列表，每个文件有 patch 字段
            for file_change in compare_data.get("files", []):
                if file_change.get("patch"):
                    all_diff_content += file_change["patch"] + "\n"
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get diff for Coding push {before_sha}...{after_sha}: {e}")
            return

        # review 代码
        review_result = CodeReviewer().review_and_strip_code(all_diff_content, commits_text)

        # 构造 PushReviewEntity
        entity = PushReviewEntity(
            repo_id=str(repo_id),
            branch=branch_name,
            after_sha=after_sha,
            before_sha=before_sha,
            pusher_name=pusher_name,
            pusher_email=pusher_email,
            diff_content=all_diff_content,
            web_url=web_url,
            platform="coding",
            platform_url=coding_url,
            platform_url_slug=coding_url_slug,
            token=coding_token,
            review_result=review_result,
            score=CodeReviewer.parse_review_score(review_text=review_result),
            updated_at=int(datetime.now().timestamp()),
            commits=commits
        )

        # 触发事件
        event_manager['push_reviewed'].send(entity)
        logger.info(f"Coding Push event for {branch_name} triggered for review.")

    except Exception as e:
        error_message = f"AI Code Review 服务出现未知错误: {str(e)}\n{traceback.format_exc()}"
        # notifier.send_notification(content=error_message) # 如果需要通知，可以取消注释
        logger.error(f"Error processing Coding Push event: {error_message}")
        return