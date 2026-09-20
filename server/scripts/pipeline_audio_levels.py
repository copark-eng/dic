# -*- coding: utf-8 -*-
from __future__ import annotations
"""
MyDic 2단계~7단계 오디오 파일 순차 구축 및 자동 배포 파이프라인 (Audio Levels Pipeline)
Level 2부터 Level 7까지 순차적으로:
1. 미국식/영국식 물리 MP3 파일 다운로드 및 무결성 검증 (server/audio/level_{n}/)
2. server/data/level_{n}.json 오디오 URL을 GitHub Raw CDN 경로로 갱신
3. server/data/manifest.json 체크섬 및 메타데이터 갱신
4. 레벨별 Git Add -> Commit -> GitHub Push 자동 실행
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

import subprocess
import time
from download_audio_files import download_level_audios

# 콘솔 출력 UTF-8 설정
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

def run_cmd(cmd: list[str], max_retries: int = 3) -> bool:
    for attempt in range(1, max_retries + 1):
        try:
            res = subprocess.run(cmd, cwd=str(SERVER_DIR.parent), capture_output=True, text=True, check=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"  [경고] 명령어 실패 (시도 {attempt}/{max_retries}): {' '.join(cmd)}")
            print(f"  오류 내용: {e.stderr[:200]}")
            if attempt < max_retries:
                time.sleep(3 * attempt)
    return False

def process_level(level: int, workers: int = 16) -> bool:
    print("\n" + "=" * 70)
    print(f"▶ [Level {level}] 오디오 다운로드 및 GitHub CDN 배포 시작")
    print("=" * 70)

    # 1. 음원 다운로드 및 바이너리 검증
    dl_res = download_level_audios(level=level, workers=workers)
    if not dl_res["success"] and dl_res["failed"] > 50:
        print(f"[오류] Level {level} 다운로드 실패율이 너무 높습니다. ({dl_res['failed']}건 실패)")
        return False

    # 2. enrich_level_dataset.py 실행하여 JSON 오디오 URL 및 manifest 갱신
    print(f"\n[Level {level}] JSON 데이터셋 및 manifest.json 갱신 중...")
    enrich_cmd = [sys.executable, str(SCRIPTS_DIR / "enrich_level_dataset.py"), "--level", str(level)]
    if not run_cmd(enrich_cmd):
        print(f"[오류] Level {level} JSON 갱신 실패")
        return False

    # 3. Git Stage & Commit & Push
    audio_rel = f"server/audio/level_{level}"
    json_rel = f"server/data/level_{level}.json"
    manifest_rel = "server/data/manifest.json"

    print(f"\n[Level {level}] Git 스테이징 및 커밋 생성 중...")
    add_cmd = ["git", "add", audio_rel, json_rel, manifest_rel]
    if not run_cmd(add_cmd):
        print(f"[오류] Git add 실패")
        return False

    commit_msg = f"feat: add {dl_res['total']:,} physical MP3 audio files for Level {level}"
    commit_cmd = ["git", "commit", "-m", commit_msg]
    if not run_cmd(commit_cmd):
        print(f"[정보] 커밋할 변경사항이 없거나 이미 커밋되었습니다.")

    print(f"\n[Level {level}] GitHub 원격 저장소 푸시 중 (origin main)...")
    push_cmd = ["git", "push", "origin", "main"]
    if not run_cmd(push_cmd, max_retries=3):
        print(f"[오류] GitHub push 실패")
        return False

    print(f"★ [Level {level}] 배포 완료! ({dl_res['total']:,}개 MP3 파일, {dl_res['total_bytes'] / (1024*1024):.2f} MB)")
    return True

def main():
    import argparse
    parser = argparse.ArgumentParser(description="MyDic 2~7단계 오디오 자동 구축 및 배포 파이프라인")
    parser.add_argument("--start", type=int, default=2, choices=range(1, 8), help="시작 레벨 (기본값: 2)")
    parser.add_argument("--end", type=int, default=7, choices=range(1, 8), help="종료 레벨 (기본값: 7)")
    parser.add_argument("--workers", type=int, default=16, help="동시 다운로드 스레드 수 (기본값: 16)")
    args = parser.parse_args()

    total_levels = list(range(args.start, args.end + 1))
    print("=" * 70)
    print(f"MyDic 오디오 전 레벨 자동 구축 및 배포 시작 (Level {args.start} ~ Level {args.end})")
    print(f"대상 레벨: {total_levels}")
    print("=" * 70)

    start_all = time.time()
    success_levels = []
    failed_levels = []

    for lvl in total_levels:
        lvl_start = time.time()
        ok = process_level(lvl, workers=args.workers)
        if ok:
            success_levels.append(lvl)
        else:
            failed_levels.append(lvl)
            print(f"[경고] Level {lvl} 실패로 중단합니다.")
            break

    elapsed_all = time.time() - start_all
    print("\n" + "=" * 70)
    print("전체 파이프라인 실행 결과 요약")
    print("=" * 70)
    print(f"성공 완료 레벨: {success_levels}")
    if failed_levels:
        print(f"실패 레벨: {failed_levels}")
    print(f"총 소요 시간: {elapsed_all / 60:.2f}분")
    print("=" * 70)

if __name__ == "__main__":
    main()
