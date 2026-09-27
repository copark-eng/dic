# -*- coding: utf-8 -*-
from __future__ import annotations
"""
설정 파일 (Configuration)
단어 데이터 구축 파이프라인의 경로, API 설정, 레벨 메타데이터 정의
Python 3.10+ 호환, UTF-8 인코딩 적용
"""

import os
import sys
from pathlib import Path

# Windows Anaconda 환경에서 SSL DLL(libssl, libcrypto) 로드 실패 방지
if sys.platform == "win32":
    _anaconda_lib_bin = Path(sys.prefix) / "Library" / "bin"
    if _anaconda_lib_bin.exists():
        os.environ["PATH"] = f"{_anaconda_lib_bin};{os.environ.get('PATH', '')}"
        if hasattr(os, "add_dll_directory"):
            try:
                os.add_dll_directory(str(_anaconda_lib_bin))
            except Exception:
                pass

# 기본 디렉터리 경로 설정
SCRIPTS_DIR = Path(__file__).resolve().parent
SERVER_DIR = SCRIPTS_DIR.parent
RAW_DIR = SERVER_DIR / "raw"
DATA_DIR = SERVER_DIR / "data"
CACHE_DIR = SERVER_DIR / ".cache"

# Free Dictionary API 설정
API_BASE_URL = "https://api.dictionaryapi.dev/api/v2/entries/en"
REQUEST_TIMEOUT = 3        # 초 단위 (지연 시 빠른 Fallback)
REQUEST_DELAY = 0.1        # 요청 간 대기 시간 (초 단위)
MAX_RETRIES = 2            # 실패 시 최대 재시도 횟수
BACKOFF_FACTOR = 1.2       # 지수 백오프 배수

# 레벨별 메타데이터 (Level 1 ~ 7)
LEVEL_INFO = {
    1: {"name": "기초", "target_count": 1000, "code": "L1"},
    2: {"name": "중등", "target_count": 2000, "code": "L2"},
    3: {"name": "수능기본", "target_count": 3000, "code": "L3"},
    4: {"name": "수능심화", "target_count": 4500, "code": "L4"},
    5: {"name": "TOEIC 750", "target_count": 4000, "code": "L5"},
    6: {"name": "TOEIC 900", "target_count": 5500, "code": "L6"},
    7: {"name": "TOEIC 990", "target_count": 6500, "code": "L7"},
}
