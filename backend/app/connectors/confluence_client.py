from __future__ import annotations

import html
import re
from typing import Any

import httpx


class ConfluenceClient:
    def __init__(self, *, base_url: str, token: str, auth_type: str = 'bearer', timeout: int = 60) -> None:
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.auth_type = auth_type
        self.headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        }
        if auth_type == 'basic':
            self._auth = tuple(token.split(':', 1)) if ':' in token else (token, '')
        else:
            self._auth = None
            self.headers['Authorization'] = f'Bearer {token}'

    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        with httpx.Client(timeout=self.timeout, auth=self._auth) as client:
            response = client.request(method, f"{self.base_url}{path}", headers=self.headers, **kwargs)
            response.raise_for_status()
            return response

    def test_connection(self) -> dict[str, Any]:
        response = self._request('GET', '/wiki/api/v2/pages', params={'limit': 1})
        data = response.json()
        return {
            'results_count': len(data.get('results') or []),
            'base': (data.get('_links') or {}).get('base'),
        }

    def fetch_page(self, page_id: str) -> dict[str, Any]:
        response = self._request('GET', f'/wiki/api/v2/pages/{page_id}', params={'body-format': 'storage'})
        return response.json()

    def get_footer_comment(self, comment_id: str) -> dict[str, Any]:
        response = self._request('GET', f'/wiki/api/v2/footer-comments/{comment_id}', params={'body-format': 'storage'})
        return response.json()

    def create_comment(self, page_id: str, body: str) -> str:
        payload = {
            'pageId': str(page_id),
            'body': {
                'representation': 'storage',
                'value': self._markdown_to_storage(body),
            },
        }
        response = self._request('POST', '/wiki/api/v2/footer-comments', json=payload)
        data = response.json()
        return str(data['id'])

    def update_comment(self, page_id: str, comment_id: str, body: str) -> None:
        current = self.get_footer_comment(comment_id)
        current_version = ((current.get('version') or {}).get('number') or 1)
        payload = {
            'version': {'number': int(current_version) + 1},
            'body': {
                'representation': 'storage',
                'value': self._markdown_to_storage(body),
            },
        }
        self._request('PUT', f'/wiki/api/v2/footer-comments/{comment_id}', json=payload)

    def normalize_page(self, page_payload: dict[str, Any]) -> tuple[str | None, str, dict[str, Any]]:
        title = page_payload.get('title')
        body_storage = (((page_payload.get('body') or {}).get('storage') or {}).get('value')) or ''
        text_body = self._storage_to_text(body_storage)
        page_id = page_payload.get('id')
        status = page_payload.get('status')
        space_id = page_payload.get('spaceId')
        version_number = ((page_payload.get('version') or {}).get('number'))
        links = page_payload.get('_links') or {}
        webui = links.get('webui')

        normalized_text = '\n'.join([
            f'Page id: {page_id}' if page_id is not None else '',
            f'Title: {title}' if title else '',
            f'Status: {status}' if status else '',
            f'Space id: {space_id}' if space_id else '',
            f'Version: {version_number}' if version_number is not None else '',
            '',
            'Body:',
            text_body or '(empty)',
        ]).strip()

        metadata = {
            'page_id': page_id,
            'status': status,
            'space_id': space_id,
            'version_number': version_number,
            'webui': webui,
        }
        return title, normalized_text, metadata

    def _storage_to_text(self, value: str) -> str:
        if not value:
            return ''
        text = re.sub(r'<br\s*/?>', '\n', value, flags=re.IGNORECASE)
        text = re.sub(r'</(p|div|h1|h2|h3|h4|h5|h6|li|tr)>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'<[^>]+>', '', text)
        text = html.unescape(text)
        lines = [line.strip() for line in text.splitlines()]
        return '\n'.join(line for line in lines if line)

    def _markdown_to_storage(self, value: str) -> str:
        if not value.strip():
            return '<p>(empty)</p>'
        paragraphs = []
        for block in value.split('\n\n'):
            escaped = html.escape(block.strip())
            escaped = escaped.replace('\n', '<br/>')
            paragraphs.append(f'<p>{escaped}</p>')
        return ''.join(paragraphs)
