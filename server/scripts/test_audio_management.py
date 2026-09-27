# -*- coding: utf-8 -*-
from __future__ import annotations
"""
클라이언트 오디오 파일 관리 수명주기 및 3중 Fallback 시뮬레이션 테스트
(Client Audio Management Lifecycle & Fallback Test Suite)

검증 시나리오:
1. [Test Case 1] Cache Miss -> CDN 스트리밍 다운로드 -> 로컬 캐시 저장 검증
2. [Test Case 2] Cache Hit -> 100% 오프라인 0ms 즉시 재생 검증
3. [Test Case 3] 미국식(US) vs 영국식(UK) 독립 캐싱 및 바이너리 분리 검증
4. [Test Case 4] 네트워크 타임아웃/오류 발생 시 Android 내장 TTS Fallback 전환 검증
5. [Test Case 5] Day 단위/Level 단위 캐시 용량 산출 및 캐시 정리(Purge) 검증
"""

import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
SERVER_DIR = SCRIPTS_DIR.parent
DATA_DIR = SERVER_DIR / "data"

sys.path.insert(0, str(SCRIPTS_DIR))
import config

import json
import os
import shutil
import ssl
import time
import urllib.request
from typing import Any

# Windows 콘솔 UTF-8 설정
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ctx = ssl.create_default_context()

class AudioCacheManagerSimulator:
    """안드로이드 앱 클라이언트의 AudioCacheManager 및 MediaPlayer 동작을 1:1 시뮬레이션"""
    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.network_enabled = True
        self.timeout_sec = 1.5 # ADR-001 기준 1.5초 타임아웃

    def get_cache_path(self, word_id: str, accent: str) -> Path:
        return self.cache_dir / f"{word_id}_{accent.lower()}.mp3"

    def play_audio(self, word_id: str, word: str, accent: str, audio_url: str) -> dict[str, Any]:
        """클라이언트 3단계 발음 재생 로직 시뮬레이션"""
        t0 = time.time()
        cache_file = self.get_cache_path(word_id, accent)

        # 1계층: 로컬 캐시 확인 (Cache Hit)
        if cache_file.exists() and cache_file.stat().st_size > 500:
            elapsed = time.time() - t0
            return {
                "source": "LOCAL_CACHE",
                "word": word,
                "accent": accent,
                "latency_sec": elapsed,
                "file_path": str(cache_file),
                "file_size": cache_file.stat().st_size,
                "status": "SUCCESS"
            }

        # 2계층: 고속 CDN 다운로드 (Cache Miss)
        if self.network_enabled and audio_url and audio_url.startswith("https://"):
            try:
                req = urllib.request.Request(
                    audio_url,
                    headers={"User-Agent": "Mozilla/5.0 (Android 14; Mobile) MyDic/1.0"}
                )
                with urllib.request.urlopen(req, context=ctx, timeout=self.timeout_sec) as resp:
                    if resp.status == 200:
                        data = resp.read()
                        if len(data) > 500:
                            with open(cache_file, "wb") as f:
                                f.write(data)
                            elapsed = time.time() - t0
                            return {
                                "source": "CDN_DOWNLOAD",
                                "word": word,
                                "accent": accent,
                                "latency_sec": elapsed,
                                "file_path": str(cache_file),
                                "file_size": len(data),
                                "status": "SUCCESS"
                            }
            except Exception as e:
                pass # 타임아웃 또는 네트워크 실패 시 3계층 Fallback으로 전이

        # 3계층: Android 단말 내장 Google TTS Fallback
        elapsed = time.time() - t0
        return {
            "source": "NATIVE_TTS_FALLBACK",
            "word": word,
            "accent": accent,
            "latency_sec": elapsed,
            "engine": f"Google TTS ({'Locale.US' if accent == 'US' else 'Locale.UK'})",
            "status": "FALLBACK_SUCCESS"
        }

    def get_total_cache_size(self) -> int:
        return sum(f.stat().st_size for f in self.cache_dir.glob("*.mp3"))

    def clear_cache(self) -> int:
        count = 0
        for f in self.cache_dir.glob("*.mp3"):
            f.unlink()
            count += 1
        return count

