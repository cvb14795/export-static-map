# -*- coding: utf-8 -*-
from configparser import ConfigParser
import cartopy.crs as ccrs
from cartopy.io.img_tiles import OSM
from fiona.errors import DriverError
from fiona.drvsupport import supported_drivers
import geopandas as gp
import time
from tempfile import TemporaryDirectory
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import math
import numpy as np
import os, sys
import ogr2ogr
import rasterio
from rasterio.crs import CRS
import rasterio.plot
from rasterio.warp import calculate_default_transform, reproject
import shutil
import stat
# cartpy0.17bug
import six
from PIL import Image


class ExportPic:
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
        def readASC(tmp_dir, out_path, index):
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
                        self.file_set.append("{}.{}".format(f,self.ext[i]))
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
                            out_path = "{}\\{}.shp".format(out_dir,f)  # 檔案路徑
                            if not os.path.exists(out_dir):
                                os.makedirs(out_dir)
                            ogr2ogr.main(["","-f", "ESRI Shapefile", out_path, ".\\input\\{}.kml".format(f),
                                          "-dim", "2",
                                          "-lco", "ENCODING=UTF-8"])
                            #supported_drivers['libkml'] = 'rw'
                            #supported_drivers['LIBKML'] = 'rw'
                            #self.options['driver']='KML'

                        '''讀取為dataframe'''
                        print("\n讀取檔案: {}.{}".format(f, self.ext[i]) )
                        if self.ext[i] == 'kml':
                            df = gp.read_file(out_path, encoding='utf-8')
                        elif self.ext[i] == 'asc':
                            # 欲座標轉換的asc檔 存在"input\\ASC\\當前檔名" 資料夾下
                            out_dir = ".\\input\\ASC\\{}".format(f)
                            out_path = "{}\\{}_WGS84.{}".format(out_dir, f, self.ext[i])
                            if not os.path.exists(out_dir):
                                os.makedirs(out_dir)
                            readASC(out_dir, out_path, i)
                            continue
                        else:
                            df = gp.read_file(".\\input\\{}.{}".format(f, self.ext[i]), encoding='utf-8', **self.options)

                        df.crs = {'init': 'epsg:4326'} # 避免input沒給 這邊給預設值(WGS84)
                        print("原座標系統： {}".format(df.crs))
                        # 座標轉換
                        df = df.to_crs(epsg=4326)
                        print("轉換為： {}".format(df.crs))

                        # 只取geometry
                        #search = u"臺北市"
                        #df = df[df['COUNTYNAME'].isin(["臺北市"])]
                        print(df.head())
                        #df = df[['COUNTYNAME','geometry']]
                        df = df[['geometry']]
                        df.reset_index(drop=True)
                        self.df_set.append(df)
                        df.plot()
                i += 1
        except DriverError:
            print("無法讀取檔案: {}!".format(f))

    def getAx(self):
        def newGetImage(self, tile):
            if six.PY3:
                from urllib.request import urlopen, Request
            else:
                from urllib2 import urlopen
            url = self._image_url(tile)  # added by H.C. Winsemius
            req = Request(url)  # added by H.C. Winsemius
            req.add_header('User-agent', 'your bot 0.1')
            # fh = urlopen(url)  # removed by H.C. Winsemius
            fh = urlopen(req)
            im_data = six.BytesIO(fh.read())
            fh.close()
            img = Image.open(im_data)

            img = img.convert(self.desired_tile_form)

            return img, self.tileextent(tile), 'lower'

        def getBoundsZoomLevel(bound, mapDim):
            WORLD_DIM = {"height": 256,
                         "width": 256}
            ZOOM_MAX = 20

            def latRad(lat):
                sin = math.sin(lat * math.pi / 180)
                radX2 = math.log((1 + sin) / (1 - sin)) / 2
                return max(min(radX2, math.pi), -math.pi) / 2

            def zoom(mapPx, worldPx, fraction):
                return math.floor(math.log(mapPx / worldPx / fraction) / math.log(2))

            # 計算採用googlemap格式 (緯度,經度)
            # 右上
            ne = {"lat": bound[3],
                  "lng": bound[1]}
            # 左下
            sw = {"lat": bound[2],
                  "lng": bound[0]}

            latFraction = (latRad(ne["lat"]) - latRad(sw["lat"])) / math.pi

            lngDiff = ne["lng"] - sw["lng"]
            lngFraction = ((lngDiff + 360) / 360) if lngDiff < 0 else (lngDiff / 360)

            latZoom = zoom(mapDim["height"], WORLD_DIM["height"], latFraction)
            lngZoom = zoom(mapDim["width"], WORLD_DIM["width"], lngFraction)

            return min(latZoom, lngZoom, ZOOM_MAX)

        def getLngLatBounds():
            # !
            # 迭代各dataframe 回傳經緯度min/max (minx/maxx/miny/maxy)
            bound = [9999, 0, 9999, 0]  # 預設值
            for df in self.df_set:
                bounds = df.geometry.bounds
                # 檢查各值 有更大的框則更新
                bound = [min(bounds.minx) if min(bounds.minx) < bound[0] else bound[0],  # 最小經度
                         max(bounds.maxx) if max(bounds.maxx) > bound[1] else bound[1],  # 最大經度
                         min(bounds.miny) if min(bounds.miny) < bound[2] else bound[2],  # 最小緯度
                         max(bounds.maxy) if max(bounds.maxy) > bound[3] else bound[3]]  # 最大緯度
                # margin_lng = (bound[0] - bound[1]) * 0.03
                # margin_lat = (bound[2] - bound[3]) * 0.03
                # bound = list(map(lambda x, y: x + y, bound, [-margin_lng, +margin_lng, -margin_lat, +margin_lat]))
            return bound

        bound = getLngLatBounds()
        # fig與legend固定4比1
        # 字體大小12pt
        # legend超出則裁切
        # 解決matplotlib本身不支援中文字體 會顯示成方塊的問題
        # see： https://stackoverflow.com/questions/10960463/non-ascii-characters-in-matplotlib
        plt.rcParams['axes.unicode_minus'] = False  # 解決負號 '-' 顯示為方塊的問題
        plt.rc('font', **{'sans-serif': 'Microsoft JhengHei',  # 指定中文字體 (微軟正黑體)
                          'family': 'sans-serif'})  # 指定默認字型
        self.dpi = 300
        fig = plt.figure(dpi=self.dpi)
        ax = fig.add_subplot(1, 1, 1, projection=ccrs.PlateCarree())

        ax.set_title("測試")
        ax.set_extent(bound, ccrs.PlateCarree())
        # 獲取fig框像素大小
        fig_size = fig.get_size_inches() * fig.dpi
        mapDim = {"height": int(fig_size[0]),
                  "width": int(fig_size[1])}
        # 計算zoom_level
        zoom_lv = getBoundsZoomLevel(bound, mapDim)
        print("計算最佳zoom_level: ", zoom_lv)

        OSM.get_image = newGetImage
        imagery = OSM()

        # interpolation: matplotlib抗鋸齒
        # 0.18版更新 可修正下述bug
        # cartopy0.18版interpolation的bug
        # see: https://github.com/SciTools/cartopy/issues/1563
        # cartopy0.17版add_image的bug
        # see: https://github.com/SciTools/cartopy/issues/1341

        inter = 'spline36'
        # regrid_shape: basemap長寬之短邊尺寸
        regrid = max(mapDim.values())
        # ax.add_image(imagery, zoom, interpolation=inter, regrid_shape=regrid)
        ax.add_image(imagery, zoom_lv, regrid_shape=regrid)
        # 色碼表： https://www.ebaomonthly.com/window/photo/lesson/colorList.htm
        return ax

    def plot(self):
        def savePicure():
            st = time.time()
            print("正在儲存影像檔，請稍候...")
            plt.savefig('.\\output\\result.jpg',
                        dpi=self.dpi,
                        #!
                        # 防止圖例轉圖像時被裁剪
                        bbox_extra_artists=(self.lg,),
                        bbox_inches='tight'
                        )
            et = time.time() - st
            print("成功! 存檔耗時{:.1f}秒".format(et))

        ax = self.getAx()
        patchs = []
        data_set = self.df_set + self.raster_set
        for i, (label, color, data) in enumerate(zip(self.file_set, self.color_set, data_set)):
            # vector檔
            if i < len(self.df_set):
                if sum(data.geom_type == 'Point') != 0:
                    ax.scatter([point.x for point in data.geometry],
                               [point.y for point in data.geometry],
                               s=[2 for j in range(len(data.geometry))],  # s = size:控制每個點大小的list
                               c=color,
                               alpha=0.6,
                               transform=ccrs.PlateCarree(),
                               zorder=2)  # Zorder:大的在上面
                elif sum(data.geom_type == 'MultiPoint') != 0:
                    for points in data.geometry:
                        ax.scatter([point.x for point in points],
                                   [point.y for point in points],
                                   s=[2 for i in range(len(data.geometry))],
                                   c=color,
                                   alpha=0.6,
                                   transform=ccrs.PlateCarree(),
                                   zorder=2)
                else:  # polygon
                    c='blue'
                    # add_geomrtries把資料視為polygon匯入 若是point add後會沒有東西
                    ax.add_geometries(data.geometry,
                                      ccrs.PlateCarree(),
                                      edgecolor='white',
                                      facecolor=color,
                                      alpha=0.5,
                                      zorder=1)
                # plt.plot的圖例可指定實例讓handles自動生成
                # add_geometries的圖例需由mpatches.Patch生成
                patchs.append(mpatches.Patch(color=color,
                                             label=label))
            # raster檔
            else:
                with rasterio.open(data) as src:
                    rasterio.plot.show(src, ax=ax)
        self.lg = plt.legend(handles=patchs,
                             bbox_to_anchor=(1.05, 1))  # (0,0):軸左下 ; (1,1):軸右上
                             # loc='upper left',
                             # borderaxespad=0.
        try:
            savePicure()
        except ValueError:
            # 找不到tiles
            print("獲取背景圖tiles時發生錯誤，請檢查網路連線!")
            sys.exit(0)
        plt.show()


if __name__ == "__main__":
    main = ExportPic()
    main.readConfig()
    main.readInputFile()
    main.plot()
    os.system("pause")





