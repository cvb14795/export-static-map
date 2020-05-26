# -*- coding: utf-8 -*-
import geopandas as gp
from configparser import ConfigParser
import mplleaflet

cfg = ConfigParser()
cfg.read('config.ini')
ftype = cfg['file']['filetype']
fname = cfg['file']['filename']

df = gp.read_file("./input/{}.{}".format(fname, ftype), encoding='utf-8')
print("檔案原座標系統： ", df.crs)

# 轉為WGS84座標
df = df.to_crs(epsg=4326)
# 只取geometry
df = df[['geometry']]
df.head()

ax = df.plot(color="red")
mplleaflet.show(fig=ax.figure)
#df.to_file("./output/result.shp")

# imagery = OSM()
# print(type(imagery.crs))
# fig, ax = plt.subplots(subplot_kw={'projection': imagery.crs})
#
# gl = ax.gridlines(draw_labels=True)
# gl.xlabels_top = gl.ylabels_right = False
# gl.xformatter = LONGITUDE_FORMATTER
# gl.yformatter = LATITUDE_FORMATTER
#
# ax.set_extent([120, 122, 21.8, 25.4])
# ax.add_image(imagery, 8)

