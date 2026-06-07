# okayama-transit-gis

岡山市の公共交通網と人口分布を重ね合わせたインタラクティブWebGIS。

都市政策を担当する実務者が、GISエンジニアとしての素養を習得するプロジェクトの一環として作成。

---

## 概要

岡山市内を走る路面電車・バス2社のGTFSオープンデータと、国勢調査の500mメッシュ人口データを組み合わせ、以下を可視化する。

- 各停留所・電停の位置
- 路線ライン（路面電車・両備バス・岡電バス）
- 徒歩300m圏（バッファ）
- 人口分布（白→オレンジ→赤のグラデーション）

レイヤーごとにON/OFF切替が可能で、「公共交通カバー圏内に人口がどう分布しているか」を直感的に把握できる。

---

## 使用データ

| データ | 提供元 | 備考 |
|---|---|---|
| 路面電車 GTFS | 岡山電気軌道 | テスト配信中 |
| 両備バス GTFS | 両備バス | オープンデータ |
| 岡電バス GTFS | 岡電バス | オープンデータ |
| 500mメッシュ人口 | e-Stat（令和2年国勢調査） | 無料ダウンロード |

GTFSデータの取得先：[岡山市公共交通オープンデータ](https://www.ryobi-holdings.jp/bus/)

人口メッシュデータの取得先：[e-Stat 統計地理情報システム](https://www.e-stat.go.jp/gis/statmap-search?type=1)

---

## 環境

- Python 3.11+
- pandas
- geopandas
- folium
- shapely

```bash
pip install pandas geopandas folium
```

---

## 使い方

1. GTFSデータを以下の構成で配置する

```
0kayama_GTFS/
  ├── ryobi/        # 両備バス
  ├── okaden/       # 岡電バス
  ├── gtfs/         # 路面電車
  └── tblT001101H33/
        └── tblT001101H33.txt  # 人口メッシュ
```

2. スクリプト内のパスを環境に合わせて修正する

```python
BASE_DIR = r"C:\Users\yourname\Downloads\0kayama_GTFS"
```

3. 実行する

```bash
python okayama_transit_map.py
```

4. 生成された `okayama_transit_map.html` をブラウザで開く

---

## 出力イメージ

- ベースマップ：OpenStreetMap
- 路面電車：赤
- 両備バス：青
- 岡電バス：オレンジ
- 人口密度：白→オレンジ→赤（令和2年国勢調査）

---

## 今後の予定

- [ ] 立地適正化計画の居住誘導区域との重ね合わせ
- [ ] 公共交通カバー率の定量分析
- [ ] 他都市への展開（仙台・福岡等）
- [ ] GitHub Pagesでの地図公開

---

## ライセンス

MIT License

使用データの利用規約については各提供元を参照のこと。
