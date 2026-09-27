# -*- coding: utf-8 -*-
from __future__ import annotations
"""
Dictionary API 연동 클라이언트 (API Client)
api.dictionaryapi.dev 호출, 재시도, Rate Limit 대기 및 에러 핸들링
Python 3.10+ 호환, UTF-8 인코딩 적용
"""

import json
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Optional

from config import (
    API_BASE_URL,
    BACKOFF_FACTOR,
    MAX_RETRIES,
    REQUEST_DELAY,
    REQUEST_TIMEOUT,
)


class DictionaryApiClient:
    """api.dictionaryapi.dev 와 통신하는 REST 클라이언트"""

    def __init__(self) -> None:
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json",
        }

    def fetch_word(self, word: str) -> Optional[list[dict[str, Any]]]:
        """
        단어 정보를 API에서 조회합니다.
        
        :param word: 조회할 영어 단어 (공백 및 특수문자 인코딩 처리)
        :return: API 응답 JSON 리스트 또는 단어가 없을 경우(404) None
        """
        encoded_word = urllib.parse.quote(word.strip().lower())
        url = f"{API_BASE_URL}/{encoded_word}"

        delay = REQUEST_DELAY
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                # Rate limit 방지를 위한 요청 전 딜레이
                time.sleep(REQUEST_DELAY)

                req = urllib.request.Request(url, headers=self.headers, method="GET")
                with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as response:
                    if response.status == 200:
                        raw_data = response.read().decode("utf-8")
                        return json.loads(raw_data)

            except urllib.error.HTTPError as e:
                if e.code == 404:
                    # 단어가 사전에 등록되어 있지 않은 경우 정상 Fallback
                    return None
                elif e.code == 429:
                    # Too Many Requests: 백오프 시간 대기 후 재시도
                    wait_time = delay * (BACKOFF_FACTOR ** attempt) * 2
                    print(f"  [API 429] 일시적 요청 제한 감지. {wait_time:.1f}초 대기... ({attempt}/{MAX_RETRIES})")
                    time.sleep(wait_time)
                else:
                    print(f"  [HTTP {e.code}] {word}: {e.reason}")
                    return None

            except (urllib.error.URLError, TimeoutError, socket.timeout, Exception) as e:
                # 타임아웃 또는 네트워크 단절 시 예외 출력 후 재시도
                err_msg = str(e) if str(e) else type(e).__name__
                if attempt < MAX_RETRIES:
                    time.sleep(delay)
                else:
                    print(f" (네트워크 미응답/Fallback 적용: {err_msg})", end="")

            delay *= BACKOFF_FACTOR

        return None
