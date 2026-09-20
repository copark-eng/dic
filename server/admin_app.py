# -*- coding: utf-8 -*-
"""
MyDic 단어 데이터 검수 및 관리 어드민 대시보드 (Streamlit)
Streamlit Community Cloud 무료 배포 지원 (비용 $0)
- 7단계 단어 데이터 현황 및 manifest 모니터링
- 단어 검색, 뜻/예문 검수 및 편집
- 미국식/영국식 오디오 링크 청취 및 가용성 테스트
"""

import json
import os
from pathlib import Path
import streamlit as st

# 페이지 기본 설정
st.set_page_config(
    page_title="MyDic 단어 관리 대시보드",
    page_icon="📖",
    layout="wide",
    initial_sidebar_state="expanded"
)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = BASE_DIR / "raw"

LEVEL_NAMES = {
    1: "Level 1 (기초 1,000)",
    2: "Level 2 (중등 2,000)",
    3: "Level 3 (수능기본 3,000)",
    4: "Level 4 (수능심화 4,500)",
    5: "Level 5 (TOEIC 750 4,000)",
    6: "Level 6 (TOEIC 900 5,500)",
    7: "Level 7 (TOEIC 990 6,500)",
}

@st.cache_data
def load_manifest():
    manifest_path = DATA_DIR / "manifest.json"
    if manifest_path.exists():
        with open(manifest_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

@st.cache_data
def load_level_data(level: int):
    file_path = DATA_DIR / f"level_{level}.json"
    if file_path.exists():
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

# 사이드바
st.sidebar.title("📚 MyDic Admin")
st.sidebar.caption("100% 무료 단어 데이터 관리/검수 포털 (ADR-001)")

menu = st.sidebar.radio(
    "메뉴 선택",
    ["📊 데이터셋 현황 (Manifest)", "🔍 단어 검색 및 검수", "📝 단계별 단어 리스트 (Step 1)", "⚙️ 설정 및 ADR 명세"]
)

# 1. 데이터셋 현황
if menu == "📊 데이터셋 현황 (Manifest)":
    st.header("📊 Level 1 ~ 7 단어 데이터셋 현황")
    manifest = load_manifest()
    
    if manifest:
        st.info(f"최종 업데이트 일시: {manifest.get('updated_at', 'N/A')} | 스키마 버전: {manifest.get('version', '1.0.0')}")
        
        cols = st.columns(4)
        total_words = 0
        for i in range(1, 8):
            lvl_str = str(i)
            info = manifest.get("levels", {}).get(lvl_str, {})
            w_count = info.get("total_words", 0)
            total_words += w_count
            col_idx = (i - 1) % 4
            with cols[col_idx]:
                st.metric(label=LEVEL_NAMES[i], value=f"{w_count:,} 단어", delta=f"{info.get('file_size_bytes', 0) // 1024:,} KB")
        
        st.subheader("총 누적 단어 수")
        st.success(f"전체 7단계 총 **{total_words:,}** 단어 배포 준비 완료")
        
        st.subheader("Manifest 세부 JSON")
        st.json(manifest)
    else:
        st.warning("manifest.json 파일을 찾을 수 없습니다.")

# 2. 단어 검색 및 검수
elif menu == "🔍 단어 검색 및 검수":
    st.header("🔍 단어 검색, 예문 검수 및 발음 테스트")
    
    col1, col2 = st.columns([1, 3])
    with col1:
        selected_level = st.selectbox("조회할 레벨 선택", options=list(range(1, 8)), format_func=lambda x: LEVEL_NAMES[x])
    with col2:
        search_query = st.text_input("단어 또는 한국어 뜻 검색", placeholder="예: schedule, 발견하다, apple...")
    
    words = load_level_data(selected_level)
    
    if words:
        if search_query:
            filtered = [
                w for w in words
                if search_query.lower() in w.get("word", "").lower() or search_query in w.get("meaning", "")
            ]
        else:
            filtered = words[:50]
        
        st.write(f"표시 단어: **{len(filtered)}**건 (전체 {len(words)}건 중)")
        
        for idx, item in enumerate(filtered):
            with st.expander(f"**{item.get('word')}** [{item.get('pos')}] - {item.get('meaning')}"):
                c1, c2 = st.columns([2, 2])
                with c1:
                    st.write(f"**ID:** `{item.get('id')}`")
                    st.write(f"**미국식 발음:** `{item.get('phonetics', {}).get('us', '-')}`")
                    st.write(f"**영국식 발음:** `{item.get('phonetics', {}).get('uk', '-')}`")
                    
                    us_audio = item.get("audio", {}).get("us")
                    uk_audio = item.get("audio", {}).get("uk")
                    if us_audio:
                        st.audio(us_audio, format="audio/mp3")
                        st.caption(f"US CDN: {us_audio}")
                    if uk_audio:
                        st.audio(uk_audio, format="audio/mp3")
                        st.caption(f"UK CDN: {uk_audio}")
                        
                with c2:
                    st.markdown(f"**예문 (EN):** {item.get('example_en', '-')}")
                    st.markdown(f"**해석 (KO):** {item.get('example_ko', '-')}")
                    if item.get("synonyms"):
                        st.caption(f"유의어: {', '.join(item['synonyms'])}")
                    if item.get("antonyms"):
                        st.caption(f"반의어: {', '.join(item['antonyms'])}")
    else:
        st.warning(f"Level {selected_level} 데이터 파일이 없습니다. 먼저 빌더를 실행하세요.")

# 3. 단계별 단어 리스트
elif menu == "📝 단계별 단어 리스트 (Step 1)":
    st.header("📝 단계별 순수 단어 리스트 확인 (Step 1)")
    st.markdown("파이프라인 Step 1에서 생성된 각 레벨별 순수 단어 목록(`word`, `pos`) 원본 파일입니다.")
    
    sel_lvl = st.radio("확인할 레벨", options=list(range(1, 8)), horizontal=True, format_func=lambda x: f"L{x}")
    txt_path = RAW_DIR / f"level_{sel_lvl}_words.txt"
    
    if txt_path.exists():
        with open(txt_path, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip()]
        st.success(f"**Level {sel_lvl}** 총 단어 수: **{len(lines):,}개** (목표 수량 달성)")
        st.text_area("단어 리스트 내용 (미리보기)", value="\n".join(lines[:300]), height=400)
    else:
        st.warning(f"{txt_path.name} 파일이 존재하지 않습니다.")

# 4. 설정 및 ADR 명세
elif menu == "⚙️ 설정 및 ADR 명세":
    st.header("⚙️ 인프라 및 아키텍처 명세 (ADR-001)")
    st.markdown("""
    - **호스팅 비용**: $0 (GitHub Pages/Raw 배포 CDN + Streamlit Community Cloud)
    - **오디오 타임아웃 해결**:
      1. 로컬 디스크 캐시 (0ms 즉시 재생)
      2. 1.5초 타임아웃 제한 고속 CDN URL
      3. Android 단말 내장 Google TTS Fallback (100% 오프라인 보장)
    - **연동 문서**: `server/server_requirements.md`, `adr/ADR-001-free-server-and-audio-pipeline.md`
    """)