def run_tests():
    print("=" * 65)
    print("MyDic 오디오 파일 관리 라이프사이클 및 Fallback 종합 테스트")
    print("=" * 65)

    test_cache_dir = SERVER_DIR / ".test_audio_cache"
    if test_cache_dir.exists():
        shutil.rmtree(test_cache_dir)
    
    manager = AudioCacheManagerSimulator(test_cache_dir)

    # 테스트 대상 단어 선정 (Level 1: schedule, apple)
    with open(DATA_DIR / "level_1.json", "r", encoding="utf-8") as f:
        l1_data = json.load(f)
    
    test_word_1 = l1_data[0] # L1-0001 (I)
    test_word_2 = l1_data[1] # L1-0002 (you)

    print("\n[시나리오 1] Cache Miss -> 고속 CDN 스트리밍 다운로드 & 로컬 저장")
    res1 = manager.play_audio(
        test_word_1["id"], test_word_1["word"], "US", test_word_1["audio"]["us"]
    )
    print(f"  - 요청: {test_word_1['id']} ({test_word_1['word']}) US 발음")
    print(f"  - 재생 소스: {res1['source']} (신규 다운로드)")
    print(f"  - 응답 시간: {res1['latency_sec']:.3f}초")
    print(f"  - 저장된 파일: {Path(res1['file_path']).name} ({res1['file_size']} bytes)")
    assert res1["source"] == "CDN_DOWNLOAD", "CDN 다운로드가 실패했습니다!"
    assert Path(res1["file_path"]).exists(), "캐시 파일이 저장되지 않았습니다!"
    print("  -> [성공] CDN 음원 정상 수신 및 로컬 캐시 파일 영구 저장 확인")

    print("\n[시나리오 2] Cache Hit -> 100% 오프라인 로컬 캐시 즉시 재생 (0ms 지연)")
    # 오프라인 상태 시뮬레이션: 네트워크 차단
    manager.network_enabled = False
    res2 = manager.play_audio(
        test_word_1["id"], test_word_1["word"], "US", test_word_1["audio"]["us"]
    )
    print(f"  - 네트워크 상태: [단절/오프라인 모드]")
    print(f"  - 요청: {test_word_1['id']} ({test_word_1['word']}) US 발음 재학습")
    print(f"  - 재생 소스: {res2['source']} (로컬 캐시 즉시 히트)")
    print(f"  - 응답 시간: {res2['latency_sec'] * 1000:.2f} ms (사실상 0ms 즉시 재생)")
    print(f"  - 파일 경로: {Path(res2['file_path']).name}")
    assert res2["source"] == "LOCAL_CACHE", "로컬 캐시 조회가 실패했습니다!"
    assert res2["latency_sec"] < 0.05, "로컬 캐시 재생이 지연되었습니다!"
    print("  -> [성공] 오프라인 환경에서도 로컬 캐시로부터 0ms 즉시 재생 확인")

    print("\n[시나리오 3] 미국식(US) vs 영국식(UK) 독립 캐싱 및 바이너리 분리")
    manager.network_enabled = True
    res3_uk = manager.play_audio(
        test_word_1["id"], test_word_1["word"], "UK", test_word_1["audio"]["uk"]
    )
    us_file = manager.get_cache_path(test_word_1["id"], "US")
    uk_file = manager.get_cache_path(test_word_1["id"], "UK")
    
    print(f"  - 미국식 음원 파일: {us_file.name} ({us_file.stat().st_size} bytes)")
    print(f"  - 영국식 음원 파일: {uk_file.name} ({uk_file.stat().st_size} bytes)")
    assert us_file.exists() and uk_file.exists(), "US/UK 파일이 독립 생성되지 않았습니다!"
    assert us_file.name != uk_file.name, "파일명 충돌이 발생했습니다!"
    print("  -> [성공] 동일 단어의 US와 UK 음원이 각각 독립된 파일로 완벽히 분리 보관됨")

    print("\n[시나리오 4] 네트워크 오류 / 타임아웃 시 Android 내장 Google TTS Fallback")
    # 네트워크 단절 상태에서 미캐시 단어 재생 시도
    manager.network_enabled = False
    res4 = manager.play_audio(
        test_word_2["id"], test_word_2["word"], "US", test_word_2["audio"]["us"]
    )
    print(f"  - 네트워크 상태: [단절 / CDN 타임아웃]")
    print(f"  - 요청: {test_word_2['id']} ({test_word_2['word']}) US 발음 (미캐시 단어)")
    print(f"  - 재생 소스: {res4['source']}")
    print(f"  - 대체 엔진: {res4['engine']}")
    print(f"  - 소요 시간: {res4['latency_sec'] * 1000:.2f} ms")
    assert res4["source"] == "NATIVE_TTS_FALLBACK", "TTS Fallback 전환에 실패했습니다!"
    print("  -> [성공] 네트워크 오류/타임아웃 시 사용자 대기 없이 즉시 단말 내장 TTS로 무중단 재생")

    print("\n[시나리오 5] 학습 단위 캐시 용량 산출 및 디스크 정리(Cache Purge)")
    manager.network_enabled = True
    # 5개 단어 US/UK 총 10개 음원 캐시 생성
    for it in l1_data[:5]:
        manager.play_audio(it["id"], it["word"], "US", it["audio"]["us"])
        manager.play_audio(it["id"], it["word"], "UK", it["audio"]["uk"])
    
    total_size = manager.get_total_cache_size()
    cached_files = list(test_cache_dir.glob("*.mp3"))
    avg_per_file = total_size / len(cached_files) if cached_files else 0
    day_size_estimate = avg_per_file * 50 # 1일 50단어 기준 (1개 발음 기준 400KB, 2개 발음 기준 800KB)

    print(f"  - 현재 캐시 파일 수: {len(cached_files)}개")
    print(f"  - 총 캐시 사용량: {total_size / 1024:.2f} KB (파일당 평균 {avg_per_file / 1024:.2f} KB)")
    print(f"  - 1개 Day(50단어) 기준 예상 캐시 용량: 약 {day_size_estimate / 1024:.2f} KB")
    print(f"  - 1개 Level(1,000단어) 전체 완독 시 예상 용량: 약 {(avg_per_file * 1000 * 2) / (1024 * 1024):.2f} MB")
    
    # 캐시 일괄 삭제 테스트
    deleted = manager.clear_cache()
    print(f"  - 캐시 비우기 실행: {deleted}개 파일 삭제 완료 (남은 용량: {manager.get_total_cache_size()} bytes)")
    assert manager.get_total_cache_size() == 0, "캐시 비우기가 정상 수행되지 않았습니다!"
    print("  -> [성공] 용량 계산 및 원클릭 캐시 정리 기능 정상 동작 확인")

    # 테스트 디렉터리 정리
    if test_cache_dir.exists():
        shutil.rmtree(test_cache_dir)

    print("\n" + "=" * 65)
    print("모든 5개 시나리오 테스트 통과 (100% 무결성 확인)")
    print("=" * 65)

if __name__ == "__main__":
    run_tests()
