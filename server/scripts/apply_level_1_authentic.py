# -*- coding: utf-8 -*-
"""
Level 1 기초 1,000단어 정통 예문 전면 적용 스크립트
Part 1 ~ Part 5 데이터를 병합하여 level_1.json 및 app/assets/data/level_1.json을 갱신하고
manifest.json의 해시값을 재계산합니다.
"""

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
import sys

SCRIPTS_DIR = Path(__file__).resolve().parent
SERVER_DIR = SCRIPTS_DIR.parent
DATA_DIR = SERVER_DIR / "data"
APP_ASSETS_DIR = SERVER_DIR.parent / "app" / "assets" / "data"

sys.path.insert(0, str(SCRIPTS_DIR))
from l1_data_part1 import PART1_SENTENCES
from l1_data_part2 import PART2_SENTENCES
from l1_data_part3 import PART3_SENTENCES
from l1_data_part4 import PART4_SENTENCES
from l1_data_part5 import PART5_SENTENCES

def main():
    print("=" * 60)
    print(" [Level 1 기초 1,000단어 정통 맞춤형 예문 전면 교체]")
    print("=" * 60)

    # 1. 1,000개 예문 병합
    all_sentences = {}
    all_sentences.update(PART1_SENTENCES)
    all_sentences.update(PART2_SENTENCES)
    all_sentences.update(PART3_SENTENCES)
    all_sentences.update(PART4_SENTENCES)
    all_sentences.update(PART5_SENTENCES)

    print(f"-> 총 등록된 예문 수: {len(all_sentences)}개 (목표 1,000개)")
    assert len(all_sentences) == 1000, f"예문 개수가 1,000개가 아닙니다: {len(all_sentences)}"

    # 2. level_1.json 로드
    l1_path = DATA_DIR / "level_1.json"
    with open(l1_path, "r", encoding="utf-8") as f:
        entries = json.load(f)

    print(f"-> level_1.json 단어 수: {len(entries)}개")
    assert len(entries) == 1000, f"level_1.json 단어 수가 1,000개가 아닙니다: {len(entries)}"

    # 3. 예문 치환
    for idx, entry in enumerate(entries, start=1):
        if idx in all_sentences:
            ex_en, ex_ko = all_sentences[idx]
            entry["example_en"] = ex_en
            entry["example_ko"] = ex_ko

    # 4. 저장
    with open(l1_path, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)
    print(f"-> {l1_path.name} 저장 완료!")

    # 5. app/assets/data/level_1.json 복사
    if APP_ASSETS_DIR.exists():
        app_l1_path = APP_ASSETS_DIR / "level_1.json"
        shutil.copy2(l1_path, app_l1_path)
        print(f"-> 앱 자산 동기화 완료: {app_l1_path}")

    # 6. SHA-256 계산 및 manifest.json 갱신
    hasher = hashlib.sha256()
    with open(l1_path, "rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    sha256 = hasher.hexdigest()

    manifest_path = DATA_DIR / "manifest.json"
    if manifest_path.exists():
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        manifest.setdefault("levels", {})["1"] = {
            "name": "기초",
            "count": len(entries),
            "file": "level_1.json",
            "sha256": sha256,
        }
        manifest["updated_at"] = datetime.now(timezone.utc).isoformat()
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
        print("-> manifest.json Level 1 SHA-256 갱신 완료!")

    print("\nLevel 1 전체 교체 작업 완료!")

if __name__ == "__main__":
    main()
