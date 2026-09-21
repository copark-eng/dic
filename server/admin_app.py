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
import sys
from pathlib import Path
import streamlit as st
import pandas as pd

# scripts 모듈 경로 추가
sys.path.insert(0, str(Path(__file__).resolve().parent / "scripts"))
try:
    from import_custom_wordbook import (
        generate_sample_template,
        parse_and_build_custom_wordbook,
        save_and_sync,
    )
except ImportError:
    from scripts.import_custom_wordbook import (
        generate_sample_template,
        parse_and_build_custom_wordbook,
        save_and_sync,
    )

# 페이지 기본 설정
st.set_page_config(
    page_title="MyDic 단어 관리 대시보드",
    page_icon="📖",
    layout="wide",
    initial_sidebar_state="expanded"
)

BASE_DIR = Path(__file__).resolve().parent
SERVER_DIR = BASE_DIR
DATA_DIR = BASE_DIR / "data"
RAW_DIR = BASE_DIR / "raw"
AUDIO_DIR = BASE_DIR / "audio"

LEVEL_NAMES = {
    -1: "전체 레벨 (All 26,500+단어)",
    0: "⭐️ 디폴트 나만의 단어장 (MY)",
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
    if level == 0:
        file_path = DATA_DIR / "custom_wordbook.json"
    else:
        file_path = DATA_DIR / f"level_{level}.json"
    if file_path.exists():
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

@st.cache_data
def load_all_words():
    combined = []
    # 디폴트 나만의 단어장이 있으면 포함
    custom_data = load_level_data(0)
    if custom_data:
        combined.extend(custom_data)
    for lvl in range(1, 8):
        data = load_level_data(lvl)
        combined.extend(data)
    return combined

# 사이드바
st.sidebar.title("📚 MyDic Admin")
st.sidebar.caption("100% 무료 단어 데이터 관리/검수 포털 (ADR-001)")

menu = st.sidebar.radio(
    "메뉴 선택",
    [
        "📊 데이터셋 현황 (Manifest)",
        "📥 엑셀 단어장 업로드 (디폴트 나만의 단어장)",
        "🔍 단어 검색 및 검수",
        "📝 단계별 단어 리스트 (Step 1)",
        "⚙️ 설정 및 ADR 명세"
    ]
)

# 1. 데이터셋 현황
if menu == "📊 데이터셋 현황 (Manifest)":
    st.header("📊 단어 데이터셋 현황 (Manifest)")
    manifest = load_manifest()
    
    if manifest:
        st.info(f"최종 업데이트 일시: {manifest.get('updated_at', 'N/A')} | 스키마 버전: {manifest.get('version', '1.0.0')}")
        
        levels_dict = manifest.get("levels", {})
        custom_info = levels_dict.get("0") or levels_dict.get("custom")
        if custom_info:
            st.subheader("⭐️ 디폴트 나만의 단어장 (MY)")
            st.metric(
                label="디폴트 나만의 단어장",
                value=f"{custom_info.get('total_words', custom_info.get('count', 0)):,} 단어",
                delta=f"{custom_info.get('file_size_bytes', 0) // 1024:,} KB"
            )

        st.subheader("공식 7단계 레벨별 현황")
        cols = st.columns(4)
        total_words = 0
        for i in range(1, 8):
            lvl_str = str(i)
            info = levels_dict.get(lvl_str, {})
            w_count = info.get("total_words", info.get("count", 0))
            total_words += w_count
            col_idx = (i - 1) % 4
            with cols[col_idx]:
                st.metric(label=LEVEL_NAMES[i], value=f"{w_count:,} 단어", delta=f"{info.get('file_size_bytes', 0) // 1024:,} KB")
        
        if custom_info:
            c_cnt = custom_info.get("total_words", custom_info.get("count", 0))
            total_words += c_cnt

        st.subheader("총 누적 단어 수")
        st.success(f"전체 총 **{total_words:,}** 단어 배포 준비 완료")
        
        st.subheader("Manifest 세부 JSON")
        st.json(manifest)
    else:
        st.warning("manifest.json 파일을 찾을 수 없습니다.")

# 2. 엑셀 단어장 업로드
elif menu == "📥 엑셀 단어장 업로드 (디폴트 나만의 단어장)":
    st.header("📥 디폴트 나만의 단어장 엑셀 업로드 및 배포")
    st.markdown("""
    사용자가 직접 작성한 엑셀 파일(`.xlsx`, `.xls`) 또는 `.csv` 파일을 업로드하여 
    **디폴트 나만의 단어장 (Level 0 / MY)** 데이터셋을 생성하고, 서버 및 모바일 앱에 즉시 배포합니다.
    """)

    col_t1, col_t2 = st.columns([2, 1])
    with col_t1:
        st.subheader("1. 엑셀 표준 템플릿 준비")
        st.write("아래 컬럼이 포함된 엑셀 파일을 준비해 주세요:")
        st.code("단어(word) | 품사(pos) | 뜻(meaning) | 영어예문(example_en) | 예문해석(example_ko) | 발음기호(phonetic)", language="markdown")
        st.caption("※ '단어'와 '뜻'은 필수 컬럼이며, 예문과 발음기호가 비어있을 경우 자동으로 기본 예문 및 발음 URL이 보정 생성됩니다.")

    with col_t2:
        st.subheader("템플릿 다운로드")
        template_file = DATA_DIR / "sample_my_wordbook.xlsx"
        if not template_file.exists():
            generate_sample_template(template_file)
        with open(template_file, "rb") as f:
            template_bytes = f.read()
        st.download_button(
            label="📥 표준 엑셀 템플릿 다운로드 (.xlsx)",
            data=template_bytes,
            file_name="sample_my_wordbook.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

    st.divider()
    st.subheader("2. 단어 데이터 입력 (파일 업로드 또는 텍스트 직접 붙여넣기)")
    tab_file, tab_text = st.tabs(["📁 엑셀 / CSV 파일 업로드", "✍️ 텍스트 직접 붙여넣기 (apple 사과 형식)"])

    if "custom_wordbook_parsed" not in st.session_state:
        st.session_state["custom_wordbook_parsed"] = None

    with tab_file:
        uploaded_file = st.file_uploader(
            "엑셀 파일(.xlsx, .xls) 또는 CSV / TXT 파일을 선택하세요",
            type=["xlsx", "xls", "csv", "txt"],
            help="단어와 뜻이 기재된 파일을 업로드하세요. 헤더가 없는 단순 2열(단어, 뜻) 파일도 자동 지원됩니다."
        )
        if uploaded_file is not None:
            try:
                with st.spinner("파일을 파싱 및 검증하는 중입니다..."):
                    st.session_state["custom_wordbook_parsed"] = parse_and_build_custom_wordbook(uploaded_file, uploaded_file.name)
            except Exception as e:
                st.error(f"파일 파싱 중 오류가 발생했습니다: {e}")

    with tab_text:
        st.caption("메모장이나 엑셀에서 복사한 '단어 뜻' 목록을 아래에 그대로 붙여넣으세요. (공백, 탭, 콜론 구분 모두 지원)")
        raw_text = st.text_area(
            "단어 목록 붙여넣기",
            placeholder="apple 사과\nbanana 바나나\norange 오렌지, 감귤류\n...",
            height=200
        )
        if st.button("📋 붙여넣은 텍스트 인식 및 변환", use_container_width=True):
            if raw_text.strip():
                try:
                    with st.spinner("텍스트 파싱 중..."):
                        st.session_state["custom_wordbook_parsed"] = parse_and_build_custom_wordbook(raw_text)
                except Exception as e:
                    st.error(f"텍스트 파싱 중 오류가 발생했습니다: {e}")
            else:
                st.warning("붙여넣을 텍스트를 입력해 주세요.")

    parsed_data = st.session_state.get("custom_wordbook_parsed")
    if parsed_data is not None:
        total_words = parsed_data["total_words"]
        words_list = parsed_data["words"]
        st.success(f"총 **{total_words:,}**개의 단어가 성공적으로 인식되었습니다!")

        # 미리보기 표
        preview_rows = []
        for w in words_list:
            preview_rows.append({
                "ID": w["id"],
                "Day": f"Day {w['day']:02d}",
                "단어": w["word"],
                "품사": w["pos"],
                "뜻": w["meaning"],
                "발음기호": w.get("phonetic_us", "-"),
                "영어예문": w.get("example_en", "-"),
                "예문해석": w.get("example_ko", "-"),
            })
        
        st.dataframe(pd.DataFrame(preview_rows), use_container_width=True, height=350)

        # 배포 실행 버튼
        st.subheader("3. 단어장 생성 및 앱/서버 동기화")
        if st.button("🚀 디폴트 단어장 저장 및 앱/서버 배포", type="primary", use_container_width=True):
            with st.spinner("단어장 JSON 생성, manifest 갱신 및 앱 assets 동기화 중..."):
                sync_result = save_and_sync(parsed_data)
                st.cache_data.clear()
            st.balloons()
            st.success(f"🎉 디폴트 나만의 단어장이 성공적으로 배포되었습니다!\n"
                       f"- 총 단어 수: {sync_result['total_words']:,}단어\n"
                       f"- JSON 용량: {sync_result['file_size_bytes']:,} bytes\n"
                       f"- 앱 assets(`app/assets/data/custom_wordbook.json`) 동기화 완료")

# 3. 단어 검색 및 검수
elif menu == "🔍 단어 검색 및 검수":
    st.header("🔍 단어 검색, 예문 검수 및 발음 테스트")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        selected_level = st.selectbox(
            "조회할 레벨 선택",
            options=[-1, 0, 1, 2, 3, 4, 5, 6, 7],
            format_func=lambda x: LEVEL_NAMES[x],
            index=1,  # Default to Level 0 (디폴트 나만의 단어장)
        )
    with col2:
        search_query = st.text_input("단어 또는 한국어 뜻 검색", placeholder="예: schedule, 발견하다, apple...")
    
    # State key to detect filter changes and reset page to 1
    current_filter_key = f"{selected_level}::{search_query.strip().lower()}"
    if st.session_state.get("last_filter_key") != current_filter_key:
        st.session_state.last_filter_key = current_filter_key
        st.session_state.admin_page = 1

    if selected_level == -1:
        words = load_all_words()
    elif selected_level == 0:
        words = load_level_data(0)
    else:
        words = load_level_data(selected_level)
    
    if words:
        if search_query:
            q = search_query.strip().lower()
            filtered = [
                w for w in words
                if q in w.get("word", "").lower() or q in w.get("meaning", "").lower()
            ]
        else:
            filtered = words
        
        total_items = len(filtered)
        
        if total_items == 0:
            st.warning("검색 조건에 일치하는 단어가 없습니다.")
        else:
            # 페이징 컨트롤 바
            ctrl_col1, ctrl_col2, ctrl_col3 = st.columns([2, 2, 2])
            with ctrl_col1:
                page_size = st.selectbox(
                    "페이지당 단어 수",
                    options=[20, 50, 100, 200, 500],
                    index=1,
                    key="admin_page_size",
                )
            
            total_pages = max(1, (total_items + page_size - 1) // page_size)
            
            if "admin_page" not in st.session_state:
                st.session_state.admin_page = 1
            if st.session_state.admin_page > total_pages:
                st.session_state.admin_page = total_pages
            if st.session_state.admin_page < 1:
                st.session_state.admin_page = 1

            with ctrl_col2:
                page_input = st.number_input(
                    f"페이지 번호 (1 ~ {total_pages})",
                    min_value=1,
                    max_value=total_pages,
                    value=st.session_state.admin_page,
                    step=1,
                    key="page_input_widget",
                )
                if page_input != st.session_state.admin_page:
                    st.session_state.admin_page = page_input
                    st.rerun()

            with ctrl_col3:
                view_mode = st.radio(
                    "화면 표시 형태",
                    options=["상세 카드 (오디오/예문)", "빠른 표 (테이블)"],
                    horizontal=True,
                )

            # 이전/다음 네비게이션 버튼
            btn1, btn2, btn3, btn4 = st.columns([1, 1, 1, 3])
            with btn1:
                if st.button("⏮ 처음", disabled=(st.session_state.admin_page <= 1)):
                    st.session_state.admin_page = 1
                    st.rerun()
            with btn2:
                if st.button("◀ 이전", disabled=(st.session_state.admin_page <= 1)):
                    st.session_state.admin_page -= 1
                    st.rerun()
            with btn3:
                if st.button("다음 ▶", disabled=(st.session_state.admin_page >= total_pages)):
                    st.session_state.admin_page += 1
                    st.rerun()
            with btn4:
                if st.button("끝 ⏭", disabled=(st.session_state.admin_page >= total_pages)):
                    st.session_state.admin_page = total_pages
                    st.rerun()

            start_idx = (st.session_state.admin_page - 1) * page_size
            end_idx = min(start_idx + page_size, total_items)

            st.success(
                f"총 **{total_items:,}**개 단어 중 **{start_idx + 1:,} ~ {end_idx:,}**번째 표시 (페이지 **{st.session_state.admin_page} / {total_pages}**)"
            )

            page_items = filtered[start_idx:end_idx]

            if view_mode == "빠른 표 (테이블)":
                table_rows = []
                for w in page_items:
                    p_us = (w.get("phonetics") or {}).get("us") or w.get("phonetic_us") or "-"
                    p_uk = (w.get("phonetics") or {}).get("uk") or w.get("phonetic_uk") or "-"
                    table_rows.append({
                        "Level": f"L{w.get('level', selected_level)}",
                        "ID": w.get("id"),
                        "단어": w.get("word"),
                        "품사": w.get("pos"),
                        "뜻": w.get("meaning"),
                        "미국식 발음": p_us,
                        "영국식 발음": p_uk,
                        "예문(EN)": w.get("example_en", "-"),
                        "해석(KO)": w.get("example_ko", "-"),
                    })
                st.dataframe(table_rows, use_container_width=True, height=600)
            else:
                import urllib.parse
                for idx, item in enumerate(page_items):
                    item_lvl = item.get("level", selected_level)
                    with st.expander(f"**[{item.get('id')}] {item.get('word')}** (Level {item_lvl}, {item.get('pos')}) - {item.get('meaning')}"):
                        c1, c2 = st.columns([2, 2])
                        with c1:
                            st.write(f"**ID:** `{item.get('id')}` | **레벨:** `Level {item_lvl}`")
                            p_us = (item.get("phonetics") or {}).get("us") or item.get("phonetic_us") or "-"
                            p_uk = (item.get("phonetics") or {}).get("uk") or item.get("phonetic_uk") or "-"
                            st.write(f"**미국식 발음:** `{p_us}`")
                            st.write(f"**영국식 발음:** `{p_uk}`")
                            
                            entry_id = item.get("id", "")
                            clean_word = urllib.parse.quote(str(item.get("word", "")).strip())
                            local_us = AUDIO_DIR / f"level_{item_lvl}" / f"{entry_id}_us.mp3"
                            local_uk = AUDIO_DIR / f"level_{item_lvl}" / f"{entry_id}_uk.mp3"

                            us_audio = (item.get("audio") or {}).get("us") or item.get("audio_us")
                            uk_audio = (item.get("audio") or {}).get("uk") or item.get("audio_uk")

                            # 신뢰할 수 있는 음원 URL 보정
                            if not us_audio or "dictionaryapi.dev" in us_audio:
                                us_audio = f"https://dict.youdao.com/dictvoice?audio={clean_word}&type=2"
                            if not uk_audio or "dictionaryapi.dev" in uk_audio:
                                uk_audio = f"https://dict.youdao.com/dictvoice?audio={clean_word}&type=1"

                            if local_us.exists():
                                st.audio(str(local_us), format="audio/mp3")
                                st.caption(f"US (Local File): {local_us.name}")
                            elif us_audio:
                                st.audio(us_audio, format="audio/mp3")
                                st.caption(f"US 발음: {us_audio}")

                            if local_uk.exists():
                                st.audio(str(local_uk), format="audio/mp3")
                                st.caption(f"UK (Local File): {local_uk.name}")
                            elif uk_audio:
                                st.audio(uk_audio, format="audio/mp3")
                                st.caption(f"UK 발음: {uk_audio}")
                                
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
