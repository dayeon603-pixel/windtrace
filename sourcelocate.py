"""바람따라 — 악취 발생원 역확산 추정 (격자 베이지안).

여러 시민 제보(도달 지점·강도)와 실시간 풍향을 입력받아,
'냄새가 어디서 출발했는가'를 격자 사후확률로 역추정한다.

원리: 악취는 발생원에서 바람을 타고 풍하(downwind)로 퍼진다.
      → 후보 발생원 c에서 각 제보 지점 r로의 방향이 '풍하 방향'과 일치하고
        crosswind 편차가 작을수록 c가 진짜 발생원일 가능성이 높다(가우시안 플룸 역문제).
"""
from __future__ import annotations
import math
import numpy as np

EARTH = 111_000.0  # m per degree (approx)


def _bearing_and_dist(clat, clng, rlat, rlng):
    """후보 c → 제보 r 의 방위(0=N,90=E, deg)와 거리(m)."""
    coslat = math.cos(math.radians((clat + rlat) / 2))
    north = (rlat - clat) * EARTH
    east = (rlng - clng) * EARTH * coslat
    dist = math.hypot(north, east)
    bearing = math.degrees(math.atan2(east, north)) % 360.0
    return bearing, dist


def _ang_diff(a, b):
    d = abs((a - b + 180) % 360 - 180)
    return d


def estimate_source(reports, wind_from_deg, wind_speed=None,
                    grid=34, span_deg=0.055, sigma0=120.0, spread=0.35):
    """발생원 추정.

    reports: [{'lat','lng','intensity'(1~3)}...]
    wind_from_deg: 바람이 불어오는 방향(기상학적, deg). 풍하 = (wind_from+180)%360.
    return: dict(source{lat,lng}, confidence(0~1), downwind_deg, n, grid_geojson, message)
    """
    pts = [(float(r["lat"]), float(r["lng"]), float(r.get("intensity", 2)))
           for r in reports]
    n = len(pts)
    if n == 0:
        return {"source": None, "confidence": 0.0, "n": 0,
                "message": "제보가 없습니다."}

    downwind = (float(wind_from_deg) + 180.0) % 360.0

    # 제보들의 무게중심 기준으로 격자 범위 설정(풍상쪽으로 충분히 포함)
    clat = sum(p[0] for p in pts) / n
    clng = sum(p[1] for p in pts) / n
    lats = np.linspace(clat - span_deg, clat + span_deg, grid)
    lngs = np.linspace(clng - span_deg, clng + span_deg, grid)

    logpost = np.full((grid, grid), 0.0)
    for i, glat in enumerate(lats):
        for j, glng in enumerate(lngs):
            ll = 0.0
            for (rlat, rlng, inten) in pts:
                bearing, dist = _bearing_and_dist(glat, glng, rlat, rlng)
                if dist < 1.0:
                    continue
                diff = _ang_diff(bearing, downwind)          # 0이면 정확히 풍하
                along = dist * math.cos(math.radians(diff))   # 풍하 성분
                cross = dist * math.sin(math.radians(diff))   # 측풍 성분
                if along <= 0:        # 제보가 후보의 '풍상' → 발생원일 수 없음
                    ll += -6.0 * (inten / 2.0)
                    continue
                sigma = sigma0 + spread * along               # 플룸은 멀수록 퍼짐
                like = math.exp(-(cross * cross) / (2 * sigma * sigma))
                # 너무 먼 거리는 약하게 감쇠(가까운 발생원 선호)
                like *= math.exp(-along / 6000.0)
                ll += (inten / 2.0) * math.log(like + 1e-9)
            logpost[i, j] = ll

    logpost -= logpost.max()
    post = np.exp(logpost)
    post /= post.sum()

    idx = np.unravel_index(np.argmax(post), post.shape)
    src_lat = float(lats[idx[0]])
    src_lng = float(lngs[idx[1]])

    # 확신도: 최댓값 주변 3x3 질량 + 제보수 보정
    i0, j0 = idx
    region = post[max(0, i0 - 1):i0 + 2, max(0, j0 - 1):j0 + 2].sum()
    nfac = min(1.0, n / 5.0)                # 제보 5개 이상에서 포화
    confidence = float(min(0.97, region * (0.55 + 0.45 * nfac) * 3.0))

    msg = "발생원 추정 완료"
    if n < 3:
        msg = f"제보 {n}건 — 3건 이상부터 정확도가 크게 오릅니다(현재 잠정)."

    # 격자 히트맵(상위 셀만, 시각화용)
    cells = []
    thr = np.quantile(post, 0.92)
    for i in range(grid):
        for j in range(grid):
            if post[i, j] >= thr:
                cells.append({"lat": float(lats[i]), "lng": float(lngs[j]),
                              "w": float(post[i, j] / post.max())})

    return {
        "source": {"lat": round(src_lat, 6), "lng": round(src_lng, 6)},
        "confidence": round(confidence, 3),
        "downwind_deg": round(downwind, 1),
        "wind_from_deg": round(float(wind_from_deg), 1),
        "wind_speed": wind_speed,
        "n": n,
        "heat": cells,
        "message": msg,
    }


