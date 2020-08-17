# -*- coding: utf-8 -*-
import cartopy.crs as ccrs
from cartopy.io.img_tiles import OSM
import time
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import math
import os, sys
import read
# cartpy0.17
import six
from PIL import Image
# 針對打包exe後之環境變數配置
#os.environ["GDAL_DATA"] = os.path.realpath(".\\lib\\osgeo\\data\\gdal")
#os.environ["PROJ_LIB"] = os.path.realpath(".\\lib\\osgeo\\data\\proj")
class ExportPic:
    def __init__(self):
        print("設置環境變數...")
        print("GDAL_DATA: ", os.environ["GDAL_DATA"])
        print("PROJ_LIB: ", os.environ["PROJ_LIB"])
        self.reading = read.ReadInput()
        resCfgIni, self.err_msg, self.title, self.bound = self.reading.readConfig()
        if not resCfgIni:
            print(self.err_msg)
            sys.exit(1)
        resCfgFile, self.err_msg, self.file_set, self.df_set, self.color_set = self.reading.readInputFile()
        if not resCfgFile:
            print(self.err_msg)
            sys.exit(1)


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
                if len(df) != 0:
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

        # 沒有自訂bound 使用資料之最大邊界為bound
        if len(self.bound) == 0:
            self.bound = getLngLatBounds()

        # fig與legend固定4比1
        # 字體大小12pt
        # legend超出則裁切
        # 解決matplotlib本身不支援中文字體 會顯示成方塊的問題
        # see： https://stackoverflow.com/questions/10960463/non-ascii-characters-in-matplotlib
        plt.rcParams['axes.unicode_minus'] = False  # 解決負號 '-' 顯示為方塊的問題
        plt.rc('font', **{'sans-serif': 'Microsoft JhengHei',  # 指定中文字體 (微軟正黑體)
                          'family': 'sans-serif',
                          'size': 12})  # 指定默認字型
        self.dpi = 300
        fig = plt.figure(dpi=self.dpi)
        ax = fig.add_subplot(1, 1, 1, projection=ccrs.PlateCarree())

        ax.set_title(self.title)
        ax.set_extent(self.bound, ccrs.PlateCarree())
        # 獲取fig框像素大小
        fig_size = fig.get_size_inches() * fig.dpi
        mapDim = {"height": int(fig_size[0]),
                  "width": int(fig_size[1])}
        # 計算zoom_level
        zoom_lv = getBoundsZoomLevel(self.bound, mapDim)
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
        #ax.add_image(imagery, zoom_lv, regrid_shape=regrid)
        ax.add_image(imagery, zoom_lv)
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
                        #bbox_extra_artists=(self.lg,),
                        bbox_inches='tight'
                        )
            et = time.time() - st
            print("成功! 存檔耗時{:.2f}秒".format(et))

        ax = self.getAx()
        patchs = []
        labels = []
        for i, (label, color, data) in enumerate(zip(self.file_set, self.color_set, self.df_set)):
            if sum(data.geom_type == 'Point') != 0:
                ax.scatter([point.x for point in data.geometry],
                           [point.y for point in data.geometry],
                           s=[2 for index in range(len(data.geometry))],  # s = size:控制每個點大小的list
                           c=color,
                           alpha=0.6,
                           transform=ccrs.PlateCarree(),
                           zorder=2)  # Zorder:大的在上面
            elif sum(data.geom_type == 'MultiPoint') != 0:
                for points in data.geometry:
                    ax.scatter([point.x for point in points],
                               [point.y for point in points],
                               s=[2 for index in range(len(data.geometry))],
                               c=color,
                               alpha=0.6,
                               transform=ccrs.PlateCarree(),
                               zorder=2)
            elif os.path.splitext(label)[1] == ".asc":
                cmap = plt.get_cmap(color)
                color = cmap
                for poly, val in zip(data.geometry, data.raster_val):
                    cmap_result = self.reading.asc.calcValRange(val)

                    ax.add_geometries([poly],
                                      ccrs.PlateCarree(),
                                      edgecolor=None,
                                      # facecolor=cmap((val / max_raster_val)),
                                      facecolor=cmap(cmap_result),
                                      alpha=0.85,
                                      zorder=3
                                      )
            else:  # 其他檔案類型的polygon
                # add_geomrtries把資料視為polygon匯入 若是point add後會沒有東西
                ax.add_geometries(data.geometry,
                                  ccrs.PlateCarree(),
                                  edgecolor='white',
                                  facecolor=color,
                                  alpha=0.5,
                                  zorder=1)
            # plt.plot的圖例可指定實例讓handles自動生成
            # add_geometries的圖例需由mpatches.Patch生成
            label_color = color if os.path.splitext(label)[1] != ".asc" else color(0)
            patchs.append(mpatches.Patch(color=label_color,
                                         label=label))
        self.lg = plt.legend(handles=patchs,
                             bbox_to_anchor=(1.05, 1),  # (0,0):軸左下 ; (1,1):軸右上
                             loc='upper left',
                             borderaxespad=0.)
        try:
            savePicure()
            #先savefig再show 否則圖片空白
            #plt.show()
        except ValueError:
            # 找不到tiles
            self.err_msg += "獲取背景圖tiles時發生錯誤，請檢查網路連線!"
            print(self.err_msg)
            sys.exit(1)


if __name__ == "__main__":
    main = ExportPic()
    main.plot()
    os.system("pause")
