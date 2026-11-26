# Shoopa - Arrow Tap Puzzle · 쏙쏙 빼기

shoopa.ipe.rest의 12개 언어 정적 사이트입니다. 언어별 문구는 `content/`, 생성된 GitHub Pages 파일은 `public/`에 있습니다.

```sh
python3 scripts/kit_lock.py sync --kit /path/to/ipe_web_kit
python3 scripts/build_site.py
scripts/check.sh
python3 -m http.server --bind 127.0.0.1 --directory public 8000
```

저널 초안은 `content/journal/`에 둡니다. `ipe_web_kit.journal`이 12개 판의 Iris 검수자와 날짜를 확인한 뒤 글·이미지·사이트맵 항목을 생성합니다. GitHub Pages 워크플로는 수동 실행으로 설정되어 있습니다.
