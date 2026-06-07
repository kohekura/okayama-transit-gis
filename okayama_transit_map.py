import pandas as pd
import folium
import geopandas as gpd
import os
from shapely.geometry import Point, Polygon

# ============================================================
# パス設定
# ============================================================
BASE_DIR   = r"C:\Users\rd006\Downloads\0kayama_GTFS"
RYOBI_DIR  = os.path.join(BASE_DIR, "ryobi")
OKADEN_DIR = os.path.join(BASE_DIR, "okaden")
TRAM_DIR   = os.path.join(BASE_DIR, "gtfs")
MESH_FILE  = os.path.join(BASE_DIR, "tblT001101H33", "tblT001101H33.txt")

# ============================================================
# 500mメッシュ座標変換
# ============================================================
def mesh4_to_polygon(code):
    code = str(code).zfill(9)
    p = int(code[0:2]); u = int(code[2:4])
    q = int(code[4]);   v = int(code[5])
    r = int(code[6]);   w = int(code[7])
    m = int(code[8])
    lat_sw3 = p / 1.5 + q / 12.0 + r / 120.0
    lon_sw3 = (u + 100) + v / 8.0 + w / 80.0
    dlat = 1 / 240.0
    dlon = 1 / 160.0
    row = (m - 1) // 2
    col = (m - 1) % 2
    lat_sw = lat_sw3 + row * dlat
    lon_sw = lon_sw3 + col * dlon
    return Polygon([
        (lon_sw,        lat_sw),
        (lon_sw + dlon, lat_sw),
        (lon_sw + dlon, lat_sw + dlat),
        (lon_sw,        lat_sw + dlat),
    ])

# ============================================================
# 人口メッシュ読み込み
# ============================================================
print("人口メッシュ読み込み中...")
mesh_df = pd.read_csv(MESH_FILE, encoding="shift-jis", low_memory=False)
mesh_df = mesh_df.dropna(subset=["KEY_CODE"])
mesh_df["key_code"]   = mesh_df["KEY_CODE"].astype(float).astype(int).astype(str)
mesh_df["population"] = pd.to_numeric(mesh_df["T001101001"], errors="coerce").fillna(0)
mesh_df = mesh_df[mesh_df["population"] > 0].copy()
mesh_df["geometry"] = mesh_df["key_code"].apply(mesh4_to_polygon)
gdf_mesh = gpd.GeoDataFrame(mesh_df, geometry="geometry", crs="EPSG:4326")
gdf_mesh = gdf_mesh.cx[133.7:134.2, 34.5:35.0]
print(f"岡山市域: {len(gdf_mesh)}メッシュ / 総人口: {int(gdf_mesh['population'].sum()):,}人")

# 色設定：白→オレンジ→赤（薄め）
max_pop = gdf_mesh["population"].quantile(0.95)
def pop_color(pop):
    ratio = min(pop / max_pop, 1.0)
    if ratio < 0.5:
        t = ratio * 2
        r = 255
        g = int(200 - t * 130)
        b = int(180 - t * 180)
    else:
        t = (ratio - 0.5) * 2
        r = 255
        g = int(70 - t * 70)
        b = 0
    return f"#{r:02x}{g:02x}{b:02x}"

# ============================================================
# 停留所・路線読み込み
# ============================================================
def load_stops(folder, label, color):
    df = pd.read_csv(os.path.join(folder, "stops.txt"))
    df["label"] = label
    df["color"] = color
    return df[["stop_name", "stop_lat", "stop_lon", "label", "color"]]

ryobi  = load_stops(RYOBI_DIR,  "両備バス", "#0077cc")
okaden = load_stops(OKADEN_DIR, "岡電バス", "#e65c00")
tram   = load_stops(TRAM_DIR,   "路面電車", "#cc0022")

def load_shapes(folder):
    df = pd.read_csv(os.path.join(folder, "shapes.txt"))
    return (
        df.sort_values(["shape_id", "shape_pt_sequence"])
        .groupby("shape_id")
        .apply(lambda g: list(zip(g["shape_pt_lat"], g["shape_pt_lon"])))
        .to_dict()
    )

print("路線データ読み込み中...")
ryobi_shapes  = load_shapes(RYOBI_DIR)
okaden_shapes = load_shapes(OKADEN_DIR)
tram_shapes   = load_shapes(TRAM_DIR)

# ============================================================
# 300mバッファ生成
# ============================================================
print("バッファ生成中...")
def make_buffer_gdf(stops_df):
    gdf = gpd.GeoDataFrame(
        stops_df,
        geometry=[Point(lon, lat) for lat, lon in
                  zip(stops_df["stop_lat"], stops_df["stop_lon"])],
        crs="EPSG:4326"
    )
    gdf_proj = gdf.to_crs("EPSG:6673")
    gdf_proj["buffer"] = gdf_proj.geometry.buffer(300)
    return gdf_proj.set_geometry("buffer").to_crs("EPSG:4326")

buf_ryobi  = make_buffer_gdf(ryobi)
buf_okaden = make_buffer_gdf(okaden)
buf_tram   = make_buffer_gdf(tram)

# ============================================================
# 地図作成
# ============================================================
m = folium.Map(
    location=[34.6618, 133.9344],
    zoom_start=13,
    tiles="OpenStreetMap"
)

