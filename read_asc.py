import os
import rasterio
import rasterio.features
import rasterio.warp
from rasterio.warp import calculate_default_transform, reproject
from tempfile import TemporaryDirectory

class ReadASC:
    def getGeometry(self, f):
        geojson_list = []
        with TemporaryDirectory() as temp_dir:
            # 複製原檔案 將crs寫到暫存檔
            org_path = ".\\input\\{}.asc".format(f)
            temp_path = "{}\\temp_{}.tif".format(temp_dir, f)
            # ASCII預設之CRS & GeoTiff投影前CRS
            src_crs = 'EPSG:3826'
            # GeoTiff投影後CRS
            dst_crs = 'EPSG:4326'
            # ASCII轉GeoTiff
            os.system("gdal_translate -of GTiff -a_srs " + src_crs + " " + org_path + " " + temp_path)
            # 獲取投影轉換參數
            with rasterio.open(temp_path, mode='r') as src:
                print("cellSize(x,y): ", src.res)
                print("shape: ", src.width, "cols,", src.height, "rows")
                transform, width, height = calculate_default_transform(
                    src.crs, dst_crs, src.width, src.height, *src.bounds)
                kwargs = src.meta.copy()
                kwargs.update({
                    'crs': dst_crs,
                    'transform': transform,
                    'width': width,
                    'height': height
                })
                # 將src_crs重新投影為dst_crs
                dst_path = "{}\\temp_{}_WGS84.tif".format(temp_dir, f)
                with rasterio.open(dst_path, mode='w', **kwargs) as dst:
                    for i in range(1, src.count + 1):
                        reproject(
                            source=rasterio.band(src, i),
                            destination=rasterio.band(dst, i),
                            src_transform=src.transform,
                            src_crs=src.crs,
                            dst_transform=transform,
                            dst_crs=dst_crs)
                    print("轉換為： {}".format(dst.crs))
                    print("正在讀取{} 資料中，請稍候...".format(f))
            with rasterio.open(dst_path) as src:
                image = src.read(1)  # first band
                self.max_raster_val = image.max()
                mask = src.dataset_mask()
                results = (
                    {'properties': {'raster_val': v}, 'geometry': s}
                    for i, (s, v)
                    in enumerate(
                    rasterio.features.shapes(image, mask=mask, transform=src.transform)))
            geom = list(results)
            return geom

    def getRasterMaxValue(self):
        return self.max_raster_val