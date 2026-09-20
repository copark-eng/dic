# -*- coding: utf-8 -*-
from __future__ import annotations
"""
Step 1: 7단계 순수 단어 리스트 생성 스크립트 (Generate Word Lists)
Oxford 5K, Oxford OPAL, Kengdic 원천 데이터를 기반으로
각 레벨별 목표 수량에 맞춰 고유한 영단어 및 한국어 뜻 리스트를 생성합니다.

목표 수량:
- Level 1: 1,000단어 (기초)
- Level 2: 2,000단어 (중등)
- Level 3: 3,000단어 (수능기본)
- Level 4: 4,500단어 (수능심화)
- Level 5: 4,000단어 (TOEIC 750)
- Level 6: 5,500단어 (TOEIC 900)
- Level 7: 6,500단어 (TOEIC 990)
총 26,500단어 (레벨 간 중복 없음)
"""

import csv
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

# 설정 불러오기
SCRIPTS_DIR = Path(__file__).resolve().parent
SERVER_DIR = SCRIPTS_DIR.parent
RAW_DIR = SERVER_DIR / "raw"

# 시스템 경로 추가 및 config 로드 (Windows SSL/경로 지원)
sys.path.insert(0, str(SCRIPTS_DIR))
import config

TARGET_COUNTS = {
    1: 1000,
    2: 2000,
    3: 3000,
    4: 4500,
    5: 4000,
    6: 5500,
    7: 6500,
}

def clean_word(w: str) -> str:
    w = w.strip().lower()
    # 괄호 및 특수문자 제거
    w = re.sub(r'[\(\)\[\]\{\}\'\"\.\,\;\:\!\?]', '', w)
    return w.strip()

def build_kengdic_pool() -> tuple[dict[str, str], dict[str, list[str]]]:
    """Kengdic TSV에서 영단어 -> 대표 한국어 뜻 및 레벨별 단어 풀 추출"""
    kengdic_file = RAW_DIR / "kengdic.tsv"
    word_meaning: dict[str, str] = {}
    level_buckets: dict[str, list[str]] = defaultdict(list)
    
    with open(kengdic_file, "r", encoding="utf-8") as f:
        f.readline() # 헤더 스킵
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) >= 4:
                surface = parts[1].strip() # 한국어 뜻
                gloss = parts[3].strip()   # 영단어/구문
                lvl = parts[4].strip() if len(parts) >= 5 else "" # A, B, C, D 또는 빈값
                
                # 구문 분리
                for raw_w in re.split(r'[,;/]', gloss):
                    cw = clean_word(raw_w)
                    if cw.isalpha() and len(cw) >= 2:
                        if cw not in word_meaning:
                            word_meaning[cw] = surface
                        if lvl in ("A", "B", "C", "D"):
                            level_buckets[lvl].append(cw)
                        else:
                            level_buckets["OTHER"].append(cw)
                            
    return word_meaning, level_buckets

