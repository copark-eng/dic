import json, hashlib
from pathlib import Path
from datetime import datetime, timezone

base = Path(r'c:\antigravity\mydic')
cw_path = base / 'server' / 'data' / 'custom_wordbook.json'
json_bytes = cw_path.read_bytes()
cw_sha256 = hashlib.sha256(json_bytes).hexdigest()
cw_size = len(json_bytes)
now_iso = datetime.now(timezone.utc).isoformat()

for mpath in [base / 'server' / 'data' / 'manifest.json', base / 'docs' / 'data' / 'manifest.json', base / 'app' / 'assets' / 'data' / 'manifest.json']:
    if mpath.exists():
        with open(mpath, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
        manifest['levels']['0'] = {
            'name': '디폴트 나만의 단어장',
            'code': 'MY',
            'total_words': 1222,
            'count': 1222,
            'file': 'custom_wordbook.json',
            'file_size_bytes': cw_size,
            'sha256': cw_sha256,
            'updated_at': now_iso
        }
        with open(mpath, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
        print('Updated:', mpath)
