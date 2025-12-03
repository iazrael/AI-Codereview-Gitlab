import json
import os
from typing import Dict, Any, Optional, List

class GitProviderManager:
    def __init__(self, config_path="conf/git_providers.json"):
        self.config_path = config_path
        self.providers_config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        if not os.path.exists(self.config_path):
            return {"providers": []}
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def get_provider_config(self, provider_name: str) -> Optional[Dict[str, Any]]:
        for provider in self.providers_config.get("providers", []):
            if provider["name"] == provider_name:
                return provider
        return None

    def identify_provider(self, headers: Dict[str, str]) -> Optional[Dict[str, Any]]:
        # 打印一下 headers
        print(f"headers: {headers}")
        for provider_config in self.providers_config.get("providers", []):
            identification_rules = provider_config.get("identification", {})
            headers_rules = identification_rules.get("headers", {})

            # Check if all header rules match
            match = True
            for header_name, expected_values in headers_rules.items():
                actual_value = headers.get(header_name)
                if not actual_value or actual_value not in expected_values:
                    match = False
                    break
            if match:
                return provider_config
        # 默认返回 gitlab 的 配置
        return self.get_provider_config("gitlab")

    def get_access_token(self, provider_config: Dict[str, Any], request_headers: Dict[str, str]) -> Optional[str]:
        credentials_config = provider_config.get("credentials", {})
        cred_type = credentials_config.get("type")
        cred_key = credentials_config.get("key")

        if cred_type == "env" and cred_key:
            return os.getenv(cred_key)
        # Add other credential types (e.g., from request headers, payload) here if needed
        return None

    def get_payload_parser_path(self, provider_config: Dict[str, Any]) -> Optional[str]:
        return provider_config.get("payload_parser")

    def get_event_mapping(self, provider_config: Dict[str, Any], provider_event_type: str) -> Optional[str]:
        event_mapping = provider_config.get("event_mapping", {})
        return event_mapping.get(provider_event_type)
