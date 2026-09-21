# -*- coding: utf-8 -*-
"""
단어 예문 및 번역 품질 검증 린터 (Quality Linter)
데이터셋 내의 기계적 템플릿, 비문법적 표현, 불완전한 조사 등을 전수 검사합니다.
"""

import argparse
import json
import re
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
SERVER_DIR = SCRIPTS_DIR.parent
DATA_DIR = SERVER_DIR / "data"

PROHIBITED_BOILERPLATE = [
    "plays an essential role",
    "looked up the word",
    "after careful consideration",
    "in any situation",
    "completed the project",
    "highlighted the word",
    "is very important to us",
]

GRAMMAR_ERRORS_EN = [
    r"\bthe\s+these\b",
    r"\bthe\s+this\b",
    r"\bthe\s+those\b",
    r"\bthe\s+that\b",
    r"\bthe\s+I\b",
    r"\bthe\s+you\b",
    r"\bthe\s+he\b",
    r"\bthe\s+she\b",
    r"\bthe\s+we\b",
    r"\bthe\s+they\b",
    r"\bthe\s+my\b",
    r"\bthe\s+your\b",
    r"\bthe\s+his\b",
    r"\bthe\s+her\b",
    r"\bthe\s+our\b",
    r"\bthe\s+their\b",
    r"\bregarding\s+the\s+these\b",
]

GRAMMAR_ERRORS_KO = [
    r"\(은\)는",
    r"\(이\)가",
    r"\(을\)를",
    r"\(과\)와",
    r"\(으\)로",
    r"달리하기로",
    r"좋하고",
]

def verify_level(level_num: int) -> dict:
    file_path = DATA_DIR / f"level_{level_num}.json"
    if not file_path.exists():
        return {"error": f"File not found: {file_path.name}"}

    with open(file_path, "r", encoding="utf-8") as f:
        entries = json.load(f)

    issues = []
    boilerplate_counts = {bp: 0 for bp in PROHIBITED_BOILERPLATE}

    for idx, entry in enumerate(entries):
        word_id = entry.get("id", f"idx_{idx}")
        word = entry.get("word", "")
        ex_en = entry.get("example_en", "")
        ex_ko = entry.get("example_ko", "")
        meaning = entry.get("meaning", "")

        if not ex_en or not ex_ko:
            issues.append((word_id, word, "Empty example", f"en: '{ex_en}', ko: '{ex_ko}'"))
            continue

        # 1. Boilerplate check
        ex_en_lower = ex_en.lower()
        for bp in PROHIBITED_BOILERPLATE:
            if bp.lower() in ex_en_lower:
                boilerplate_counts[bp] += 1
                issues.append((word_id, word, f"Boilerplate detected: '{bp}'", ex_en))

        # 2. English grammar check
        for pattern in GRAMMAR_ERRORS_EN:
            if re.search(pattern, ex_en, re.IGNORECASE):
                issues.append((word_id, word, "Grammar error EN", ex_en))

        # 3. Korean grammar check
        for pattern in GRAMMAR_ERRORS_KO:
            if re.search(pattern, ex_ko):
                issues.append((word_id, word, "Grammar error KO", ex_ko))

    return {
        "level": level_num,
        "total_words": len(entries),
        "issue_count": len(issues),
        "issues": issues,
        "boilerplate_counts": {k: v for k, v in boilerplate_counts.items() if v > 0},
    }

def main():
    parser = argparse.ArgumentParser(description="단어 예문 품질 검증 린터")
    parser.add_argument("--level", type=int, help="검증할 레벨 (1~7). 미지정 시 전체 검증")
    args = parser.parse_args()

    levels = [args.level] if args.level else list(range(1, 8))

    total_issues = 0
    print("=" * 60)
    print(" [MyDic 단어 예문 품질 검증 린터(Linter)]")
    print("=" * 60)

    for lvl in levels:
        res = verify_level(lvl)
        if "error" in res:
            print(f"[Level {lvl}] 오류: {res['error']}")
            continue

        print(f"\n[Level {lvl}] 총 {res['total_words']}단어 검사:")
        bp_c = res["boilerplate_counts"]
        if bp_c:
            print("  - 감지된 템플릿 문구:")
            for bp, count in bp_c.items():
                print(f"    * '{bp}': {count}회")
        print(f"  - 총 결함 건수: {res['issue_count']}건")

        if res["issue_count"] > 0:
            total_issues += res["issue_count"]
            print("  - 주요 결함 샘플 (최대 5건):")
            for word_id, word, reason, sample in res["issues"][:5]:
                print(f"    * [{word_id}] {word}: {reason} -> \"{sample}\"")
        else:
            print("  -> 품질 검증 통과! (결함 0건)")

    print("\n" + "=" * 60)
    if total_issues > 0:
        print(f"FAILED: 총 {total_issues}건의 품질 결함이 발견되었습니다.")
        sys.exit(1)
    else:
        print("PASSED: 모든 레벨의 예문 품질 검증이 성공적으로 통과되었습니다.")
        sys.exit(0)

if __name__ == "__main__":
    main()
