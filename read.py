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
        self.title = "GIS出圖程式範例"
        # 邊界(畫面顯示範圍)
        self.bound = []
        # gp.read_file的options (csv)
        self.options = {}
        self.temp_dir = ".\\temp"
        self.err_msg = ""

    def readConfig(self):
        cfg = ConfigParser()
        cfgName = "config.ini"
        print("\n載入{}中...".format(cfgName))
        cfgPath = ".\\{}".format(cfgName)
        res = len(cfg.read(cfgPath, encoding='utf-8-sig'))
        if not res:
            self.err_msg += "{}檔案不存在！\n請檢查路徑: {}！".format(cfgName, os.path.realpath(cfgPath))
            return False, self.err_msg, self.title, self.bound
        # 由ini讀入各格式檔名
        cfg_file = cfg.sections()

        # 讀取標題
        print("讀取標題...")
        temp_title = cfg["title"]['name'].strip()
        if temp_title != "":
            self.title = temp_title
        else:
            print("讀取標題為空白！將設置為預設標題")
        print("標題設置為: {}".format(self.title))
        cfg_file.pop(cfg_file.index("title"))

        # 讀取bound
        print("\n讀取bound之自訂輸出畫面範圍...")
        blank = 0
        for i, (key, value) in enumerate(list(cfg["bound"].items())):
            try:
                if value == "":
                    blank += 1
                else:
                    deg = float(value)
                    if key == "minx" or key == "maxx":
                        if abs(deg) > 180:  # 經度-180 ~ 180之外
                            raise ValueError
                    elif key == "miny" or key == "maxy":
                        if abs(deg) > 90:  # 緯度-90 ~ 90之外
                            raise ValueError
                    self.bound.append(deg)
                print("欄位:'{}', 值: '{}',".format(key, value))
            except ValueError:
                self.err_msg += "{}欄位內包含非法值：{}！請檢查是否為正確的經緯度表示方式！".format(key, value)
                self.err_msg += "\n若不想設置bound，請將minX,maxX,minY,maxY四個欄位全部留空！"
                return False, self.err_msg, self.title, self.bound
        if blank == 4:
            self.bound = []
            self.err_msg += "bound全部留空，將計算最貼合資料之範圍為顯示範圍！"
        elif blank != 0:
            self.err_msg += "bound內有一部分留空值，一部分為數字值！\n若不想設置bound，請將minX,maxX,minY,maxY四個欄位全部留空！"
            return False, self.err_msg, self.title, self.bound

        cfg_file.pop(cfg_file.index("bound"))

        # 讀取檔案
        for i, section in enumerate(cfg_file):
            if section.startswith("file_"):
                self.read_files.append(cfg[section]['name'])
                self.read_colors.append(cfg[section]['color'])
                self.ext.append(section.split('file_')[1])
                if self.ext[i] == "asc":
                    try:
                        print("\n讀取asc檔案之自訂顏色顯示範圍...")
                        for key, value in zip(("minvalue", "maxvalue"),
                                              (self.asc.cfg_min_val, self.asc.cfg_max_val)):
                            if cfg[section][key] != "":
                                value = float(cfg[section][key])
                            else:
                                print("{}留空，將設置為預設值！".format(key))
                            print("欄位:'{}', 值: '{}',".format(key, value))
                    except ValueError:
                        self.err_msg += "{}欄位內包含非法值：{}！請檢查是否為正確的數字表示方式！".format(key, cfg[section][key])
                        return False, self.err_msg, self.title, self.bound
                if self.read_colors[i] != "":
                    cs = self.read_colors[i].split(',')
                    for c in cs:
                        c.strip()
                        self.color_set.append(c)
                print("\n{} 發現檔案:".format(section))
                for temp in self.read_files[cfg_file.index(section)].split(','):  # 迭代該種類下的每個檔名
                    print(temp.strip()) if temp != "" else print("沒有發現任何檔案")
        return True, self.err_msg, self.title, self.bound

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
                            res, err, geom = self.asc.getGeometry(f, self.temp_dir)
                            if not res:
                                self.err_msg += err
                                return False, self.err_msg, self.file_set, self.df_set, self.color_set
                            else:
                                df = gp.GeoDataFrame.from_features(geom)
                                print(df.head())
                                self.df_set.append(df)
                            continue
                        else:
                            df = gp.read_file(".\\input\\{}.{}".format(f, self.ext[i]), encoding='utf-8',
                                              **self.options)

                        # {'init': 'epsg:4326'}會導致xy軸座標交換的錯誤
                        # see: https://github.com/pyproj4/pyproj/issues/355
                        df.crs = 'EPSG:4326'  # 避免input沒給 這邊給預設值(WGS84)
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
            return True, self.err_msg, self.file_set, self.df_set, self.color_set
        except DriverError:
            self.err_msg += "無法讀取檔案: {}!".format(f)
            return False, self.err_msg, self.file_set, self.df_set, self.color_set