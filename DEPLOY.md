# 바람따라 — A) 로컬 데모·녹화 + B) 배포 (둘 다)

> 지금 **로컬 서버가 돌고 있음** → 브라우저 **http://localhost:8765**
> (다시 켤 때: `cd app && PORT=8765 python3 server.py`)

---

## 🅰 로컬 데모 + 3분 녹화 (가장 안전한 제출물)

**녹화:** macOS `Cmd+Shift+5` → "선택 부분 녹화" 또는 전체화면 → 브라우저 창 녹화.

**시연 순서 (3분):**
1. **(문제·15초)** 말로: "인천 서구 악취 민원 전국 1위, 발생원 '원인불명' 17.4%. 측정차량이 가면 냄새는 이미 사라집니다."
2. **(시민 제보·60초)** [🙋 시민 제보] 탭 → 지도에서 냄새 난 곳 **5~6군데 탭** → 종류(탄내)·강도(심함) 선택 → **[📍 제보하기]**. 색 핀이 쌓이는 것 보여주기.
3. **(실시간 바람·20초)** 우상단 **풍향 화살표** 가리키며 "지금 인천 서구 실시간 바람(Open-Meteo)을 받고 있습니다."
4. **(발생원 추정·60초)** [🏛️ 관제] 탭 → **[🎯 발생원 추정]** → 🏭 발생원 핀 + **확신도 %** + **가장 가까운 시설명**(예: 가좌하수처리장) 등장. "풍향을 역산해 발생원을 지목했습니다."
5. **(마무리·15초)** "고정 측정망이 놓치는 순간 악취를, 수백 명의 코 + 바람으로 발생원까지 역추적합니다."

**팁:** 녹화 전 [🗑️ 데모 초기화]로 깨끗이 시작. 전문 편집(자막·BGM)은 심사 미반영이니 화면+음성만.
**제출 파일:** `제품서비스개발_센시티_바람따라.mp4` (4GB·자유형식).

---

## 🅱 배포 — 실제 구동 URL (선택, 영상과 병행 제출 가능)

### B-1) ngrok — 가장 빠름(5분), 즉시 공개 URL
로컬 서버를 그대로 외부에 노출. *심사 동안 노트북이 켜져 있어야 함.*
```bash
brew install ngrok            # 또는 ngrok.com에서 다운
ngrok config add-authtoken <토큰>   # ngrok.com 무료가입 후 토큰
ngrok http 8765
```
→ `https://xxxx.ngrok-free.app` 공개 URL 생성. 이걸 증빙으로 제출.

### B-2) Render — 진짜 상시 가동 URL(15분, 권장)
배포 파일 다 준비됨(`render.yaml`·`Procfile`·`requirements.txt`·`runtime.txt`).
1. `app/` 폴더를 **GitHub 저장소**로 push (app 폴더가 repo 루트가 되게).
   ```bash
   cd app && git init && git add -A && git commit -m "windtrace"
   # GitHub에 새 repo 만들고 push
   ```
2. **render.com** 무료가입 → New → **Web Service** → GitHub repo 연결.
3. Render가 `render.yaml`/`Procfile` 자동 인식 → **Create**. (Build: `pip install -r requirements.txt`, Start: `python server.py`, PORT 자동 주입)
4. 몇 분 뒤 `https://windtrace.onrender.com` 류의 **상시 URL** 발급.
- ⚠️ 무료 플랜은 15분 미사용 시 잠들어 **첫 접속 30~60초 지연**(cold start). 심사 직전 한 번 깨워두면 됨.
- ⚠️ 무료 디스크는 휘발성 → 재시작 시 제보 초기화(데모엔 오히려 깔끔).

> **추천 조합:** 제출은 **🅰 시연 영상(필수·안전)** + **🅱-2 Render URL(보너스 증빙)**. 둘 다 내면 "작동한다"가 확실해집니다.

---

## ⚙️ 가점(인천 공공데이터) — 이미 구현됨, 키만 넣으면 작동
- **기상청 AWS 연동 구현 완료**(`fetch_wind_kma()` + 격자변환). 키 없으면 Open-Meteo 자동 폴백.
- data.go.kr에서 **「기상청 단기예보 조회서비스」** 키 발급(즉시) 후:
  ```bash
  KMA_SERVICE_KEY="발급키" PORT=8765 python3 server.py
  ```
  → 풍향 출처가 **"기상청 AWS(공공데이터)"**로 전환 → **가점 1점 + 공공데이터 점수** 확보.
- (선택) `FACILITIES`를 **인천 악취배출사업장 공개 DB** 좌표로 교체.
