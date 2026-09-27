# -*- coding: utf-8 -*-
"""
품사(POS) 데이터 전면 정제 및 교정 스크립트
- Oxford 5K 및 한국어 뜻 어미 분석을 결합하여 잘못 분류된 품사(대다수 'noun')를
  정확한 품사('adjective', 'verb', 'adverb', 'noun' 등)로 재분류
- server/data, app/assets/data, docs/data 동시 동기화
"""

import csv
import json
import os
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "raw"
SERVER_DATA = BASE_DIR / "data"
APP_ASSETS = BASE_DIR.parent / "app" / "assets" / "data"
DOCS_DATA = BASE_DIR.parent / "docs" / "data"

def load_oxford_pos():
    pos_map = {}
    oxford_file = RAW_DIR / "oxford-5k.csv"
    if oxford_file.exists():
        with open(oxford_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                w = row.get("word", "").strip().lower()
                p = row.get("pos", "").strip().lower()
                if w and p and w not in pos_map:
                    # 정규화
                    if p in ["noun", "verb", "adjective", "adverb", "preposition", "conjunction", "pronoun", "exclamation"]:
                        pos_map[w] = p
                    elif "adj" in p:
                        pos_map[w] = "adjective"
                    elif "adv" in p:
                        pos_map[w] = "adverb"
                    elif "verb" in p:
                        pos_map[w] = "verb"
    return pos_map

def infer_pos_from_meaning(meaning, word="", default_pos="noun"):
    if not meaning or not meaning.strip():
        return default_pos

    # 괄호 제거: "(기계가)정교한" -> "정교한"
    cleaned = re.sub(r'\(.*?\)', '', meaning).strip()
    tokens = [t.strip() for t in re.split(r'[,;/~·]', cleaned) if t.strip()]
    if not tokens:
        return default_pos

    adj_votes = 0
    verb_votes = 0
    adv_votes = 0

    for t in tokens:
        # 형용사 패턴
        if any(t.endswith(e) for e in ['한', '된', '인', '로운', '스러운', '스런', '없는', '있는', '직한', '같은']) or \
           (t.endswith('은') and len(t) >= 2 and not t.endswith(('것은', '말은'))) or \
           (t.endswith('적') and len(t) >= 2) or \
           (t.endswith('는') and not t.endswith('하는 것')):
            adj_votes += 1
            continue

        # 동사 패턴
        if any(t.endswith(e) for e in ['하다', '되다', '시키다', '거리다', '대다', '받다', '주다', '내다', '나다', '오다', '가다', '치다', '지다', '맞추다', '놓다', '두다']) or \
           (t.endswith('다') and len(t) >= 2 and not t.endswith('마다')):
            verb_votes += 1
            continue

        # 부사 패턴
        if any(t.endswith(e) for e in ['하게', '히', '으로', '듯이', '스레']):
            adv_votes += 1
            continue

    # 투표 결과 판별
    if adj_votes > 0 and adj_votes >= verb_votes and adj_votes >= adv_votes:
        return 'adjective'
    if verb_votes > 0 and verb_votes >= adj_votes and verb_votes >= adv_votes:
        return 'verb'
    if adv_votes > 0 and adv_votes >= adj_votes and adv_votes >= verb_votes:
        return 'adverb'

    # 영단어 접미사 보조 휴리스틱
    w_lower = word.lower()
    if w_lower.endswith(('able', 'ible', 'ous', 'ious', 'ful', 'less', 'ish')) and adj_votes >= verb_votes:
        return 'adjective'
    if w_lower.endswith('ly') and not w_lower.endswith(('friendly', 'lovely', 'costly', 'lively', 'lonely', 'ugly', 'silly', 'holy', 'early')):
        if adv_votes >= adj_votes and adv_votes >= verb_votes:
            return 'adverb'

    return default_pos

def process_file(file_path, oxford_map):
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if not isinstance(data, list):
        return 0, len(data)

    changed = 0
    pos_stats = {}

    for item in data:
        w = item.get('word', '').strip().lower()
        curr_pos = item.get('pos', 'noun')
        meaning = item.get('meaning', '')

        # 1차: 뜻 기반 분석
        inferred = infer_pos_from_meaning(meaning, word=w, default_pos=curr_pos)

        # 2차: Oxford 5K와 대조 (Oxford가 형용사/동사/부사인데 현재가 noun인 경우 Oxford 적극 반영)
        if w in oxford_map:
            ox_pos = oxford_map[w]
            if curr_pos == 'noun' and ox_pos in ['adjective', 'verb', 'adverb']:
                inferred = ox_pos
            elif inferred == 'noun' and ox_pos != 'noun':
                inferred = ox_pos

        if inferred != curr_pos:
            item['pos'] = inferred
            changed += 1

        p = item.get('pos', 'noun')
        pos_stats[p] = pos_stats.get(p, 0) + 1

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return changed, len(data), pos_stats

def main():
    oxford_map = load_oxford_pos()
    print(f"[정보] Oxford 5K 단어 로드: {len(oxford_map)}개")

    target_files = [
        "custom_wordbook.json",
        "level_1.json",
        "level_2.json",
        "level_3.json",
        "level_4.json",
        "level_5.json",
        "level_6.json",
        "level_7.json",
    ]

    for fname in target_files:
        src = APP_ASSETS / fname
        if not src.exists():
            continue

        changed, total, stats = process_file(src, oxford_map)
        print(f"[{fname}] 변경: {changed}/{total}건 | 분포: {stats}")

        # docs/data 및 server/data 동기화
        doc_dest = DOCS_DATA / fname
        if doc_dest.parent.exists():
            with open(src, 'r', encoding='utf-8') as sf, open(doc_dest, 'w', encoding='utf-8') as df:
                df.write(sf.read())

        srv_dest = SERVER_DATA / fname
        if srv_dest.parent.exists():
            with open(src, 'r', encoding='utf-8') as sf, open(srv_dest, 'w', encoding='utf-8') as df:
                df.write(sf.read())

    print("\n[완료] 모든 데이터셋의 품사(POS) 정제 및 동기화 완료!")

if __name__ == "__main__":
    main()
