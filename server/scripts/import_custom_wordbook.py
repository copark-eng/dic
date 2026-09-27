# -*- coding: utf-8 -*-
"""
MyDic 커스텀 단어장 (디폴트 나만의 단어장) 엑셀 임포터 및 빌더
- 엑셀(.xlsx, .xls) 및 CSV(.csv) 파일을 읽어 custom_wordbook.json 생성
- 표준 템플릿(sample_my_wordbook.xlsx) 생성 기능 제공
- manifest.json 및 app/assets/data 자동 동기화 지원
"""

import os
import sys
import json
import hashlib
import shutil
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
APP_ASSETS_DIR = BASE_DIR.parent / "app" / "assets" / "data"
DOCS_DATA_DIR = BASE_DIR.parent / "docs" / "data"

COLUMN_MAPPING = {
    # word
    "word": "word", "단어": "word", "표제어": "word", "영어단어": "word",
    # pos
    "pos": "pos", "품사": "pos",
    # meaning
    "meaning": "meaning", "뜻": "meaning", "의미": "meaning", "한글뜻": "meaning", "한국어뜻": "meaning",
    # examples
    "example_en": "example_en", "예문": "example_en", "영어예문": "example_en", "example": "example_en",
    "example_ko": "example_ko", "예문해석": "example_ko", "해석": "example_ko", "한글해석": "example_ko", "translation": "example_ko",
    # phonetics
    "phonetic_us": "phonetic_us", "발음": "phonetic_us", "발음기호": "phonetic_us", "phonetic": "phonetic_us",
    "phonetic_uk": "phonetic_uk",
}

def generate_sample_template(output_path: Path) -> Path:
    """사용자가 다운로드하여 사용할 수 있는 샘플 엑셀 템플릿 생성"""
    sample_data = [
        {
            "단어": "serendipity",
            "품사": "noun",
            "뜻": "뜻밖의 행운, 우연한 발견",
            "영어예문": "Finding this cozy little cafe in the alley was pure serendipity.",
            "예문해석": "골목길에서 이 아늑하고 작은 카페를 발견한 것은 뜻밖의 순수한 행운이었다.",
            "발음기호": "/ˌser.ənˈdɪp.ə.t̬i/"
        },
        {
            "단어": "resilience",
            "품사": "noun",
            "뜻": "회복력, 탄력성",
            "영어예문": "The local community showed great resilience in rebuilding after the disaster.",
            "예문해석": "지역 주민들은 재난 이후 마을을 재건하는 과정에서 놀라운 회복력을 보여주었다.",
            "발음기호": "/rɪˈzɪl.jəns/"
        },
        {
            "단어": "eloquent",
            "품사": "adjective",
            "뜻": "유창한, 설득력 있는",
            "영어예문": "She gave an eloquent speech that moved the entire audience to tears.",
            "예문해석": "그녀는 모든 청중을 눈물 흘리게 만든 설득력 있고 유창한 연설을 했다.",
            "발음기호": "/ˈel.ə.kwənt/"
        },
        {
            "단어": "meticulous",
            "품사": "adjective",
            "뜻": "꼼꼼한, 세심한",
            "영어예문": "The researcher kept meticulous records of every experiment.",
            "예문해석": "그 연구원은 모든 실험에 대해 꼼꼼하고 세심한 기록을 남겼다.",
            "발음기호": "/məˈtɪk.jə.ləs/"
        },
        {
            "단어": "collaborate",
            "품사": "verb",
            "뜻": "협력하다, 공동 연구하다",
            "영어예문": "The two universities decided to collaborate on clean energy technology.",
            "예문해석": "두 대학은 청정 에너지 기술 개발에 서로 협력하기로 결정했다.",
            "발음기호": "/kəˈlæb.ə.reɪt/"
        }
    ]
    df = pd.DataFrame(sample_data)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(output_path, index=False, engine='openpyxl')
    return output_path


import re
import io

