# gis_export_image
`gis_export_image`為基於Python 3的GIS（地理資訊系統）出圖程式。  
`gis_export_image` is a Python program for plotting static base map and export to image file to display.

------

## 功能：

* 可串接OpenStreetMap之地圖API
* 支援.shp、.csv、.kml等資料來源
* 僅需提供檔案名稱、圖層顏色之色碼即可出圖

## 使用範例：
![image](https://github.com/cvb14795/export-static-map/blob/master/img/Example.jpg)
點擊右方連結以觀看更詳細的範例：https://github.com/cvb14795/export-static-map/blob/master/ExportPic.ipynb
  ### 資料來源:  
  > 台灣_鄉鎮市區界線： https://data.gov.tw/dataset/7441  
  > 氣象測站：https://e-service.cwb.gov.tw/wdps/obs/state.htm <br>
  

## 所需第三方模組：

* cartopy == 0.17.0
* numpy >=1.18.4
* geopandas >= 0.7.0
* fiona >= 1.8.13
* matplotlib >=3.2.1	
* rasterio >= 1.1.5

## Note:

地圖API目前僅支援OpenStreetMap (OSM)。
