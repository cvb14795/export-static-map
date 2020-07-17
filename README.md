# export-static-map
`export-static-map` is a Python program for plotting static base map and export to image file to display.

------

`export-static-map`為基於Python3的GIS（地理資訊系統）出圖程式。

## 功能：

* 可串接OpenStreetMap之地圖API
* 支援.shp、.csv、.kml .asc 等資料來源 (*)
* 僅需提供檔案名稱、圖層顏色之色碼即可出圖

## 所需第三方模組：

* cartopy == 0.17.0
* numpy >= 1.18.4
* geopandas >= 0.7.0
* fiona >= 1.8.13
* matplotlib >= 3.2.1	
* rasterio >= 1.1.5

## Note:

* 地圖API目前僅支援OpenStreetMap (OSM)。
* .asc檔案格式支援尚在實驗階段。
