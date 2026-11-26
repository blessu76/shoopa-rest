# Shoopa - Arrow Tap Puzzle · 쏙쏙 빼기

shoopa.ipe.rest의 12개 언어 정적 사이트입니다. 언어별 문구는 `content/`, 생성된 GitHub Pages 파일은 `public/`에 있습니다.

```sh
python3 scripts/kit_lock.py sync --kit /path/to/ipe_web_kit
python3 scripts/build_site.py
scripts/check.sh
python3 -m http.server --bind 127.0.0.1 --directory public 8000
```

저널 초안은 `content/journal/`에 둡니다. `ipe_web_kit.journal`이 12개 판의 Iris 검수자와 날짜를 확인한 뒤 글·이미지·사이트맵 항목을 생성합니다.

## GitHub Pages 배포

1. 위 명령으로 사이트를 생성하고 로컬 `scripts/check.sh`가 통과하면 `public/` 생성물을 소스와 함께 커밋합니다.
2. 기본 브랜치에 워크플로와 생성물이 반영되면 저장소의 Settings → Pages에서 배포 소스를 GitHub Actions로 선택합니다. 맞춤 도메인 `shoopa.ipe.rest`를 저장하고 DNS가 연결되면 HTTPS 적용을 확인합니다.
3. Actions에서 Pages 워크플로를 기본 브랜치 대상으로 수동 실행합니다. 워크플로는 커밋된 `public/`을 배포합니다.
