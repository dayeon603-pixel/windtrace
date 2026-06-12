"""인천 공공데이터 로더 — 악취 배출사업장/측정점 좌표 (가점용 실데이터 연동).

하드코딩 대신 인천 공공데이터 CSV를 로드해 발생원 시설 매칭에 사용한다.
- data/incheon_facilities.csv 가 있으면 그것을 사용(실데이터),
- 없으면 내장 시드(인천 서구 실제 시설 5곳)로 폴백.

CSV 스키마(헤더):  name,lat,lng,type
출처 예) data.incheon.go.kr 악취 배출사업장 현황 / data.go.kr 15102640(악취 실태조사 측정점)
"""
import csv
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data")
CSV_PATH = os.path.join(DATA_DIR, "incheon_facilities.csv")

# 인천 서구 실제 악취 배출원(시드 — 전체 배출사업장 CSV로 교체 권장)
_SEED = [
    {"name": "수도권매립지", "lat": 37.5772, "lng": 126.6285, "type": "매립"},
    {"name": "청라소각장(자원순환센터)", "lat": 37.5360, "lng": 126.6510, "type": "소각"},
    {"name": "가좌하수처리장", "lat": 37.5005, "lng": 126.6730, "type": "하수"},
    {"name": "서부산업단지", "lat": 37.4880, "lng": 126.6600, "type": "산단"},
    {"name": "북항 배후 산단", "lat": 37.5180, "lng": 126.6300, "type": "산단"},
]


def load_facilities(path=CSV_PATH):
    """(facilities, source_label) 반환. CSV 우선, 없으면 시드."""
    if os.path.exists(path):
        out = []
        with open(path, encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                try:
                    out.append({
                        "name": row["name"].strip(),
                        "lat": float(row["lat"]),
                        "lng": float(row["lng"]),
                        "type": (row.get("type") or "").strip(),
                    })
                except (KeyError, ValueError):
                    continue
        if out:
            return out, f"인천 공공데이터 CSV ({os.path.basename(path)}, {len(out)}건)"
    return list(_SEED), "내장 시드 5건 (실 CSV 교체 권장)"


if __name__ == "__main__":
    fac, src = load_facilities()
    print(f"출처: {src}")
    for f in fac[:5]:
        print(" ", f["name"], f["lat"], f["lng"], f.get("type"))
