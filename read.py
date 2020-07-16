# -*- coding: utf-8 -*-
from configparser import ConfigParser
from fiona.errors import DriverError
from fiona.drvsupport import supported_drivers
import geopandas as gp
import matplotlib.pyplot as plt
import numpy as np
import os
import ogr2ogr
import rasterio
from rasterio.crs import CRS
from rasterio.warp import calculate_default_transform, reproject
import shutil
from tempfile import TemporaryDirectory


class ReadInput:
    def __init__(self):
        self.read_files = []
        self.read_colors = []
        self.file_set = []
        self.df_set = []
        self.raster_set = []
        self.color_set = []
        # 副檔名
        self.ext = []
        # gp.read_file的options (csv)
        self.options = {}

    def readConfig(self):
        i = 0
        cfg = ConfigParser()
        cfg.read('config.ini', encoding='utf-8-sig')
        # 由ini讀入各格式檔名
        for section in cfg.sections():
            self.read_files.append(cfg[section]['name'])
            self.read_colors.append(cfg[section]['color'])
            if self.read_colors[i] != "":
                cs = self.read_colors[i].split(',')
                for c in cs:
                    c.strip()
                    # 讀到colormap時
                    if not c.startswith('#'):
                        cmap = plt.get_cmap(c)
                        CLASSES = 5  # 顏色漸層分幾類
                        colors = cmap(np.linspace(0, 1, CLASSES))
                        self.color_set.append(colors)
                    # 讀到色碼時
                    else:
                        self.color_set.append(c)
            i += 1
            self.ext.append(section.split('file_')[1])
            print("\n{} 發現檔案:".format(section))
            for temp in self.read_files[cfg.sections().index(section)].split(','):
                print(temp.strip()) if temp != "" else print("沒有發現任何檔案")

    def readInputFile(self):
        def readASC(f, tmp_dir, out_path, index):
            with TemporaryDirectory(dir=tmp_dir) as temp_dir:
                # 複製原檔案 將crs寫到暫存檔
                org_path = ".\\input\\{}.{}".format(f, self.ext[index])
                temp_path = "{}\\temp_{}.{}".format(temp_dir, f, self.ext[index])
                shutil.copy(org_path, temp_path)
                dst_crs = 'epsg:4326'
                # 不使用rasterio.open
                # mode='r+'會在覆寫已打開的檔案時將發生ERROR 1: Deleting (file_name) failed: Permission denied
                # see: https://rasterio.groups.io/g/main/topic/64368748
                if not os.path.exists(os.path.splitext(org_path)[0] + ".prj"):
                    crs_3826 = CRS.from_epsg(3826)
                    with open(os.path.splitext(temp_path)[0] + ".prj", "w") as prj:
                        prj.write(crs_3826.to_wkt())
                with rasterio.open(temp_path, mode='r') as src:
                    print(src.bounds)
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
                    with rasterio.open(out_path, mode='w', **kwargs) as dst:
                        for i in range(1, src.count + 1):
                            reproject(
                                source=rasterio.band(src, i),
                                destination=rasterio.band(dst, i),
                                src_transform=src.transform,
                                src_crs=src.crs,
                                dst_transform=transform,
                                dst_crs=dst_crs)
                        print("轉換為： {}".format(dst.crs))
                        self.raster_set.append(out_path)
        i = 0
        try:
            # 讀檔
            for files in self.read_files:
                if files != "":
                    # 重置參數
                    self.options = {}
                    # 分割當前種類檔名
                    fs = files.split(',')
                    for f in fs:
                        # 去除空白
                        f = f.strip()
                        self.file_set.append("{}.{}".format(f, self.ext[i]))
                        '''dataframe前處理'''
                        # shp檔
                        if self.ext[i] == 'shp':
                            pass
                        # csv檔
                        elif self.ext[i] == 'csv':
                            # 啟用指定的fiona驅動
                            # see: https://gdal.org/drivers/vector/index.html
                            supported_drivers['CSV'] = 'rw'
                            # 指定經緯度參數的欄位名稱
                            # see: https://gdal.org/drivers/vector/csv.html#reading-csv-containing-spatial-information
                            self.options['X_POSSIBLE_NAMES'] = 'Lon'
                            self.options['Y_POSSIBLE_NAMES'] = 'Lat'
                        # kml檔
                        elif self.ext[i] == 'kml':
                            # kml轉shp shp檔存在 "input\\KML\\當前檔名" 資料夾下
                            out_dir = ".\\input\\KML\\{}".format(f)  # 資料夾路徑
                            out_path = "{}\\{}.shp".format(out_dir, f)  # 檔案路徑
                            if not os.path.exists(out_dir):
                                os.makedirs(out_dir)
                            ogr2ogr.main(["", "-f", "ESRI Shapefile", out_path, ".\\input\\{}.kml".format(f),
                                          "-dim", "2",
                                          "-lco", "ENCODING=UTF-8"])
                            # supported_drivers['libkml'] = 'rw'
                            # supported_drivers['LIBKML'] = 'rw'
                            # self.options['driver']='KML'

                        '''讀取為dataframe'''
                        print("\n讀取檔案: {}.{}".format(f, self.ext[i]))
                        if self.ext[i] == 'kml':
                            df = gp.read_file(out_path, encoding='utf-8')
                        elif self.ext[i] == 'asc':
                            # 欲座標轉換的asc檔 存在"input\\ASC\\當前檔名" 資料夾下
                            out_dir = ".\\input\\ASC\\{}".format(f)
                            out_path = "{}\\{}_WGS84.{}".format(out_dir, f, self.ext[i])
                            if not os.path.exists(out_dir):
                                os.makedirs(out_dir)
                            readASC(f, out_dir, out_path, i)
                            continue
                        else:
                            df = gp.read_file(".\\input\\{}.{}".format(f, self.ext[i]), encoding='utf-8',
                                              **self.options)

                        df.crs = {'init': 'epsg:4326'}  # 避免input沒給 這邊給預設值(WGS84)
                        print("原座標系統： {}".format(df.crs))
                        # 座標轉換
                        df = df.to_crs(epsg=4326)
                        print("轉換為： {}".format(df.crs))

                        # 只取geometry
                        # search = u"臺北市"
                        # df = df[df['COUNTYNAME'].isin(["臺北市"])]
                        print(df.head())
                        # df = df[['COUNTYNAME','geometry']]
                        df = df[['geometry']]
                        df.reset_index(drop=True)
                        self.df_set.append(df)
                        df.plot()
                i += 1
            return True, self.file_set, self.df_set, self.raster_set, self.color_set
        except DriverError:
            print("無法讀取檔案: {}!".format(f))
            return False, [], [], [], []