# --- レイヤー定義 ---
lg_mesh        = folium.FeatureGroup(name="人口分布（500mメッシュ）",  show=True)
lg_buf_tram    = folium.FeatureGroup(name="路面電車 徒歩300m圏",       show=True)
lg_buf_ryobi   = folium.FeatureGroup(name="両備バス 徒歩300m圏",       show=False)
lg_buf_okaden  = folium.FeatureGroup(name="岡電バス 徒歩300m圏",       show=False)
lg_line_tram   = folium.FeatureGroup(name="路面電車 路線",             show=True)
lg_line_ryobi  = folium.FeatureGroup(name="両備バス 路線",             show=True)
lg_line_okaden = folium.FeatureGroup(name="岡電バス 路線",             show=True)
lg_stop_tram   = folium.FeatureGroup(name="路面電車 停留所",           show=True)
lg_stop_ryobi  = folium.FeatureGroup(name="両備バス 停留所",           show=True)
lg_stop_okaden = folium.FeatureGroup(name="岡電バス 停留所",           show=True)

# --- 人口メッシュ（薄め：fillOpacity=0.4）---
print("人口メッシュ描画中...")
for _, row in gdf_mesh.iterrows():
    color = pop_color(row["population"])
    folium.GeoJson(
        row["geometry"].__geo_interface__,
        style_function=lambda x, c=color: {
            "fillColor": c, "color": "none",
            "fillOpacity": 0.4, "weight": 0
        },
        tooltip=f"人口: {int(row['population'])}人"
    ).add_to(lg_mesh)

# --- バッファ ---
for _, row in buf_tram.iterrows():
    folium.GeoJson(row["buffer"].__geo_interface__,
        style_function=lambda x: {
            "fillColor": "#cc0022", "color": "#cc0022",
            "weight": 0.5, "fillOpacity": 0.1}
    ).add_to(lg_buf_tram)

for _, row in buf_ryobi.iterrows():
    folium.GeoJson(row["buffer"].__geo_interface__,
        style_function=lambda x: {
            "fillColor": "#0077cc", "color": "#0077cc",
            "weight": 0.3, "fillOpacity": 0.07}
    ).add_to(lg_buf_ryobi)

for _, row in buf_okaden.iterrows():
    folium.GeoJson(row["buffer"].__geo_interface__,
        style_function=lambda x: {
            "fillColor": "#e65c00", "color": "#e65c00",
            "weight": 0.3, "fillOpacity": 0.07}
    ).add_to(lg_buf_okaden)

# --- 路線ライン ---
for coords in tram_shapes.values():
    folium.PolyLine(coords, color="#cc0022", weight=5, opacity=1.0).add_to(lg_line_tram)
for coords in ryobi_shapes.values():
    folium.PolyLine(coords, color="#0077cc", weight=2, opacity=0.8).add_to(lg_line_ryobi)
for coords in okaden_shapes.values():
    folium.PolyLine(coords, color="#e65c00", weight=2, opacity=0.8).add_to(lg_line_okaden)

# --- 停留所 ---
for _, row in tram.iterrows():
    folium.CircleMarker(
        location=[row["stop_lat"], row["stop_lon"]],
        radius=5, color="#cc0022", fill=True, fill_color="#cc0022",
        fill_opacity=1.0, popup=f"路面電車: {row['stop_name']}"
    ).add_to(lg_stop_tram)

for _, row in ryobi.iterrows():
    folium.CircleMarker(
        location=[row["stop_lat"], row["stop_lon"]],
        radius=3, color="#0077cc", fill=True, fill_color="#0077cc",
        fill_opacity=0.9, popup=f"両備バス: {row['stop_name']}"
    ).add_to(lg_stop_ryobi)

for _, row in okaden.iterrows():
    folium.CircleMarker(
        location=[row["stop_lat"], row["stop_lon"]],
        radius=3, color="#e65c00", fill=True, fill_color="#e65c00",
        fill_opacity=0.9, popup=f"岡電バス: {row['stop_name']}"
    ).add_to(lg_stop_okaden)

# --- レイヤーを地図に追加 ---
for lg in [lg_mesh,
           lg_buf_tram, lg_buf_ryobi, lg_buf_okaden,
           lg_line_tram, lg_line_ryobi, lg_line_okaden,
           lg_stop_tram, lg_stop_ryobi, lg_stop_okaden]:
    lg.add_to(m)

folium.LayerControl(collapsed=False).add_to(m)

# --- 凡例 ---
legend_html = """
<div style="
    position: fixed; bottom: 30px; left: 30px;
    background: white; padding: 12px 16px;
    border-radius: 8px; border: 1px solid #ccc;
    font-size: 13px; z-index: 1000; color: #222;
    box-shadow: 2px 2px 8px rgba(0,0,0,0.15);
">
    <b>岡山市 公共交通×人口分布</b><br>
    <small style="color:#888;">令和2年国勢調査 500mメッシュ</small><br><br>
    <span style="background:linear-gradient(to right,#ffd0b0,#ff8800,#ff0000);
        display:inline-block;width:80px;height:10px;vertical-align:middle;border:1px solid #ccc;">
    </span> 人口密度（低→高）<br><br>
    <span style="color:#cc0022;">━━ ●</span> 路面電車（岡電）<br>
    <span style="color:#0077cc;">━━ ●</span> 両備バス<br>
    <span style="color:#e65c00;">━━ ●</span> 岡電バス
</div>
"""
m.get_root().html.add_child(folium.Element(legend_html))

# ============================================================
# 保存
# ============================================================
OUTPUT_PATH = os.path.join(BASE_DIR, "okayama_transit_map.html")
m.save(OUTPUT_PATH)
print(f"\n地図を保存しました: {OUTPUT_PATH}")
