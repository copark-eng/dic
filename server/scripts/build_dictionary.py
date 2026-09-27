# -*- coding: utf-8 -*-
from __future__ import annotations
"""
단어장 빌더 메인 스크립트 (Build Dictionary)
1~7단계 원천 어휘 목록을 읽어 api.dictionaryapi.dev에서 정보를 수집하고,
표준 JSON 파일 및 manifest.json 메타데이터를 빌드합니다.
Python 3.9+ 호환, UTF-8 인코딩 적용
"""

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# 스크립트 디렉터리를 sys.path에 추가하여 어디서 실행하든 모듈을 찾을 수 있도록 보장
sys.path.insert(0, str(Path(__file__).resolve().parent))

from api_client import DictionaryApiClient
from config import CACHE_DIR, DATA_DIR, LEVEL_INFO, RAW_DIR
from word_parser import WordParser

# 초기 테스트 및 원천 파일 부재 시 활용 가능한 레벨별 시드(Seed) 샘플 어휘
SEED_WORDS: dict[int, list[tuple[str, str]]] = {
    1: [
        ("apple", "사과"),
        ("book", "책"),
        ("school", "학교"),
        ("happy", "행복한"),
        ("water", "물"),
    ],
    2: [
        ("achieve", "성취하다"),
        ("balance", "균형"),
        ("climate", "기후"),
        ("discover", "발견하다"),
        ("essential", "필수적인"),
    ],
    3: [
        ("adequate", "적절한, 충분한"),
        ("comprehend", "이해하다"),
        ("distinction", "구별, 특징"),
        ("fluctuate", "변동하다"),
        ("inevitable", "불가피한"),
    ],
    4: [
        ("ambiguity", "모호성"),
        ("deteriorate", "악화되다"),
        ("impetus", "자극, 추진력"),
        ("juxtapose", "병치하다"),
        ("scrutinize", "면밀히 조사하다"),
    ],
    5: [
        ("agenda", "의제, 안건"),
        ("budget", "예산"),
        ("commute", "통근하다"),
        ("deadline", "마감일"),
        ("invoice", "청구서, 송장"),
    ],
    6: [
        ("acquisition", "인수, 획득"),
        ("compliance", "준수, 순응"),
        ("feasibility", "실현 가능성"),
        ("reimburse", "변제하다, 환급하다"),
        ("yield", "산출하다, 수익"),
    ],
    7: [
        ("consolidate", "통합하다, 강화하다"),
        ("depreciation", "가치 하락, 감가상각"),
        ("indemnify", "배상하다, 보장하다"),
        ("liquidity", "유동성"),
        ("prerequisite", "전제 조건"),
    ],
}


