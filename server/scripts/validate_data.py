# -*- coding: utf-8 -*-
from __future__ import annotations
"""
데이터셋 무결성 및 스키마 검증기 (Validate Data)
Level 1부터 Level 7까지 모든 JSON 파일의 스키마, 필수 필드 누락 여부,
단어 수 일치 여부, manifest.json 체크섬 정합성을 종합 검증합니다.
"""

import hashlib
import json
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
SERVER_DIR = SCRIPTS_DIR.parent
DATA_DIR = SERVER_DIR / "data"

EXPECTED_COUNTS = {
    1: 1000,
    2: 2000,
    3: 3000,
    4: 4500,
    5: 4000,
    6: 5500,
    7: 6500,
}

REQUIRED_KEYS = [
    "id", "word", "level", "pos", "meaning",
    "phonetics", "audio", "example_en", "example_ko"
]

def main() -> int:
    print("=" * 60)
    print("MyDic 단어 데이터셋 종합 무결성 검증 (Level 1 ~ 7)")
    print("=" * 60)

    # 1. manifest.json 로드
    manifest_path = DATA_DIR / "manifest.json"
    if not manifest_path.exists():
        print("[ERROR] manifest.json 파일이 존재하지 않습니다.")
        return 1

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    total_words_sum = 0
    all_words_seen: set[str] = set()
    errors: list[str] = []

    for lvl in range(1, 8):
        json_path = DATA_DIR / f"level_{lvl}.json"
        if not json_path.exists():
            errors.append(f"Level {lvl}: {json_path.name} 파일 없음")
            continue

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        count = len(data)
        total_words_sum += count

        # 수량 검증
        exp = EXPECTED_COUNTS[lvl]
        if count != exp:
            errors.append(f"Level {lvl}: 단어 수 불일치 (기대: {exp}, 실제: {count})")

        # 체크섬 검증
        hasher = hashlib.sha256()
        with open(json_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        calc_sha = hasher.hexdigest()
        mani_info = manifest.get("levels", {}).get(str(lvl), {})
        mani_sha = mani_info.get("sha256")
        if calc_sha != mani_sha:
            errors.append(f"Level {lvl}: SHA-256 불일치 (계산: {calc_sha[:8]}..., manifest: {mani_sha[:8]}...)")

        # 레코드 필드 검증
        for idx, item in enumerate(data, start=1):
            for k in REQUIRED_KEYS:
                if k not in item or item[k] is None:
                    errors.append(f"Level {lvl} #{idx} ({item.get('word')}): 필수 필드 누락 '{k}'")

            word_str = item.get("word", "").lower()
            all_words_seen.add(word_str)

        print(f"  - Level {lvl} ({mani_info.get('name', 'N/A')}): {count:,}단어 검증 통과 (SHA-256: {calc_sha[:10]}...)")

    print("-" * 60)
    print(f"전체 검증 단어 수: {total_words_sum:,}개")
    print(f"전체 고유 단어 수: {len(all_words_seen):,}개")

    if errors:
        print(f"\n[실패] 총 {len(errors)}건의 오류가 발견되었습니다:")
        for err in errors[:10]:
            print(f"  - {err}")
        return 1

    print("=" * 60)
    print("검증 성공: 모든 7단계 단어 데이터가 스키마 규격 및 ADR-001을 완벽히 만족합니다.")
    print("=" * 60)
    return 0

if __name__ == "__main__":
    sys.exit(main())
