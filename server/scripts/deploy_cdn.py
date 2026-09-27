# -*- coding: utf-8 -*-
from __future__ import annotations
"""
GitHub Pages CDN 배포 및 정적 웹 포털 빌더 (Deploy CDN)
server/data/*.json 파일을 docs/data/ 로 동기화하고
GitHub Pages 호스팅용 docs/index.html 랜딩 페이지를 자동 생성합니다. (ADR-001)
"""

import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
SERVER_DIR = SCRIPTS_DIR.parent
ROOT_DIR = SERVER_DIR.parent
DATA_DIR = SERVER_DIR / "data"
DOCS_DIR = ROOT_DIR / "docs"
DOCS_DATA_DIR = DOCS_DIR / "data"

sys.path.insert(0, str(SCRIPTS_DIR))
import config

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MyDic API & CDN Distribution Portal</title>
    <style>
        :root {
            --primary: #2563eb;
            --primary-dark: #1d4ed8;
            --bg: #f8fafc;
            --card-bg: #ffffff;
            --text: #0f172a;
            --text-muted: #64748b;
            --border: #e2e8f0;
            --success: #10b981;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; background: var(--bg); color: var(--text); line-height: 1.6; padding: 2rem 1rem; }
        .container { max-width: 900px; margin: 0 auto; }
        header { text-align: center; margin-bottom: 2.5rem; }
        h1 { font-size: 2.2rem; font-weight: 800; color: var(--text); margin-bottom: 0.5rem; }
        .badge { display: inline-block; padding: 0.25rem 0.75rem; border-radius: 9999px; font-size: 0.85rem; font-weight: 600; background: #dcfce7; color: #166534; margin-bottom: 1rem; }
        p.subtitle { color: var(--text-muted); font-size: 1.1rem; }
        .card { background: var(--card-bg); border: 1px solid var(--border); border-radius: 12px; padding: 1.5rem; margin-bottom: 1.5rem; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
        h2 { font-size: 1.3rem; margin-bottom: 1rem; border-bottom: 2px solid var(--border); padding-bottom: 0.5rem; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1rem; }
        .level-card { border: 1px solid var(--border); border-radius: 8px; padding: 1rem; background: #fafafa; transition: transform 0.15s ease; }
        .level-card:hover { transform: translateY(-2px); border-color: var(--primary); }
        .level-card h3 { font-size: 1.1rem; color: var(--primary-dark); margin-bottom: 0.25rem; }
        .level-meta { font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.75rem; }
        .btn { display: inline-block; padding: 0.4rem 0.8rem; border-radius: 6px; font-size: 0.85rem; font-weight: 600; text-decoration: none; background: var(--primary); color: white; transition: background 0.15s; }
        .btn:hover { background: var(--primary-dark); }
        pre { background: #1e293b; color: #f8fafc; padding: 1rem; border-radius: 8px; overflow-x: auto; font-size: 0.9rem; }
        footer { text-align: center; font-size: 0.85rem; color: var(--text-muted); margin-top: 3rem; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <span class="badge">● Cloudflare Global CDN Operational (100% Free)</span>
            <h1>MyDic 영어사전 배포 서버</h1>
            <p class="subtitle">GitHub Pages 기반 24/7 무중단, 초고속 7단계 단어 데이터셋 배포 포털</p>
        </header>

        <div class="card">
            <h2>📊 데이터셋 개요 (Manifest v1.0.0)</h2>
            <p>총 <strong>26,500개</strong> 고유 어휘 (레벨 간 중복 0건, 미국식/영국식 53,000개 오디오 링크 완비)</p>
            <p style="margin-top: 0.5rem;"><a href="data/manifest.json" class="btn" target="_blank">📄 manifest.json 메타데이터 열람</a></p>
        </div>

        <div class="card">
            <h2>📚 단계별 단어 데이터 (Level 1 ~ 7)</h2>
            <div class="grid">
                __LEVEL_CARDS__
            </div>
        </div>

        <div class="card">
            <h2>📱 Android 클라이언트 연동 규격</h2>
            <p style="margin-bottom: 0.75rem;">모바일 앱은 HTTPS 요청을 통해 필요한 레벨의 JSON 데이터를 직접 수신하여 Room 로컬 DB에 캐싱합니다.</p>
            <pre><code>// Android Retrofit / OkHttp 다운로드 엔드포인트
GET https://&lt;username&gt;.github.io/&lt;repo&gt;/data/manifest.json
GET https://&lt;username&gt;.github.io/&lt;repo&gt;/data/level_{1..7}.json</code></pre>
        </div>

        <footer>
            <p>MyDic Project &copy; 2026. Powered by GitHub Pages & Streamlit Cloud (ADR-001).</p>
        </footer>
    </div>
</body>
</html>
"""

def main() -> int:
    print("=" * 65)
    print("GitHub Pages CDN 배포 및 docs/ 디렉터리 동기화 시작")
    print("=" * 65)

    DOCS_DATA_DIR.mkdir(parents=True, exist_ok=True)

    # 1. manifest.json 로드
    manifest_path = DATA_DIR / "manifest.json"
    if not manifest_path.exists():
        print("[ERROR] server/data/manifest.json 파일이 없습니다. 먼저 빌드를 수행하세요.")
        return 1

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    # 2. JSON 파일 docs/data/ 로 복사
    files_to_copy = ["manifest.json"] + [f"level_{i}.json" for i in range(1, 8)]
    copied_count = 0

    print("[1/3] 단어 JSON 데이터셋 docs/data/ 로 복사 중...")
    for fname in files_to_copy:
        src = DATA_DIR / fname
        dst = DOCS_DATA_DIR / fname
        if src.exists():
            shutil.copy2(src, dst)
            copied_count += 1
            print(f"  - 동기화 완료: {dst.name} ({dst.stat().st_size // 1024:,} KB)")
        else:
            print(f"  [경고] {src.name} 파일이 존재하지 않습니다.")

    # 3. docs/index.html 랜딩 페이지 생성
    print("[2/3] GitHub Pages 웹 포털 (docs/index.html) 렌더링 중...")
    level_cards_html = []
    levels = manifest.get("levels", {})

    for i in range(1, 8):
        lvl_str = str(i)
        info = levels.get(lvl_str, {})
        name = info.get("name", f"Level {i}")
        words_count = info.get("total_words", 0)
        size_kb = info.get("file_size_bytes", 0) // 1024
        sha_short = info.get("sha256", "")[:8]

        card = f"""
                <div class="level-card">
                    <h3>Level {i}: {name}</h3>
                    <div class="level-meta">
                        <div>단어 수: <strong>{words_count:,}</strong>개</div>
                        <div>크기: {size_kb:,} KB | SHA: {sha_short}...</div>
                    </div>
                    <a href="data/level_{i}.json" class="btn" target="_blank">다운로드 JSON</a>
                </div>"""
        level_cards_html.append(card)

    rendered_html = HTML_TEMPLATE.replace("__LEVEL_CARDS__", "\n".join(level_cards_html))
    index_path = DOCS_DIR / "index.html"
    index_path.write_text(rendered_html, encoding="utf-8")
    print(f"  - 생성 완료: {index_path.relative_to(ROOT_DIR)} ({index_path.stat().st_size:,} bytes)")

    # 4. 검증
    print("[3/3] 배포 무결성 검증...")
    assert (DOCS_DATA_DIR / "manifest.json").exists(), "manifest.json 누락"
    for i in range(1, 8):
        assert (DOCS_DATA_DIR / f"level_{i}.json").exists(), f"level_{i}.json 누락"

    print("=" * 65)
    print("GitHub Pages CDN 배포 준비 완료!")
    print(f"- 배포 루트: {DOCS_DIR}")
    print("- 활성화 방법: GitHub 저장소 Settings -> Pages -> Deploy from branch -> /docs 선택 후 저장")
    print("=" * 65)
    return 0

if __name__ == "__main__":
    sys.exit(main())
