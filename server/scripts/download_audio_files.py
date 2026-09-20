# -*- coding: utf-8 -*-
from __future__ import annotations
"""
MyDic 오디오 파일 일괄 다운로더 (Download Audio Files)
레벨별 JSON 데이터셋을 읽어 단어별 미국식(US)/영국식(UK) MP3 음원을
고속 멀티스레드로 다운로드하고 바이너리 무결성을 검증하여
server/audio/level_{n}/ 디렉터리에 영구 저장합니다. (100% 무료 서버 배포용)
"""

from pathlib import Path
import sys
import os

SCRIPTS_DIR = Path(__file__).resolve().parent
SERVER_DIR = SCRIPTS_DIR.parent
DATA_DIR = SERVER_DIR / "data"
AUDIO_DIR = SERVER_DIR / "audio"

sys.path.insert(0, str(SCRIPTS_DIR))
import config

import argparse
import concurrent.futures
import json
import ssl
import time
import urllib.parse
import urllib.request
from typing import Any


# 콘솔 출력 UTF-8 설정
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ssl_ctx = ssl.create_default_context()

def check_mp3_binary(data: bytes) -> bool:
    """MPEG Audio Frame Sync(0xFF 0xEx/0xFx) 또는 ID3 태그 유효성 확인"""
    if len(data) < 128:
        return False
    if data[:3] == b"ID3":
        return True
    if data[0] == 0xFF and (data[1] & 0xE0) == 0xE0:
        return True
    return False

def download_audio_single(
    word: str,
    accent: str,
    entry_id: str,
    target_path: Path,
    max_retries: int = 3
) -> tuple[bool, str, int]:
    """단일 단어 음원 다운로드 및 무결성 검증 후 로컬 저장"""
    if target_path.exists() and target_path.stat().st_size > 500:
        # 이미 존재하는 파일의 바이너리 검증
        try:
            with open(target_path, "rb") as f:
                header = f.read(512)
            if check_mp3_binary(header):
                return True, "already_exists", target_path.stat().st_size
        except Exception:
            pass

    lang_code = "en-US" if accent == "us" else "en-GB"
    encoded_word = urllib.parse.quote(word.lower())
    url = f"https://translate.google.com/translate_tts?ie=UTF-8&tl={lang_code}&client=tw-ob&q={encoded_word}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    temp_path = target_path.with_suffix(".tmp")

    for attempt in range(1, max_retries + 1):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, context=ssl_ctx, timeout=6.0) as resp:
                if resp.status != 200:
                    time.sleep(0.3 * attempt)
                    continue
                data = resp.read()
                if len(data) > 400 and check_mp3_binary(data):
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(temp_path, "wb") as f:
                        f.write(data)
                    temp_path.replace(target_path)
                    return True, "downloaded", len(data)
        except Exception:
            time.sleep(0.4 * attempt)

    return False, f"failed after {max_retries} attempts", 0

def download_level_audios(level: int, workers: int = 12, force: bool = False) -> dict[str, Any]:
    json_path = DATA_DIR / f"level_{level}.json"
    if not json_path.exists():
        print(f"[오류] {json_path.name} 파일이 존재하지 않습니다.")
        return {"success": False, "total": 0, "downloaded": 0, "failed": 0}

    with open(json_path, "r", encoding="utf-8") as f:
        words_data = json.load(f)

    level_audio_dir = AUDIO_DIR / f"level_{level}"
    level_audio_dir.mkdir(parents=True, exist_ok=True)

    tasks: list[tuple[str, str, str, Path]] = []
    for entry in words_data:
        w = entry["word"]
        entry_id = entry["id"]
        
        # US 음원 작업
        us_path = level_audio_dir / f"{entry_id}_us.mp3"
        tasks.append((w, "us", entry_id, us_path))
        
        # UK 음원 작업
        uk_path = level_audio_dir / f"{entry_id}_uk.mp3"
        tasks.append((w, "uk", entry_id, uk_path))

    total_tasks = len(tasks)
    print(f"\n[Level {level}] 총 {len(words_data):,}개 단어, {total_tasks:,}개 오디오 다운로드 시작...")
    print(f"  - 저장 경로: {level_audio_dir}")
    print(f"  - 워커 수: {workers} threads")

    start_time = time.time()
    completed_count = 0
    downloaded_count = 0
    cached_count = 0
    failed_tasks = []
    total_bytes = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        future_map = {
            executor.submit(download_audio_single, w, accent, eid, path): (w, accent, eid)
            for w, accent, eid, path in tasks
        }

        for future in concurrent.futures.as_completed(future_map):
            w, accent, eid = future_map[future]
            ok, msg, size = future.result()
            completed_count += 1
            if ok:
                total_bytes += size
                if msg == "downloaded":
                    downloaded_count += 1
                else:
                    cached_count += 1
            else:
                failed_tasks.append((eid, w, accent, msg))

            if completed_count % 200 == 0 or completed_count == total_tasks:
                pct = (completed_count / total_tasks) * 100
                elapsed = time.time() - start_time
                speed = completed_count / elapsed if elapsed > 0 else 0
                print(f"  진행률: [{completed_count:4d}/{total_tasks}] ({pct:5.1f}%) - {speed:.1f} files/sec (성공: {downloaded_count + cached_count}, 실패: {len(failed_tasks)})")

    elapsed_total = time.time() - start_time
    print("-" * 65)
    print(f"[Level {level} 완료 보고서]")
    print(f"  - 전체 음원: {total_tasks}개")
    print(f"  - 신규 다운로드: {downloaded_count}개")
    print(f"  - 기존 보관: {cached_count}개")
    print(f"  - 실패: {len(failed_tasks)}개")
    print(f"  - 총 용량: {total_bytes / (1024 * 1024):.2f} MB")
    print(f"  - 총 소요 시간: {elapsed_total:.2f}초")

    if failed_tasks:
        print(f"  [경고] 실패 항목 샘플: {failed_tasks[:3]}")

    return {
        "success": len(failed_tasks) == 0,
        "total": total_tasks,
        "downloaded": downloaded_count,
        "cached": cached_count,
        "failed": len(failed_tasks),
        "total_bytes": total_bytes,
        "time_sec": elapsed_total
    }

def main():
    parser = argparse.ArgumentParser(description="MyDic 오디오 파일 일괄 다운로더")
    parser.add_argument("--level", type=int, default=1, choices=range(1, 8), help="다운로드할 레벨 (기본값: 1)")
    parser.add_argument("--workers", type=int, default=12, help="동시 스레드 수 (기본값: 12)")
    parser.add_argument("--force", action="store_true", help="기존 파일 덮어쓰기")
    args = parser.parse_args()

    print("=" * 65)
    print("MyDic 실제 MP3 오디오 파일 서버 구축 (100% 무료 서버 호스팅)")
    print("=" * 65)

    download_level_audios(level=args.level, workers=args.workers, force=args.force)

if __name__ == "__main__":
    main()
