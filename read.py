# -*- coding: utf-8 -*-
from configparser import ConfigParser
from fiona.errors import DriverError
from fiona.drvsupport import supported_drivers
import geopandas as gp
import os
import ogr2ogr
import read_asc

class ReadInput:
    def __init__(self):
        self.asc = read_asc.ReadASC()
        self.read_files = []
        self.read_colors = []
        self.file_set = []
        self.df_set = []
        self.color_set = []
        # 副檔名
        self.ext = []
        # 標題
        self.title = "請輸入標題..."
        # gp.read_file的options (csv)
        self.options = {}
        self.max_raster_val = -999.999

    def readConfig(self):
        cfg = ConfigParser()
        cfg.read('config.ini', encoding='utf-8-sig')
        # 由ini讀入各格式檔名
        cfg_file = cfg.sections()

        temp_title = cfg["title"]['name'].strip()
        if temp_title != "":
            self.title = temp_title

        cfg_file.pop(cfg_file.index("title"))
        for i, section in enumerate(cfg_file):
            if section.startswith("file_"):
                self.read_files.append(cfg[section]['name'])
                self.read_colors.append(cfg[section]['color'])
                self.ext.append(section.split('file_')[1])
                if self.read_colors[i] != "":
                    cs = self.read_colors[i].split(',')
                    for c in cs:
                        c.strip()
                        self.color_set.append(c)
                print("\n{} 發現檔案:".format(section))
                for temp in self.read_files[cfg_file.index(section)].split(','):
                    print(temp.strip()) if temp != "" else print("沒有發現任何檔案")

    def readInputFile(self):
        def checkDirExist(dir):
            if not os.path.exists(dir):
                os.makedirs(dir)

        checkDirExist(".\\input")
        checkDirExist(".\\output")
        try:
            # 讀檔
            for i, files in enumerate(self.read_files):
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
                            checkDirExist(out_dir)
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
                            temp_root = ".\\input\\temp"
                            temp_dir = "{}\\{}".format(temp_root, f)
                            if not os.path.exists(temp_dir):
                                os.makedirs(temp_dir)
                            geom = self.asc.getGeometry(f)
                            self.max_raster_val = self.asc.getRasterMaxValue()
                            df = gp.GeoDataFrame.from_features(geom)
                            print(df.head())
                            self.df_set.append(df)
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
                i += 1
            return True, self.title, self.file_set, self.df_set, self.color_set, self.max_raster_val
        except DriverError:
            print("無法讀取檔案: {}!".format(f))
            return False, self.title, [], [], [], []