def load_oxford_5k() -> dict[str, list[str]]:
    """Oxford 5K CSV에서 CEFR 레벨별 단어 추출"""
    oxford_file = RAW_DIR / "oxford-5k.csv"
    cefr_words: dict[str, list[str]] = defaultdict(list)
    
    if oxford_file.exists():
        with open(oxford_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                w = clean_word(row["word"])
                lvl = row["level"].strip().lower()
                if w.isalpha() and len(w) >= 2:
                    cefr_words[lvl].append(w)
    return cefr_words

def load_oxford_opal() -> list[str]:
    """Oxford OPAL CSV에서 학술 어휘 추출"""
    opal_file = RAW_DIR / "oxford-opal.csv"
    opal_words: list[str] = []
    
    if opal_file.exists():
        with open(opal_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                w = clean_word(row["word"])
                if w.isalpha() and len(w) >= 2:
                    opal_words.append(w)
    return opal_words

def load_existing_level_1() -> list[tuple[str, str]]:
    """이미 확정된 Level 1 단어 1,000개 로드"""
    l1_file = RAW_DIR / "level_1_words.txt"
    l1_entries: list[tuple[str, str]] = []
    if l1_file.exists():
        with open(l1_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split(",", 1)
                w = parts[0].strip()
                m = parts[1].strip() if len(parts) > 1 else ""
                l1_entries.append((w, m))
    return l1_entries

def main():
    print("=" * 60)
    print("Step 1: 7단계 순수 단어 리스트(Word Lists) 생성 시작")
    print("=" * 60)
    
    # 1. Kengdic 및 원천 데이터 로드
    print("[1/4] 원천 데이터셋(Kengdic, Oxford 5K, Oxford OPAL) 로드 중...")
    keng_meanings, keng_levels = build_kengdic_pool()
    oxford_cefr = load_oxford_5k()
    oxford_opal = load_oxford_opal()
    
    # 2. Level 1 고정 로드 및 중복 정제 (1,000개 고유 단어 확보)
    allocated_words: dict[int, list[tuple[str, str]]] = {}
    seen_words: set[str] = set()
    
    raw_l1 = load_existing_level_1()
    clean_l1: list[tuple[str, str]] = []
    for w, m in raw_l1:
        wl = clean_word(w)
        if wl and wl not in seen_words and wl.isalpha():
            seen_words.add(wl)
            clean_l1.append((w, m))
            
    # L1에 중복으로 인해 1,000개 미만인 경우 Oxford A1 단어로 정확히 1,000개 채움
    if len(clean_l1) < TARGET_COUNTS[1]:
        for raw_w in oxford_cefr.get("a1", []):
            cw = clean_word(raw_w)
            if cw and cw not in seen_words and cw.isalpha():
                meaning = keng_meanings.get(cw, "")
                if meaning:
                    seen_words.add(cw)
                    clean_l1.append((cw, meaning))
                    if len(clean_l1) == TARGET_COUNTS[1]:
                        break
                        
    allocated_words[1] = clean_l1
    print(f"  - Level 1: {len(clean_l1):,} 단어 정제 및 1,000단어 확정 완료 (100% 고유)")
    
    # 레벨별 후보 단어 풀 구성
    # Level 2 (중등 2,000): Oxford a2 + Kengdic A/B
    pool_l2 = oxford_cefr.get("a2", []) + keng_levels.get("A", []) + keng_levels.get("B", [])
    # Level 3 (수능기본 3,000): Oxford b1 + Kengdic B + Kengdic C
    pool_l3 = oxford_cefr.get("b1", []) + keng_levels.get("B", []) + keng_levels.get("C", [])
    # Level 4 (수능심화 4,500): Oxford b2 + Kengdic C
    pool_l4 = oxford_cefr.get("b2", []) + keng_levels.get("C", [])
    # Level 5 (TOEIC 750 4,000): Oxford c1 + Kengdic C + 일반 어휘
    pool_l5 = oxford_cefr.get("c1", []) + keng_levels.get("C", []) + keng_levels.get("OTHER", [])
    # Level 6 (TOEIC 900 5,500): Oxford OPAL + Kengdic 일반 어휘
    pool_l6 = oxford_opal + keng_levels.get("OTHER", [])
    # Level 7 (TOEIC 990 6,500): Oxford OPAL + 고급 Kengdic 일반 어휘
    pool_l7 = oxford_opal + keng_levels.get("OTHER", [])
    
    pools = {
        2: pool_l2,
        3: pool_l3,
        4: pool_l4,
        5: pool_l5,
        6: pool_l6,
        7: pool_l7,
    }
    
    # 백업 일반 어휘 풀 (부족분 충당용)
    fallback_pool = (
        keng_levels.get("C", []) +
        keng_levels.get("OTHER", [])
    )
    fallback_idx = 0
    
    print("[2/4] 레벨 2 ~ 7 순수 단어 목록 추출 및 배분 중...")
    for lvl in range(2, 8):
        target = TARGET_COUNTS[lvl]
        lvl_list: list[tuple[str, str]] = []
        
        # 1차: 해당 레벨 후보 풀에서 할당
        for raw_w in pools[lvl]:
            w = clean_word(raw_w)
            if w and w not in seen_words and w.isalpha() and len(w) >= 2:
                meaning = keng_meanings.get(w, "")
                if meaning: # 유효한 한국어 뜻이 있는 단어만 채택
                    seen_words.add(w)
                    lvl_list.append((w, meaning))
                    if len(lvl_list) >= target:
                        break
                        
        # 2차: 부족분 발생 시 fallback_pool에서 추가 채움
        while len(lvl_list) < target and fallback_idx < len(fallback_pool):
            raw_w = fallback_pool[fallback_idx]
            fallback_idx += 1
            w = clean_word(raw_w)
            if w and w not in seen_words and w.isalpha() and len(w) >= 2:
                meaning = keng_meanings.get(w, "")
                if meaning:
                    seen_words.add(w)
                    lvl_list.append((w, meaning))
                    
        allocated_words[lvl] = lvl_list
        print(f"  - Level {lvl}: {len(lvl_list):,} / {target:,} 단어 추출 완료")
        
    # 3. 파일 저장 (server/raw/level_{n}_words.txt)
    print("[3/4] server/raw/level_n_words.txt 파일 저장 중...")
    for lvl in range(1, 8):
        out_file = RAW_DIR / f"level_{lvl}_words.txt"
        with open(out_file, "w", encoding="utf-8") as f:
            for w, m in allocated_words[lvl]:
                f.write(f"{w},{m}\n")
        print(f"  - 저장 완료: {out_file.name} ({len(allocated_words[lvl]):,} 단어)")
        
    # 4. 무결성 및 중복 검증
    print("[4/4] 데이터 무결성 검증...")
    total_count = sum(len(words) for words in allocated_words.values())
    unique_words = len(seen_words)
    print(f"  - 총 단어 수: {total_count:,}")
    print(f"  - 고유 단어 수: {unique_words:,}")
    assert total_count == unique_words, "단어 간 중복이 존재합니다!"
    for lvl in range(1, 8):
        assert len(allocated_words[lvl]) == TARGET_COUNTS[lvl], f"Level {lvl} 단어 수가 일치하지 않습니다!"
        
    print("=" * 60)
    print("Step 1 완료: 총 26,500 단어 리스트가 성공적으로 구축되었습니다.")
    print("=" * 60)

if __name__ == "__main__":
    main()