def parse_raw_text(text: str) -> pd.DataFrame:
    """
    텍스트 줄 단위 파싱: 'apple 사과', 'apple\t사과', 'apple: 사과' 등
    다양한 형식의 단어-뜻 텍스트를 DataFrame으로 변환
    """
    text = text.lstrip('\ufeff\ufffe')
    lines = text.strip().splitlines()
    rows = []
    for line in lines:
        clean = line.strip().lstrip('\ufeff\ufffe')
        if not clean:
            continue
        # 앞쪽 번호(1. / 1) / [1]) 제거
        clean = re.sub(r'^\s*(\d+[\.\)]|\[\d+\])\s*', '', clean)
        
        # 1. 탭 구분
        if '\t' in clean:
            parts = [p.strip() for p in clean.split('\t') if p.strip()]
            if len(parts) >= 2:
                rows.append({'word': parts[0], 'meaning': ' '.join(parts[1:])})
                continue

        # 2. 한글 시작 위치 감지
        match = re.search(r'[\uac00-\ud7a3\u3131-\u318e]', clean)
        if match:
            idx = match.start()
            w = clean[:idx].strip().rstrip(',:-= \t')
            m = clean[idx:].strip()
            if w.endswith('~'):
                w = w[:-1].strip()
                m = '~' + m
            if w and m:
                rows.append({'word': w, 'meaning': m})
                continue

        # 3. 콜론(:) 또는 첫 번째 공백 분리
        if ':' in clean:
            parts = clean.split(':', 1)
            rows.append({'word': parts[0].strip(), 'meaning': parts[1].strip()})
        else:
            parts = clean.split(None, 1)
            if len(parts) >= 2:
                rows.append({'word': parts[0].strip(), 'meaning': parts[1].strip()})
            elif len(parts) == 1:
                rows.append({'word': parts[0].strip(), 'meaning': '뜻 정보 없음'})

    return pd.DataFrame(rows)


VOCAB_INDEX = None


def get_vocab_index() -> dict:
    """기존 Level 1~7 데이터(26,500단어)로부터 품사, 발음기호 및 예문 인덱스 로드"""
    global VOCAB_INDEX
    if VOCAB_INDEX is not None:
        return VOCAB_INDEX
    VOCAB_INDEX = {}
    for lvl in range(1, 8):
        fpath = DATA_DIR / f"level_{lvl}.json"
        if fpath.exists():
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    for item in json.load(f):
                        w = str(item.get("word", "")).strip().lower()
                        if w and w not in VOCAB_INDEX:
                            phon = item.get("phonetics") or {}
                            VOCAB_INDEX[w] = {
                                "pos": item.get("pos", "noun"),
                                "phonetic_us": phon.get("us") or item.get("phonetic_us"),
                                "phonetic_uk": phon.get("uk") or item.get("phonetic_uk"),
                                "example_en": item.get("example_en"),
                                "example_ko": item.get("example_ko"),
                            }
            except Exception:
                pass
    return VOCAB_INDEX


def infer_pos_from_meaning(meaning: str) -> str:
    """한글 뜻의 어미 패턴을 분석하여 품사(POS) 자동 유추"""
    m = meaning.strip()
    if m.endswith("하다") or m.endswith("되다") or m.endswith("시키다") or "하는 것" in m:
        return "verb"
    if m.endswith("한") or m.endswith("적") or m.endswith("있는") or m.endswith("없는") or m.endswith("로운"):
        return "adjective"
    if m.endswith("하게") or m.endswith("히") or m.endswith("으로"):
        return "adverb"
    return "noun"


def create_natural_example(word: str, meaning: str, pos: str) -> tuple:
    """품사와 단어에 맞춘 자연스러운 실생활 예문 및 한국어 번역 생성"""
    if pos == "verb":
        return f"We should {word} together to achieve our goal.", f"우리는 목표를 달성하기 위해 함께 {word}해야 한다."
    elif pos == "adjective":
        return f"It was a truly {word} experience for everyone.", f"그것은 모든 사람에게 참으로 {meaning} 경험이었다."
    elif pos == "adverb":
        return f"He performed the assigned task {word}.", f"그는 맡은 업무를 {meaning} 수행했다."
    else:
        return f"She looked at the {word} with great interest.", f"그녀는 큰 관심을 갖고 그 {word}을(를) 바라보았다."


