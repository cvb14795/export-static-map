import os
from osgeo import gdal, osr
import rasterio
import rasterio.features
import rasterio.warp
from rasterio.warp import calculate_default_transform, reproject
import shutil

class ReadASC:
    def __init__(self):
        self._cfg_min_val = 0.0  # colormap預設最小值
        self._cfg_max_val = 1.0  # colormap預設最大值
        self._max_raster_val = -999.999  # 讀入檔案之資料ASCII最大值 讀入前預設-999.999

    # cfg_min_val
    @property
    def cfg_min_val(self):
        return self._cfg_min_val

    @cfg_min_val.setter
    def cfg_min_val(self, value):
        self._cfg_min_val = value

    # cfg_max_val
    @property
    def cfg_max_val(self):
        return self._cfg_max_val

    @cfg_max_val.setter
    def cfg_max_val(self, value):
        self.cfg_max_val = value

    # max_raster_val
    @property
    def max_raster_val(self):
        return self._max_raster_val

    @max_raster_val.setter
    def max_raster_val(self, value):
        self._max_raster_val = value

    def getGeometry(self, f, temp_dir=".\\temp"):
        geom = []
        err_msg = ""
        def removeDir(dir):
            if os.path.exists(dir):
                if len(os.listdir(dir)) != 0:  # 因前次執行error有殘餘資料
                    shutil.rmtree(dir)
                else:
                    os.rmdir(dir)

        removeDir(temp_dir)
        os.makedirs(temp_dir)
        # 複製原檔案 將crs寫到暫存檔
        org_path = ".\\input\\{}.asc".format(f)
        temp_path = "{}\\temp_{}.tif".format(temp_dir, f)
        # ASCII預設之CRS & GeoTiff投影前CRS
        src_crs = 'EPSG:3826'
        # GeoTiff投影後CRS
        dst_crs = 'EPSG:4326'
        # ASCII轉GeoTiff
        # os.system("gdal_translate -of GTiff -a_srs " + src_crs + " " + org_path + " " + temp_path)

        # 開啟dataset
        ds = gdal.Open(org_path)
        if not ds:
            err_msg += "無法開啟暫存檔案：{}！".format(os.path.realpath(temp_dir))
            return False, err_msg, geom
        ds = gdal.Translate(destName=temp_path, srcDS=ds, format="GTiff", outputSRS=src_crs)
        # 關閉dataset
        ds = None
        if not os.path.exists(temp_path):  # 寫入失敗
            err_msg += "無法寫入暫存檔案：{}！".format(os.path.realpath(temp_dir))
            return False, err_msg, geom

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
            print("raster_val最大值: {:.4f}".format(self.max_raster_val))
            mask = src.dataset_mask()
            results = (
                {'properties': {'raster_val': v}, 'geometry': s}
                for i, (s, v)
                in enumerate(rasterio.features.shapes(image, mask=mask, transform=src.transform)))
        geom = list(results)
        removeDir(temp_dir)
        return True, err_msg, geom

    def calcValRange(self, val):
        if val < self.cfg_min_val:  # 小於最小值用最小值
            val = self.cfg_min_val
        elif val > self.cfg_max_val:  # 大於最大值用最大值
            val = self.cfg_max_val
        return val / self.max_raster_val
