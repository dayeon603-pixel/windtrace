# 바람따라(WindTrace) MVP — 실행 & 데모 가이드

> 인천 공공데이터·AI 경진대회 **제품·서비스 개발 부문** 시연용 MVP.
> 의존성: Python3 + numpy 만. (fastapi 등 설치 불필요)

## 🌐 온라인 데모 배포 (원클릭, API 키 불필요)

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/dayeon603-pixel/windtrace)

1. 위 **Deploy to Render** 버튼 클릭 → Render 무료 회원가입(GitHub 로그인)
2. Render가 `render.yaml`을 자동 인식 → **Apply/Deploy** 클릭
3. 1~2분 뒤 `https://windtrace.onrender.com` 형태의 **공개 URL** 발급
- 키 불필요: 기상청 키 없이도 **Open-Meteo 실시간 풍향**으로 작동(가점용 기상청 키는 Render Environment에 `KMA_SERVICE_KEY` 추가 시 활성).
- 무료 플랜은 15분 미사용 시 잠자기 → 첫 접속 콜드스타트 ~30초(심사 직전 1회 깨우기 권장).
- 첫 방문 시 **샘플 제보 5건 자동 시드** → [관제] 탭 → [발생원 추정] 누르면 바로 결과.

## ▶ 실행 (한 줄)
```bash
cd app
PORT=8765 python3 server.py        # 8000이 비었으면 그냥 python3 server.py
# 브라우저 → http://localhost:8765
```
- 지도: Leaflet+OSM(무키) · 바람: Open-Meteo 실시간(무키) · 발생원 추정: 자체 역확산

## ✅ 진짜 작동하는 것 (정직)
- 실시간 풍향(Open-Meteo) · 실제 제보 입력·저장 · **진짜 역확산 격자 베이지안**(`sourcelocate.py`) · 발생원 핀+확신도+시설 지목.
- '시민 다수'는 데모상 직접 제보(시드) — "N명이 제보하면 이렇게 뜬다"를 *실제 계산*으로 시연.

## ⚙️ 제출 본판 전 교체 권장 (가점·공공데이터 30점)
- **바람: Open-Meteo → 기상청 AWS(공공데이터포털 API)** 로 교체 = 인천 공공데이터 가점(1점) + 공공데이터 점수.
  `fetch_wind()` 한 함수만 기상청 API로 바꾸면 됨(키는 data.go.kr 즉시 발급).
- 시설 좌표(FACILITIES)를 **인천 악취배출사업장 공개 DB**로 교체.

## 📂 구조
```
app/
  server.py        # 표준 라이브러리 서버 (/api/report,/wind,/estimate,/clear)
  sourcelocate.py  # 역확산 발생원 추정 (numpy)
  web/index.html   # Leaflet 지도 UI (시민 제보 / 관제)
  reports.json     # 제보 저장(자동 생성)
```

## 📝 제출 서류 (제품·서비스 부문 = 서식6)
- 아이디어 부문 제안서(서식5) 내용 → **서식6 사업계획서**로 거의 그대로 전환 + "실제 구현(MVP)" 절 추가.
- 제출: 서식1~4 + **서식6** + **시연영상(또는 URL)** → 압축 `제품서비스개발_센시티_바람따라.zip` → klee7@korea.kr · 6/12 18:00.
