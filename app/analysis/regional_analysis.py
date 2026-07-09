import pandas as pd
import matplotlib.pyplot as plt
import plotly.express as px
import json

# -----------------------------
# 한글 폰트 설정
# -----------------------------
plt.rc("font", family="Malgun Gothic")
plt.rcParams["axes.unicode_minus"] = False

# -----------------------------
# 데이터 로드
# -----------------------------
df = pd.read_csv("../../data/welfare_20241231.csv", encoding="cp949")

# 2024년 데이터 필터
df2024 = df[df["기준년월"].str.endswith("-24")].copy()

# ==========================================================
# 1. 복지사업별 수급 현황 분석 (총합)
# ==========================================================

business_total = (
    df2024
    .groupby("사업명")[["수급권자수", "수급가구수"]]
    .sum()
    .reset_index()
)

# 가구당 수급권자 비율
business_total["가구당수급권자비율"] = (
    business_total["수급권자수"] / business_total["수급가구수"]
).round(2)

print("\n복지사업별 수급 현황 (총합)")
print(business_total)

# -----------------------------
# 1-1 수급권자 그래프
# -----------------------------
plt.figure(figsize=(13,6))
plt.bar(business_total["사업명"], business_total["수급권자수"])
plt.xticks(rotation=45, ha="right")
plt.title("2024년 복지사업별 수급권자 수 (수급 현황)")
plt.xlabel("복지사업")
plt.ylabel("수급권자 수")
plt.tight_layout()
plt.show()

# -----------------------------
# 1-2 수급가구 그래프
# -----------------------------
plt.figure(figsize=(13,6))
plt.bar(business_total["사업명"], business_total["수급가구수"])
plt.xticks(rotation=45, ha="right")
plt.title("2024년 복지사업별 수급가구 수 (수급 현황)")
plt.xlabel("복지사업")
plt.ylabel("수급가구 수")
plt.tight_layout()
plt.show()

# -----------------------------
# 1-3 가구 구조 비율
# -----------------------------
plt.figure(figsize=(13,6))
plt.bar(business_total["사업명"], business_total["가구당수급권자비율"])
plt.xticks(rotation=45, ha="right")
plt.title("복지사업별 가구당 수급권자 비율")
plt.xlabel("복지사업")
plt.ylabel("비율")
plt.tight_layout()
plt.show()


# ==========================================================
# 2. 지역별 수급 현황 분석
# ==========================================================

region_total = (
    df2024
    .groupby("시도")[["수급권자수", "수급가구수"]]
    .sum()
    .reset_index()
)

# 지역명 정리 (GeoJSON 매칭)
region_total["시도"] = region_total["시도"].replace({
    "강원특별자치도": "강원도",
    "전북특별자치도": "전라북도"
})

# -----------------------------
# 2-1 지역별 수급권자
# -----------------------------
plt.figure(figsize=(12,6))
plt.bar(region_total["시도"], region_total["수급권자수"])
plt.xticks(rotation=45)
plt.title("지역별 수급권자 수 (복지 수급 현황)")
plt.xlabel("시도")
plt.ylabel("수급권자 수")
plt.tight_layout()
plt.show()


# ==========================================================
# 3. Choropleth 지도 시각화
# ==========================================================

with open("../../data/skorea-geo.json", "r", encoding="utf-8") as f:
    geo = json.load(f)

fig = px.choropleth(
    region_total,
    geojson=geo,
    locations="시도",
    featureidkey="properties.name",
    color="수급권자수",
    color_continuous_scale="YlOrRd",
    projection="mercator",
    title="지역별 복지 수급권자 현황",
    hover_name="시도",
    hover_data={
        "수급권자수": ":,.0f",
        "수급가구수": ":,.0f"
    }
)

fig.update_geos(fitbounds="locations", visible=False)

fig.update_layout(
    width=900,
    height=700,
    margin=dict(l=0, r=0, t=50, b=0)
)

fig.show()