def compute_sha256(filepath: Path) -> str:
    """파일의 SHA-256 해시를 계산합니다."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()


class DictionaryBuilder:
    """레벨별 단어 데이터를 수집 및 빌드하는 오케스트레이터"""

    def __init__(self, use_cache: bool = True) -> None:
        self.client = DictionaryApiClient()
        self.use_cache = use_cache

        # 디렉터리 준비
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        RAW_DIR.mkdir(parents=True, exist_ok=True)

    def _get_cache_path(self, word: str) -> Path:
        """단어별 로컬 캐시 파일 경로"""
        safe_name = "".join(c if c.isalnum() else "_" for c in word.lower())
        return CACHE_DIR / f"{safe_name}.json"

    def _load_from_cache(self, word: str) -> Optional[list[dict[str, Any]]]:
        """로컬 캐시에서 API 응답 읽기"""
        if not self.use_cache:
            return None
        cache_path = self._get_cache_path(word)
        if cache_path.exists():
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return None
        return None

    def _save_to_cache(self, word: str, data: Optional[list[dict[str, Any]]]) -> None:
        """API 응답을 로컬 캐시에 저장 (중단 시 이어받기 및 재호출 방지)"""
        cache_path = self._get_cache_path(word)
        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"  [캐시 저장 실패] {word}: {e}")

    def load_raw_words(self, level: int, sample_mode: bool = False) -> list[tuple[str, str]]:
        """
        raw 파일 또는 시드 데이터로부터 (단어, 한국어 뜻) 목록을 로드합니다.
        """
        raw_file = RAW_DIR / f"level_{level}_words.txt"

        if sample_mode or not raw_file.exists():
            print(f"  [안내] Level {level}: 시드 샘플 단어 사용 ({len(SEED_WORDS.get(level, []))}개)")
            # 기본 원천 파일이 없다면 향후 편집을 위해 시드 단어로 파일 생성
            if not raw_file.exists() and level in SEED_WORDS:
                with open(raw_file, "w", encoding="utf-8") as f:
                    for w, m in SEED_WORDS[level]:
                        f.write(f"{w},{m}\n")
            return SEED_WORDS.get(level, [])

        words: list[tuple[str, str]] = []
        with open(raw_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split(",", 1)
                word = parts[0].strip()
                meaning = parts[1].strip() if len(parts) > 1 else ""
                words.append((word, meaning))

        print(f"  [안내] Level {level}: raw 파일에서 {len(words)}개 단어 로드 완료")
        return words

    def build_level(self, level: int, sample_mode: bool = False) -> Path:
        """
        특정 레벨의 단어 데이터를 수집 및 가공하여 level_{level}.json으로 저장합니다.
        """
        level_name = LEVEL_INFO.get(level, {}).get("name", f"Level {level}")
        print(f"\n==================================================")
        print(f" Level {level} ({level_name}) 단어 데이터 빌드 시작")
        print(f"==================================================")

        word_pairs = self.load_raw_words(level, sample_mode)
        built_entries: list[dict[str, Any]] = []

        total = len(word_pairs)
        for idx, (word, meaning) in enumerate(word_pairs, start=1):
            print(f"[{idx}/{total}] '{word}' ({meaning}) 처리 중...", end="", flush=True)

            # 1. 로컬 캐시 확인
            api_data = self._load_from_cache(word)
            if api_data is not None:
                print(" (캐시 적중)")
            else:
                # 2. API 호출
                api_data = self.client.fetch_word(word)
                self._save_to_cache(word, api_data)
                print(" (API 수신 완료)")

            # 3. 파싱 및 정규화
            entry = WordParser.parse_word_entry(
                word=word,
                korean_meaning=meaning,
                level=level,
                word_index=idx,
                api_data=api_data,
            )
            built_entries.append(entry)

        # 4. JSON 파일 저장
        output_file = DATA_DIR / f"level_{level}.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(built_entries, f, ensure_ascii=False, indent=2)

        print(f"-> Level {level} 저장 완료: {output_file.name} ({len(built_entries)}단어)")
        return output_file

    def update_manifest(self) -> Path:
        """
        모든 level_n.json을 검사하여 manifest.json을 갱신합니다.
        """
        manifest_path = DATA_DIR / "manifest.json"
        now_iso = datetime.now(timezone.utc).isoformat()

        levels_meta: dict[str, Any] = {}
        for level in range(1, 8):
            level_file = DATA_DIR / f"level_{level}.json"
            if level_file.exists():
                try:
                    with open(level_file, "r", encoding="utf-8") as f:
                        entries = json.load(f)
                    levels_meta[str(level)] = {
                        "name": LEVEL_INFO[level]["name"],
                        "count": len(entries),
                        "file": level_file.name,
                        "sha256": compute_sha256(level_file),
                    }
                except Exception as e:
                    print(f"[경고] {level_file.name} 메타데이터 읽기 실패: {e}")

        manifest_data = {
            "version": "1.0.0",
            "updated_at": now_iso,
            "levels": levels_meta,
        }

        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, ensure_ascii=False, indent=2)

        print(f"\n[성공] manifest.json 갱신 완료: {manifest_path}")
        return manifest_path


def main() -> None:
    parser = argparse.ArgumentParser(description="1~7단계 영어 단어 데이터셋 빌더")
    parser.add_argument(
        "--level",
        type=str,
        default="all",
        help="빌드할 레벨 번호 (1~7) 또는 'all' (기본값: all)",
    )
    parser.add_argument(
        "--sample",
        action="store_true",
        help="샘플 시드 단어로 빠르게 테스트 빌드",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="로컬 캐시를 무시하고 API 재호출 강제",
    )

    args = parser.parse_args()
    builder = DictionaryBuilder(use_cache=not args.no_cache)

    if args.level.lower() == "all":
        levels_to_build = list(range(1, 8))
    else:
        try:
            lvl = int(args.level)
            if 1 <= lvl <= 7:
                levels_to_build = [lvl]
            else:
                print("오류: --level은 1부터 7 사이의 숫자여야 합니다.")
                sys.exit(1)
        except ValueError:
            print("오류: --level 인수는 1~7 숫자 또는 'all' 이어야 합니다.")
            sys.exit(1)

    for level in levels_to_build:
        builder.build_level(level, sample_mode=args.sample)

    builder.update_manifest()
    print("\n모든 빌드 작업이 완료되었습니다!")


if __name__ == "__main__":
    main()