def _synth_reports(slat, slng, wind_from_deg, k=6, dmin=200, dmax=2500,
                   ang_noise=18, rng=None):
    """발생원(slat,slng)에서 풍하로 합성 제보 k개 생성(검증용 ground-truth)."""
    import random
    r = rng or random.Random()
    downwind = math.radians((wind_from_deg + 180) % 360)
    reps = []
    for _ in range(k):
        d = r.uniform(dmin, dmax)
        a = downwind + math.radians(r.gauss(0, ang_noise))  # 풍하 ± 각도 노이즈
        coslat = math.cos(math.radians(slat))
        rlat = slat + (d * math.cos(a)) / EARTH
        rlng = slng + (d * math.sin(a)) / (EARTH * coslat)
        reps.append({"lat": rlat, "lng": rlng, "intensity": r.choice([2, 3])})
    return reps


def validate(n_trials=50, k=6, seed=7):
    """합성 ground-truth 검증: 임의 발생원→합성 제보→역추정→오차(m) 측정.
    return: dict(mean_err_m, median_err_m, p90_err_m, n, k)
    """
    import random
    rng = random.Random(seed)
    errs = []
    for _ in range(n_trials):
        slat = 37.50 + rng.uniform(-0.03, 0.03)
        slng = 126.67 + rng.uniform(-0.03, 0.03)
        wind = rng.uniform(0, 360)
        reps = _synth_reports(slat, slng, wind, k=k, rng=rng)
        out = estimate_source(reps, wind)
        if not out.get("source"):
            continue
        e_lat, e_lng = out["source"]["lat"], out["source"]["lng"]
        coslat = math.cos(math.radians(slat))
        err = math.hypot((e_lat - slat) * EARTH, (e_lng - slng) * EARTH * coslat)
        errs.append(err)
    errs.sort()
    m = len(errs)
    return {"mean_err_m": round(sum(errs) / m), "median_err_m": round(errs[m // 2]),
            "p90_err_m": round(errs[int(m * 0.9)]), "n": m, "k": k}


if __name__ == "__main__":
    # 자가 테스트: 남서풍(217°)이면 발생원은 제보들의 '남서쪽'에 찍혀야 함
    demo = [
        {"lat": 37.512, "lng": 126.680, "intensity": 3},
        {"lat": 37.514, "lng": 126.684, "intensity": 2},
        {"lat": 37.510, "lng": 126.686, "intensity": 3},
        {"lat": 37.516, "lng": 126.681, "intensity": 2},
        {"lat": 37.513, "lng": 126.688, "intensity": 3},
    ]
    out = estimate_source(demo, wind_from_deg=217, wind_speed=7.2)
    print("추정 발생원:", out["source"], "| 확신도:", out["confidence"],
          "| 풍하:", out["downwind_deg"], "| n:", out["n"])
    print(out["message"])
