# -*- coding: utf-8 -*-
from __future__ import annotations
"""
Oxford 데이터셋과 Kengdic 매핑 테스트 스크립트
"""

import csv
from pathlib import Path

SERVER_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = SERVER_DIR / "raw"

def inspect_data():
    kengdic_path = RAW_DIR / "kengdic.tsv"
    oxford_path = RAW_DIR / "oxford-5k.csv"
    opal_path = RAW_DIR / "oxford-opal.csv"

    # 1. Kengdic 로드 (영어 단어 -> 한국어 뜻 매핑 구축)
    eng_to_kor: dict[str, list[str]] = {}
    with open(kengdic_path, "r", encoding="utf-8", errors="ignore") as f:
        reader = csv.reader(f, delimiter="\t")
        header = next(reader, None)
        print("Kengdic 헤더:", header)
        count = 0
        for row in reader:
            if len(row) >= 4:
                surface = row[1].strip()  # 한국어
                gloss = row[3].strip()    # 영어
                if surface and gloss:
                    # gloss는 종종 "to abandon", "abandon (v)" 또는 "apple" 등일 수 있음
                    eng_clean = gloss.lower().strip()
                    # 간단한 분리
                    for token in eng_clean.split(";"):
                        token = token.strip()
                        if token and len(token.split()) <= 2:
                            eng_to_kor.setdefault(token, []).append(surface)
            count += 1
        print(f"Kengdic 총 로우 수: {count}, 매핑된 영단어 수: {len(eng_to_kor)}")

    # 2. Oxford 5k 레벨 분포 확인
    level_counts: dict[str, int] = {}
    with open(oxford_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            lvl = row["level"].lower()
            level_counts[lvl] = level_counts.get(lvl, 0) + 1

    print("Oxford 5k 레벨 분포:", level_counts)

    # 3. 매핑 테스트 (샘플 10개)
    matched = 0
    total = 0
    with open(oxford_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            w = row["word"].lower().strip()
            total += 1
            if w in eng_to_kor:
                matched += 1

    print(f"Oxford 단어 매핑 성공률: {matched}/{total} ({matched/total*100:.1f}%)")

if __name__ == "__main__":
    inspect_data()
