# Shoopa - Arrow Tap Puzzle · 쏙쏙 빼기

shoopa.ipe.rest의 12개 언어 정적 사이트입니다. 언어별 문구는 `content/`, 생성된 GitHub Pages 파일은 `public/`에 있습니다.

```sh
python3 scripts/kit_lock.py sync --kit /path/to/ipe_web_kit
python3 scripts/build_site.py
scripts/check.sh
python3 -m http.server --bind 127.0.0.1 --directory public 8000
```

저널 글은 `content/journal/`에 글당 JSON 파일 하나로 둡니다. 서로 다른 한국시간 발행일을 `date`에 `YYYY-MM-DD`로 지정합니다. 발행일이 되었고 12개 언어판 각각에 Iris 검수자와 검수 날짜가 기록되어 있으면 글·목록·사이트맵에 함께 나타납니다. 이미지가 있는 글에는 각 언어판의 대체 텍스트도 적습니다.

생성과 검사는 기본으로 현재 한국시간 날짜를 사용합니다. 특정 날짜를 재현할 때는 두 명령에 같은 날짜를 전달합니다.

```sh
python3 scripts/build_site.py --date 2026-11-26
scripts/check.sh --date 2026-11-26
```

## GitHub Pages 배포

1. 위 명령으로 사이트를 생성하고 로컬 `scripts/check.sh`가 통과하면 `public/` 생성물을 소스와 함께 커밋합니다.
2. 기본 브랜치에 워크플로와 생성물이 반영되면 저장소의 Settings → Pages에서 배포 소스를 GitHub Actions로 선택합니다. 맞춤 도메인 `shoopa.ipe.rest`를 저장하고 DNS가 연결되면 HTTPS 적용을 확인합니다.
3. Actions의 Pages 워크플로는 매일 한국시간 00:17에 기본 브랜치에서 실행을 예약합니다. 수동 실행도 같은 방식으로 실행 당일의 공개 대상 글을 포함해 `public/`을 다시 생성하고 검사를 통과한 산출물을 배포합니다. 글 큐의 마지막 날짜가 지나면 검수된 글과 다음 날짜를 추가해야 합니다.
