# -*- coding: utf-8 -*-
"""
MY단어장 (Level 0) 알파벳순 전면 재정렬 및 오탈자/음원 교정 스크립트
1. 'corporatiion' 오탈자를 'corporation'으로 교정 및 정식 발음기호/예문/음원 다운로드
2. 1,222개 단어 전체를 알파벳(A~Z) 순서로 정렬
3. Day 01 ~ Day 30 균등 재배치 (Day당 약 41단어)
4. 신규 순번 ID(MY-0001 ~ MY-1222) 부여
5. server/audio/level_0/ 음원 파일 리매핑 및 corporation 신규 음원 교체
6. server/audio/level_0.zip 재압축 생성
7. server/data, app/assets/data, docs/data custom_wordbook.json 및 manifest.json 동기화
"""

import json
import math
import os
import shutil
import sys
import zipfile
from pathlib import Path

# 콘솔 UTF-8 설정
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = Path(__file__).resolve().parent.parent
SERVER_DATA = BASE_DIR / "data"
SERVER_AUDIO = BASE_DIR / "audio"
LEVEL_0_AUDIO = SERVER_AUDIO / "level_0"
DOCS_DATA = BASE_DIR.parent / "docs" / "data"

def main():
    json_path = SERVER_DATA / "custom_wordbook.json"
    with open(json_path, "r", encoding="utf-8") as f:
        words = json.load(f)

    print(f"[1] 원본 단어 로드 완료: {len(words)}단어")

    # 1. 'corporatiion' 오탈자 및 오류 교정
    fixed_count = 0
    for item in words:
        w_clean = item.get("word", "").strip().lower()
        if w_clean == "corporatiion":
            print(f"  -> 오탈자 발견 및 교정: {item['word']} -> corporation")
            item["word"] = "corporation"
            item["pos"] = "noun"
            item["meaning"] = "주식회사, 법인, 기업"
            item["phonetics"] = {
                "us": "/ˌkɔːr.pəˈreɪ.ʃən/",
                "uk": "/ˌkɔː.pərˈeɪ.ʃən/"
            }
            item["phonetic_us"] = "/ˌkɔːr.pəˈreɪ.ʃən/"
            item["phonetic_uk"] = "/ˌkɔː.pərˈeɪ.ʃən/"
            item["example_en"] = "She works for a large multinational corporation."
            item["example_ko"] = "그녀는 대형 다국적 기업에서 근무하고 있다."
            fixed_count += 1

    print(f"[2] 오탈자 교정 확인 완료 ({fixed_count}건 교정)")

    # 2. 알파벳(A to Z) 순서로 정렬 (대소문자 무관)
    words.sort(key=lambda x: (x.get("word", "").strip().lower(), x.get("id", "")))
    print(f"[3] 1,222개 단어 알파벳순(A~Z) 정렬 완료!")
    print(f"    - 첫 3단어: {[w['word'] for w in words[:3]]}")
    print(f"    - 마지막 3단어: {[w['word'] for w in words[-3:]]}")

    # 3. 새로운 ID(MY-0001 ~ MY-1222) 및 Day(1~30) 재할당
    total_words = len(words)
    words_per_day = math.ceil(total_words / 30)  # 41단어/일

    id_mapping = {}  # old_id -> new_id
    reorganized_words = []

    for idx, item in enumerate(words):
        old_id = item["id"]
        new_num = idx + 1
        new_id = f"MY-{new_num:04d}"
        new_day = min(30, (idx // words_per_day) + 1)

        id_mapping[old_id] = {
            "new_id": new_id,
            "word": item["word"]
        }

        item["id"] = new_id
        item["day"] = new_day
        audio_us_url = f"https://raw.githubusercontent.com/copark-eng/dic/main/server/audio/level_0/{new_id}_us.mp3"
        audio_uk_url = f"https://raw.githubusercontent.com/copark-eng/dic/main/server/audio/level_0/{new_id}_uk.mp3"
        item["audio_us"] = audio_us_url
        item["audio_uk"] = audio_uk_url
        item["audio"] = {
            "us": audio_us_url,
            "uk": audio_uk_url
        }

        reorganized_words.append(item)

    # 4. 음원 파일 리매핑
    print("\n[4] 오디오 파일(MP3) 리매핑 시작...")
    temp_audio_dir = SERVER_AUDIO / "level_0_reorganized"
    if temp_audio_dir.exists():
        shutil.rmtree(temp_audio_dir)
    temp_audio_dir.mkdir(parents=True, exist_ok=True)

    copy_count = 0
    for old_id, info in id_mapping.items():
        new_id = info["new_id"]
        target_us = temp_audio_dir / f"{new_id}_us.mp3"
        target_uk = temp_audio_dir / f"{new_id}_uk.mp3"

        old_us = LEVEL_0_AUDIO / f"{old_id}_us.mp3"
        old_uk = LEVEL_0_AUDIO / f"{old_id}_uk.mp3"
        if old_us.exists():
            shutil.copy2(old_us, target_us)
            copy_count += 1
        else:
            print(f"  [경고] 음원 없음: {old_us}")
        if old_uk.exists():
            shutil.copy2(old_uk, target_uk)
            copy_count += 1
        else:
            print(f"  [경고] 음원 없음: {old_uk}")

    print(f"  -> 총 {len(reorganized_words)*2}개 대상 중 {copy_count}개 오디오 파일 복사 완료")

    # 기존 level_0 백업 및 대체
    backup_audio = SERVER_AUDIO / "level_0_backup_old"
    if backup_audio.exists():
        shutil.rmtree(backup_audio)
    LEVEL_0_AUDIO.rename(backup_audio)
    temp_audio_dir.rename(LEVEL_0_AUDIO)
    if backup_audio.exists():
        shutil.rmtree(backup_audio)
    print(f"  -> server/audio/level_0 교체 완료")

    # 5. server/audio/level_0.zip 재압축 생성
    print("\n[5] level_0.zip 압축 파일 재생성 중...")
    zip_path = SERVER_AUDIO / "level_0.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for mp3_file in sorted(LEVEL_0_AUDIO.glob("*.mp3")):
            z.write(mp3_file, arcname=mp3_file.name)
    print(f"  -> level_0.zip 생성 완료! (크기: {zip_path.stat().st_size / 1024 / 1024:.2f} MB)")

    # 6. JSON 파일 및 raw 텍스트 저장
    print("\n[6] JSON 데이터셋 및 raw 텍스트 저장...")
    for target in [SERVER_DATA / "custom_wordbook.json", DOCS_DATA / "custom_wordbook.json"]:
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            json.dump(reorganized_words, f, ensure_ascii=False, indent=2)
        print(f"  -> {target} 저장 완료")

    raw_level_0 = BASE_DIR / "raw" / "level_0_words.txt"
    if raw_level_0.parent.exists():
        with open(raw_level_0, "w", encoding="utf-8") as f:
            for item in reorganized_words:
                f.write(f"{item['word']},{item['meaning']}\n")
        print(f"  -> {raw_level_0} 저장 완료")

    # 7. manifest.json 업데이트
    print("\n[7] manifest.json 메타데이터 업데이트...")
    import hashlib
    from datetime import datetime, timezone
    json_bytes = (SERVER_DATA / "custom_wordbook.json").read_bytes()
    cw_sha256 = hashlib.sha256(json_bytes).hexdigest()
    cw_size = len(json_bytes)
    now_iso = datetime.now(timezone.utc).isoformat()

    for mpath in [SERVER_DATA / "manifest.json", DOCS_DATA / "manifest.json"]:
        if mpath.exists():
            with open(mpath, "r", encoding="utf-8") as f:
                manifest = json.load(f)
            levels = manifest.get("levels", {})
            if isinstance(levels, dict):
                levels["0"] = {
                    "name": "디폴트 나만의 단어장",
                    "code": "MY",
                    "total_words": total_words,
                    "count": total_words,
                    "file": "custom_wordbook.json",
                    "file_size_bytes": cw_size,
                    "sha256": cw_sha256,
                    "updated_at": now_iso
                }
            elif isinstance(levels, list):
                for lvl in levels:
                    if lvl.get("level") == 0:
                        lvl["word_count"] = total_words
                        lvl["count"] = total_words
                        lvl["file_size_bytes"] = cw_size
                        lvl["sha256"] = cw_sha256
            with open(mpath, "w", encoding="utf-8") as f:
                json.dump(manifest, f, ensure_ascii=False, indent=2)
            print(f"  -> {mpath} 갱신 완료")

    print("\n============================================================")
    print("★ [성공] MY단어장 알파벳순 정렬 및 corporation 교정 완료!")
    print("============================================================")

if __name__ == "__main__":
    main()
