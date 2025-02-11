import json
from typing import Any
import requests
from modules.logger import Logger
from modules.config_store import ConfigStore


def get_config_value(key: str, default: Any = None) -> Any:
    """Get a config value from the ConfigStore singleton."""
    return ConfigStore().get(key, default)

def get_raw_http(response: requests.Response) -> tuple[str, str]:
    """Format raw HTTP request and response.

    Returns:
        tuple[str, str]: (formatted request, formatted response)
    """
    request = response.request
    http_version = "HTTP/2.0" if response.raw.version == 2 else "HTTP/1.1"

    def format_headers(headers):
        if response.raw.version == 2:
            pseudo = {k: v for k, v in headers.items() if k.startswith(':')}
            regular = {k: v for k, v in headers.items() if not k.startswith(':')}
            return '\n'.join(
                [f'{k}: {v}' for k, v in pseudo.items()] +
                [f'{k}: {v}' for k, v in regular.items()]
            )
        return '\n'.join(f'{k}: {v}' for k, v in headers.items())

    raw_request = (
        f"{request.method} {request.url} {http_version}\n"
        f"{format_headers(request.headers)}\n"
        f"\n{request.body.decode() if request.body else ''}"
    )

    raw_response = (
        f"{http_version} {response.status_code}\n"
        f"{format_headers(response.headers)}\n"
        f"\n{response.text}"
    )

    return raw_request, raw_response
