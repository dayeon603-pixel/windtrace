"""바람따라(WindTrace) MVP 서버 — Python 표준 라이브러리만 사용(의존성 0, numpy만).

실행:  python3 server.py   → http://localhost:8000
- 시민 제보(위치·강도·종류) 저장
- Open-Meteo로 실시간 풍향 수신(무키)
- 역확산 알고리즘으로 발생원 실시간 지목
"""
import json, os, urllib.request, urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from sourcelocate import estimate_source

HERE = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(HERE, "web")
STORE = os.path.join(HERE, "reports.json")

# 인천 서구(수도권매립지 권역) 기본 중심
CENTER = (37.5075, 126.6743)

# 인천 공공데이터(배출사업장/측정점) 로드 — 하드코딩 대체(가점용 실데이터 연동)
from incheon_data import load_facilities
FACILITIES, FACILITIES_SOURCE = load_facilities()
print("배출사업장 데이터 출처:", FACILITIES_SOURCE)


def load_reports():
    if os.path.exists(STORE):
        try:
            return json.load(open(STORE, encoding="utf-8"))
        except Exception:
            return []
    return []


def save_reports(r):
    json.dump(r, open(STORE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


# 배포 데모용 샘플 제보(인천 서구) — 첫 방문자가 빈 지도를 보지 않도록 시작 시 시드
DEMO_SEED = [
    {"lat": 37.512, "lng": 126.682, "intensity": 3, "type": "탄내", "ts": "데모"},
    {"lat": 37.514, "lng": 126.686, "intensity": 3, "type": "탄내", "ts": "데모"},
    {"lat": 37.510, "lng": 126.684, "intensity": 2, "type": "하수", "ts": "데모"},
    {"lat": 37.515, "lng": 126.683, "intensity": 3, "type": "탄내", "ts": "데모"},
    {"lat": 37.511, "lng": 126.688, "intensity": 2, "type": "가스", "ts": "데모"},
]


def seed_if_empty():
    if not load_reports():
        save_reports(DEMO_SEED)


import math, time as _time

# 기상청 공공데이터 API 키(data.go.kr). 환경변수로 주입: KMA_SERVICE_KEY=...
KMA_KEY = os.environ.get("KMA_SERVICE_KEY", "").strip()


def _latlon_to_kma_grid(lat, lon):
    """위경도 → 기상청 격자(nx, ny) (Lambert conformal, KMA 표준)."""
    RE, GRID, SLAT1, SLAT2 = 6371.00877, 5.0, 30.0, 60.0
    OLON, OLAT, XO, YO = 126.0, 38.0, 43, 136
    D = math.pi / 180.0
    re = RE / GRID
    sn = math.tan(math.pi*0.25 + SLAT2*D*0.5) / math.tan(math.pi*0.25 + SLAT1*D*0.5)
    sn = math.log(math.cos(SLAT1*D)/math.cos(SLAT2*D)) / math.log(sn)
    sf = math.tan(math.pi*0.25 + SLAT1*D*0.5); sf = (sf**sn)*math.cos(SLAT1*D)/sn
    ro = math.tan(math.pi*0.25 + OLAT*D*0.5); ro = re*sf/(ro**sn)
    ra = math.tan(math.pi*0.25 + lat*D*0.5); ra = re*sf/(ra**sn)
    theta = lon*D - OLON*D
    if theta > math.pi: theta -= 2*math.pi
    if theta < -math.pi: theta += 2*math.pi
    theta *= sn
    return int(ra*math.sin(theta)+XO+0.5), int(ro-ra*math.cos(theta)+YO+0.5)


def fetch_wind_kma(lat, lng):
    """기상청 초단기실황(공공데이터)으로 풍향·풍속. 키 없거나 실패 시 None."""
    if not KMA_KEY:
        return None
    try:
        nx, ny = _latlon_to_kma_grid(lat, lng)
        t = _time.localtime(_time.time() - 40*60)  # 실황은 약 40분 지연 제공
        base_date = _time.strftime("%Y%m%d", t)
        base_time = _time.strftime("%H00", t)
        q = urllib.parse.urlencode({
            "serviceKey": KMA_KEY, "dataType": "JSON", "numOfRows": 60, "pageNo": 1,
            "base_date": base_date, "base_time": base_time, "nx": nx, "ny": ny})
        url = ("http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/"
               "getUltraSrtNcst?" + q)
        items = (json.load(urllib.request.urlopen(url, timeout=12))
                 ["response"]["body"]["items"]["item"])
        v = {it["category"]: it["obsrValue"] for it in items}
        return {"wind_from_deg": float(v["VEC"]), "wind_speed": float(v["WSD"]),
                "temp": float(v.get("T1H", 0)), "time": f"{base_date} {base_time}",
                "source": "기상청 AWS(공공데이터)"}
    except Exception:
        return None


def fetch_wind(lat, lng):
    """풍향 우선순위: 기상청(공공데이터·가점) → Open-Meteo(무키 폴백)."""
    kma = fetch_wind_kma(lat, lng)
    if kma:
        return kma
    try:
        q = urllib.parse.urlencode({
            "latitude": lat, "longitude": lng,
            "current": "wind_speed_10m,wind_direction_10m,temperature_2m"})
        cur = json.load(urllib.request.urlopen(
            "https://api.open-meteo.com/v1/forecast?" + q, timeout=12))["current"]
        return {"wind_from_deg": cur["wind_direction_10m"],
                "wind_speed": cur["wind_speed_10m"],
                "temp": cur.get("temperature_2m"), "time": cur.get("time"),
                "source": "Open-Meteo(폴백)"}
    except Exception as e:
        return {"error": str(e)}


def nearest_facility(lat, lng):
    import math
    best, bd = None, 1e9
    for f in FACILITIES:
        d = math.hypot((f["lat"] - lat) * 111000,
                       (f["lng"] - lng) * 111000 * math.cos(math.radians(lat)))
        if d < bd:
            bd, best = d, f
    return {**best, "dist_m": round(bd)} if best else None


class H(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json"):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False).encode("utf-8")
        elif isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):  # 조용히
        pass

    def do_GET(self):
        path = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(path.query)
        if path.path in ("/", "/index.html"):
            return self._serve_file("index.html", "text/html")
        if path.path == "/api/wind":
            lat = float(qs.get("lat", [CENTER[0]])[0])
            lng = float(qs.get("lng", [CENTER[1]])[0])
            return self._send(200, fetch_wind(lat, lng))
        if path.path == "/api/reports":
            return self._send(200, load_reports())
        if path.path == "/api/estimate":
            reports = load_reports()
            if not reports:
                return self._send(200, {"source": None, "confidence": 0,
                                        "n": 0, "message": "제보가 없습니다."})
            clat = sum(r["lat"] for r in reports) / len(reports)
            clng = sum(r["lng"] for r in reports) / len(reports)
            w = fetch_wind(clat, clng)
            if "error" in w:
                return self._send(200, {"error": "풍향 수신 실패: " + w["error"]})
            out = estimate_source(reports, w["wind_from_deg"], w["wind_speed"])
            if out.get("source"):
                out["facility"] = nearest_facility(out["source"]["lat"],
                                                    out["source"]["lng"])
                out["facility_source"] = FACILITIES_SOURCE
            out["temp"] = w.get("temp")
            out["wind_time"] = w.get("time")
            return self._send(200, out)
        # static
        return self._serve_file(path.path.lstrip("/"), self._ctype(path.path))

    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path
        n = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(n) if n else b"{}"
        try:
            data = json.loads(raw or b"{}")
        except Exception:
            data = {}
        if path == "/api/report":
            reports = load_reports()
            import time
            reports.append({
                "lat": float(data["lat"]), "lng": float(data["lng"]),
                "intensity": int(data.get("intensity", 2)),
                "type": data.get("type", "기타"),
                "ts": data.get("ts") or time.strftime("%H:%M:%S"),
            })
            save_reports(reports)
            return self._send(200, {"ok": True, "count": len(reports)})
        if path == "/api/clear":
            save_reports([])
            return self._send(200, {"ok": True})
        return self._send(404, {"error": "not found"})

    def _serve_file(self, name, ctype):
        fp = os.path.join(WEB, os.path.basename(name) if name else "index.html")
        if not os.path.exists(fp):
            return self._send(404, "not found", "text/plain")
        with open(fp, "rb") as f:
            body = f.read()
        self.send_response(200)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    @staticmethod
    def _ctype(p):
        if p.endswith(".css"): return "text/css"
        if p.endswith(".js"): return "application/javascript"
        if p.endswith(".html"): return "text/html"
        return "text/plain"


if __name__ == "__main__":
    PORT = int(os.environ.get("PORT", "8000"))
    seed_if_empty()
    print(f"바람따라 MVP → http://localhost:{PORT}  (Ctrl+C 종료)")
    print("  포트 충돌 시:  PORT=8765 python3 server.py")
    ThreadingHTTPServer(("0.0.0.0", PORT), H).serve_forever()