def parse_and_build_custom_wordbook(file_path_or_buffer, file_name: str = "") -> dict:
    """
    엑셀, CSV 파일 또는 원본 텍스트를 파싱하여 MyDic 표준 단어장 데이터 구조로 변환
    """
    # 1. 원본 문자열(텍스트 붙여넣기) 또는 .txt 파일 여부 확인
    if isinstance(file_path_or_buffer, str) and ('\n' in file_path_or_buffer or not os.path.exists(file_path_or_buffer)):
        df = parse_raw_text(file_path_or_buffer)
    elif str(file_name).lower().endswith(".txt") or (isinstance(file_path_or_buffer, (str, Path)) and str(file_path_or_buffer).lower().endswith(".txt")):
        if hasattr(file_path_or_buffer, "read"):
            content = file_path_or_buffer.read()
            if isinstance(content, bytes):
                content = content.decode("utf-8", errors="ignore")
        else:
            with open(file_path_or_buffer, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        df = parse_raw_text(content)
    else:
        # 2. 파일 포맷에 따른 DataFrame 로드 (.csv, .xlsx, .xls)
        is_csv = str(file_name).lower().endswith(".csv") or (isinstance(file_path_or_buffer, (str, Path)) and str(file_path_or_buffer).lower().endswith(".csv"))
        
        if is_csv:
            try:
                df = pd.read_csv(file_path_or_buffer, encoding="utf-8-sig")
            except UnicodeDecodeError:
                df = pd.read_csv(file_path_or_buffer, encoding="cp949")
        else:
            df = pd.read_excel(file_path_or_buffer, engine="openpyxl")

        # 컬럼명 정규화 (공백 제거 및 매핑)
        renamed_cols = {}
        for col in df.columns:
            clean_col = str(col).strip().lower()
            if clean_col in COLUMN_MAPPING:
                renamed_cols[col] = COLUMN_MAPPING[clean_col]
        
        df = df.rename(columns=renamed_cols)

        # 헤더 없는 2개 열 파일 자동 복구 지원
        required = ["word", "meaning"]
        missing = [c for c in required if c not in df.columns]
        if missing and len(df.columns) == 2:
            cols = [str(c).strip().lower() for c in df.columns]
            known_headers = {'word', '단어', '표제어', '영어단어', 'pos', '품사', 'meaning', '뜻', '의미'}
            if not any(c in known_headers for c in cols):
                # 첫 번째 행이 헤더로 잘못 인식된 경우, 첫 행을 데이터로 복원
                first_row = pd.DataFrame([list(df.columns)], columns=[0, 1])
                df.columns = [0, 1]
                df = pd.concat([first_row, df], ignore_index=True)
            df.columns = ["word", "meaning"]
            missing = []

        if missing:
            raise ValueError(f"필수 컬럼이 누락되었습니다: {missing}. ('단어', '뜻' 컬럼은 반드시 포함되어야 합니다.)")

    entries = []
    total_rows = len(df)
    words_per_day = max(1, (total_rows + 29) // 30)  # 30일에 균등 배분
    vocab_idx = get_vocab_index()

    for idx, row in df.iterrows():
        raw_word = str(row.get("word", "")).strip().lstrip('\ufeff\ufffe')
        if not raw_word or raw_word.lower() in ("nan", "none", ""):
            continue

        meaning = str(row.get("meaning", "")).strip()
        if not meaning or meaning.lower() in ("nan", "none"):
            meaning = "뜻 정보 없음"

        word_key = raw_word.lower()
        cached_info = vocab_idx.get(word_key, {})

        pos = str(row.get("pos", "")).strip()
        if not pos or pos.lower() in ("nan", "none"):
            pos = cached_info.get("pos") or infer_pos_from_meaning(meaning)

        phonetic_us = str(row.get("phonetic_us", "")).strip()
        if not phonetic_us or phonetic_us.lower() in ("nan", "none"):
            phonetic_us = cached_info.get("phonetic_us") or f"/{raw_word}/"

        phonetic_uk = str(row.get("phonetic_uk", "")).strip()
        if not phonetic_uk or phonetic_uk.lower() in ("nan", "none"):
            phonetic_uk = cached_info.get("phonetic_uk") or phonetic_us

        example_en = str(row.get("example_en", "")).strip()
        example_ko = str(row.get("example_ko", "")).strip()
        if not example_en or example_en.lower() in ("nan", "none"):
            if cached_info.get("example_en"):
                example_en = cached_info["example_en"]
                example_ko = cached_info.get("example_ko", f"{raw_word}의 예문입니다.")
            else:
                example_en, example_ko = create_natural_example(raw_word, meaning, pos)

        # 순번 기반 ID 및 Day 배정 (Level 0: 디폴트 나만의 단어장)
        word_num = len(entries) + 1
        day = min(30, (word_num - 1) // words_per_day + 1)
        word_id = f"MY-{word_num:04d}"

        # 무료 발음 CDN URL 생성
        # 고품질 원어민 음원 URL 생성 (US: type 2, UK: type 1)
        clean_word_url = urllib.parse.quote(raw_word.strip())
        audio_us = f"https://dict.youdao.com/dictvoice?audio={clean_word_url}&type=2"
        audio_uk = f"https://dict.youdao.com/dictvoice?audio={clean_word_url}&type=1"

        entries.append({
            "id": word_id,
            "level": 0,
            "day": day,
            "word": raw_word,
            "pos": pos,
            "meaning": meaning,
            "phonetics": {
                "us": phonetic_us,
                "uk": phonetic_uk
            },
            "audio": {
                "us": audio_us,
                "uk": audio_uk
            },
            "phonetic_us": phonetic_us,
            "phonetic_uk": phonetic_uk,
            "audio_us": audio_us,
            "audio_uk": audio_uk,
            "example_en": example_en,
            "example_ko": example_ko
        })

    return {
        "level": 0,
        "name": "디폴트 나만의 단어장",
        "code": "MY",
        "total_words": len(entries),
        "words": entries
    }


def save_and_sync(wordbook_data: dict) -> dict:
    """
    파싱된 단어장 데이터를 JSON으로 저장하고 manifest 업데이트 및 앱 assets 동기화
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    json_path = DATA_DIR / "custom_wordbook.json"

    # 1. JSON 저장
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(wordbook_data["words"], f, ensure_ascii=False, indent=2)

    file_bytes = json_path.read_bytes()
    sha256_hash = hashlib.sha256(file_bytes).hexdigest()
    file_size = len(file_bytes)

    # 2. manifest.json 업데이트
    manifest_path = DATA_DIR / "manifest.json"
    manifest = {}
    if manifest_path.exists():
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

    if "levels" not in manifest:
        manifest["levels"] = {}

    manifest["updated_at"] = datetime.now(timezone.utc).isoformat()
    manifest["levels"]["0"] = {
        "name": "디폴트 나만의 단어장",
        "code": "MY",
        "total_words": wordbook_data["total_words"],
        "file": "custom_wordbook.json",
        "file_size_bytes": file_size,
        "sha256": sha256_hash,
        "updated_at": manifest["updated_at"],
        "count": wordbook_data["total_words"]
    }

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    # 3. 플러터 앱 assets 및 docs CDN 디렉토리 동기화
    if APP_ASSETS_DIR.exists():
        shutil.copy2(json_path, APP_ASSETS_DIR / "custom_wordbook.json")
        shutil.copy2(manifest_path, APP_ASSETS_DIR / "manifest.json")

    if DOCS_DATA_DIR.exists():
        shutil.copy2(json_path, DOCS_DATA_DIR / "custom_wordbook.json")
        shutil.copy2(manifest_path, DOCS_DATA_DIR / "manifest.json")

    return {
        "json_path": str(json_path),
        "total_words": wordbook_data["total_words"],
        "sha256": sha256_hash,
        "file_size_bytes": file_size
    }


if __name__ == "__main__":
    target_file = None
    if len(sys.argv) > 1:
        target_file = Path(sys.argv[1])
    else:
        # Check uploads directories
        upload_dirs = [BASE_DIR / "uploads", BASE_DIR.parent / "uploads"]
        candidates = []
        for udir in upload_dirs:
            if udir.exists():
                for f in udir.glob("*.*"):
                    if f.suffix.lower() in [".xlsx", ".xls", ".csv", ".txt"]:
                        candidates.append(f)
        if candidates:
            # Sort newest first
            candidates.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            target_file = candidates[0]
            print(f"[Auto-Detect] Found uploaded file: {target_file}")

    if not target_file or not target_file.exists():
        target_file = DATA_DIR / "sample_my_wordbook.xlsx"
        print(f"Generating and using sample template: {target_file}")
        generate_sample_template(target_file)

    print(f"Parsing and building custom wordbook from: {target_file}")
    parsed = parse_and_build_custom_wordbook(target_file, target_file.name)
    result = save_and_sync(parsed)
    print(f"Success! Built custom wordbook: {result['total_words']} words, size: {result['file_size_bytes']} bytes")
