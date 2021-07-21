#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Mar 21 11:40:42 2021

@author: grl
"""
# IMPORTS
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import geopandas as gpd
import fiona
import pyproj as pyproj
import verde as vd
# import time

from shapely import geometry
from geopandas import GeoDataFrame


# ---------------------------- PARAMS -----------------------------------------
plt.rcParams['figure.dpi'] = 300
crs = ''

'EPSG:32723'

''''PROJCS["WGS 84 / UTM zone 23S",
    GEOGCS["WGS 84",
        DATUM["WGS_1984",
            SPHEROID["WGS 84",6378137,298.257223563,
                AUTHORITY["EPSG","7030"]],
            AUTHORITY["EPSG","6326"]],
        PRIMEM["Greenwich",0,
            AUTHORITY["EPSG","8901"]],
        UNIT["degree",0.01745329251994328,
            AUTHORITY["EPSG","9122"]],
        AUTHORITY["EPSG","4326"]],
    UNIT["metre",1,
        AUTHORITY["EPSG","9001"]],
    PROJECTION["Transverse_Mercator"],
    PARAMETER["latitude_of_origin",0],
    PARAMETER["central_meridian",-45],
    PARAMETER["scale_factor",0.9996],
    PARAMETER["false_easting",500000],
    PARAMETER["false_northing",10000000],
    AUTHORITY["EPSG","32723"],
    AXIS["Easting",EAST],
    AXIS["Northing",NORTH]]
'''

# ---------------------------- RAW DATA INPUT ---------------------------------
# First step of the preprocess, after treatment and storage of the data colect-
# ed from geological surveys, is to load the archives from the database to the
# computer's RAM. To do so, it is necessary to identify all the metadata (The
# method that the geological/geophysical information was collected and stored),
# such as:
# - Names atribuited, after survey's data-treatment, of each channel
# - Formats that each collumn is delimeted (commas, tabs, spaces)
# - Coordinates Reference System (SIRGAS 2000 / WGS 84 / etc)
# - Number of headins and subclasses of data, such as lineflights names
# - Theese and more informations are available at the survey's report made by
# - a mining company associated or not to CPRM.
'''
/ ------------------------------------------------------------------------------
/ XYZ EXPORT [12/18/2020]
/ DATABASE   [F:\Aerolevantamentos\Dados MG\Área 14\GDB\3022_GAMA.gdb]
/ ------------------------------------------------------------------------------
/
/    ALTURA       BARO    COSMICO        CTB      CTCOR      CTEXP          DATA       eTh         eU   FIDUCIAL     GPSALT          HORA         KB       KCOR        KPERC    LATITUDE  LIVE_TIME   LONGITUDE        MDT       TEMP        THB      THCOR   THKRAZAO         UB       UCOR    UKRAZAO   UTHRAZAO        UUP          X      X_WGS          Y      Y_WGS
/========== ========== ========== ========== ========== ========== ============= ========= ========== ========== ========== ============= ========== ========== ============ =========== ========== =========== ========== ========== ========== ========== ========== ========== ========== ========== ========== ========== ========== ========== ========== ==========
/
'''
# This is the heading of 'Área 14' XYZ files.

# # -------------------- Setting Columns to work --------------------------------
# g14area ---------------------------------------------------------------------
g14area_cols = 'ALTURA BARO COSMICO CTB CTCOR CTEXP DATA eTh eU FIDUCIAL GPSALT HORA KB KCOR KPERC LATITUDE LIVE_TIME LONGITUDE MDT TEMP THB THCOR THKRAZAO UB UCOR UKRAZAO UTHRAZAO UUP X UTME Y UTMN'.split(
    " ")
g14area_df = pd.read_csv('~/grafita/resources/xyz/Area_14_gama.XYZ',
                         names=g14area_cols,
                         delim_whitespace=True,
                         skiprows=8,
                         usecols=['UTME', 'UTMN',
                                  'LONGITUDE', 'LATITUDE',
                                  'X', 'Y',
                                  'MDT',
                                  'eTh', 'eU', 'KPERC', 'CTCOR',
                                  'THKRAZAO', 'UTHRAZAO', 'UKRAZAO'])
g14area_df.dropna(inplace=True)

# 1105 ------------------------------------------------------------------------
g1105_cols = 'KB DATA BARO UB THB COSMICO CTB UUP ALTURA KPERC eU eTh CTEXP UTHRAZAO UTME UTMN UKRAZAO MDT THKRAZAO LIVE_TIME CTCOR KCOR THCOR UCOR HORA GPSALT LATITUDE FIDUCIAL TEMP LONGITUDE'.split(
    " ")
g1105_df = pd.read_csv('~/grafita/resources/xyz/1105_GamaLine.XYZ',
                       names=g1105_cols,
                       delim_whitespace=True,
                       skiprows=11,
                       usecols=['UTME', 'UTMN', 'LONGITUDE', 'LATITUDE',
                                'MDT', 'eTh', 'eU', 'KPERC', 'CTCOR',
                                'THKRAZAO', 'UTHRAZAO', 'UKRAZAO'])
g1105_df.dropna(inplace=True)

# ---------------------- Channel manipulation ---------------------------------
# CHANNEL RATIOS --------------------------------------------------------------
# Creating new variables by mathematicaly minipulating the raw data, we can ex-
# tract information that was not seen before. The correlation between variables
# is a strong feature to discretize the categorical data of each point(x,y).
'''
g1039_df['THKRAZAO'] = (g1039_df.eTh/g1039_df.KPERC)
g1039_df['UKRAZAO'] = (g1039_df.eU/g1039_df.KPERC)
g1039_df['UTHRAZAO'] = (g1039_df.eU/g1039_df.eTh)
g1039_df.to_csv('~/graphite_git/resources/csv/gama/g1039_df.csv', index=False)
'''

# --------- Bounds [O, E,
#                   S, N]

# caconde = [328909.5350343678146601, 344583.3834759797900915,
#           7614012.4019015226513147, 7629149.9828700609505177]
caconde = [319409, 354084,
           7514512, 7728650]
# area14 = [292000,500000,7550000,7640000]
# g1039 = [190000, 400000, 7375000, 7700000]
# regional = []
# - = 290000,350000,7600000,7700000
Area_N_1105 = [292819.2586019417503849, 344451.6613980582915246,
               7599950.0203590430319309, 7637672.3696409575641155]

study_area = Area_N_1105
dados = g1105_df[vd.inside((g1105_df.UTME, g1105_df.UTMN), region=study_area)]

lito_ccnd = gpd.read_file(
    '/home/grl/grafita/resources/vectors/lito_Fccnd.shp',
    crs=crs)

# --------- Configure Geometry and Coordinate Reference System ----------------
'''region['geometry'] = [geometry.Point(x, y)for
                      x, y in zip(region['UTME'], region['UTMN'])]'''

g14area_df['geometry'] = [geometry.Point(x, y) for
                          x, y in zip(g14area_df['UTME'], g14area_df['UTMN'])]

g1105_df['geometry'] = [geometry.Point(x, y) for
                        x, y in zip(g1105_df['UTME'], g1105_df['UTMN'])]
'''
"+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs"
'+proj=utm +zone=23 +south +ellps=WGS84 +datum=WGS84 +units=m +no_defs'
# Proj('+proj=utm +zone=23 +south +ellps=WGS84', preserve_units=False)
# projection = pyproj.Proj(proj="merc", lat_ts=dados.LATITUDE.mean())


# ------------------- Saving Treated Data at the HD ---------------------------
# The next step, is to construct a organized DataBase to contain all data and
# store and retrieve data efficiently. GeoPackages are database format files
# that can be read and writed by GIS-softwares. With the GeoPandas Library it
# is possible to create GeoPackages by transforming DataFrames into GeoDataFra-
# mes with gpd.GeoDataFrame(dataframe, gemetry = 'geometry') and save into a
# directory.

# ---- Creating GeoDataFrames by setting geometry column
g_14area_gdf = gpd.GeoDataFrame(
    g14area_df, geometry=gpd.points_from_xy(
        g14area_df.LONGITUDE, g14area_df.LATITUDE))
g_1105_gdf = gpd.GeoDataFrame(
    g1105_df, geometry=gpd.points_from_xy(
        g1105_df.LONGITUDE, g1105_df.LATITUDE))

# ---- Exporting GeoDataFrames as a GeoPackageFile
g_14area_gdf.to_file('/home/grl/grafita/resources/gpkg/geopoints.gpkg',
                     layer='g_14area', driver='GPKG', crs=crs)
g_1105_gdf.to_file('/home/grl/grafita/resources/gpkg/geopoints.gpkg',
                   driver='GPKG', layer='g_1105', crs=crs)


# ------------------- Loading Files From the Data Base ------------------------
# ---- Geological Data (lito_'survey_code')
lito_ccnd = gpd.read_file(
    '/home/grl/grafita/resources/vectors/lito_Fccnd.shp',
    crs=crs)
# -- Getting Regions from Litological Maps Geometries
gdf_mask = read_file(
    geopandas.datasets.get_path(
        '/home/grl/grafita/resources/vectors/lito_Fccnd.shp'))

# -- Geophysical Data ('g' or 'm'_survey_code_gdf)

'''

# -------------------------- BLOCKED REDUCTIONS -------------------------------
# 1 - vd.BlockReduce---------------- CREATING A REDUCER  ----------------------
# Block reduction are dividing the region in blocks of a especified spacing
# -- Setting Coordinates

coords_1105 = (dados['UTME'].values, dados['UTMN'].values)
# coords_14area = (g_14area_gdf['UTME'].values, g_14area_gdf['UTMN'].values)

# -- Creating a reduction function with 'np.median'
reducer = vd.BlockReduce(np.median, spacing=500)
# -- Reducing the data by sampling points at a median distance of 1000 m.
b_coords, b_eU = reducer.filter(coords_1105, dados.eU)


# Then, we ne to create a function that can retrieve each survey_data that was
# a .XYZ and saved as a vector layer into a GeoPackageFile


# 2 - ---- FITTING THE LINEAR MODEL OF DECIMATEDGRID WITH SPLINE  -------------
spline = vd.Spline()
# def spline.fit():
spline.fit(b_coords, b_eU)


# 3 -------- PREDICTTING THE ACTUAL DATA WITH THE LINEAR MODEL ----------------
# the values of non-decimated dataset with the fitted linnear model
predicted = spline.predict(coords_1105)


# 3.1 CALCULATING THE DIFERENCE BETWEEN PREDICTED AND SAMPLED DATA ------------
residuals = dados.eU - predicted


# 4 ------- CREATING A SYNTHETIC SPACIAL GRID TO BE PREDICTED -----------------
# -- Generating a regular grid with VERDE by:
# Selecting region of the grid and the spacing between each pixel

region = vd.get_region(coords_1105)
# def vd.grid_coordinates():
grid_coords = vd.grid_coordinates(region, spacing=125)


# 5 -------- PREDICTTING VALUES AT SYNTHETIC GRID WITH THE LINEAR MODEL -------
# def splne.predict():
grid_eU = spline.predict(grid_coords)


# ---------------------------- CHAINING OPERATIONS ----------------------------
# 1 --- Chanining configuration -----------------------------------------------
chain = vd.Chain([
    ('trend', vd.Trend(degree=2)),
    ('reduce', vd.BlockReduce(np.median, spacing=500)),
    ('spline', vd.Spline()),
    ])
chain

# 2 --- Fitting linear model wtihin the chain the
chain.fit(coords_1105, dados.eU)
# 2 --- Plot grid
grid = chain.grid(spacing=100, data_names=['eU'])
# Figure 7 --- Plot grid from chain
plt.figure(7)
grid.eU.plot()
plt.axis('scaled')
plt.title("Predito para o grid sintético de 500 m.")

# ------------------------- Model Validation ----------------------------------
train, test = vd.train_test_split(coords_1105, dados.eU, test_size=0.1,
                                  spacing=1000)
chain.fit(*train)
chain.score(*test)

# K-Fold Cross Validation
cv = vd.BlockKFold(spacing=1000, n_splits=10, shuffle=True)
scores = vd.cross_val_score(chain, coords_1105, dados.eU, cv=cv)






# --- ------------ Plotting Figures to report ---------------------------------
# Figure 1 --------- Plotting our raw data
plt.figure(1)
plt.scatter((*coords_1105), c=dados.eU, s=0.1)
lito_ccnd.plot(column='Litologia')
plt.title('Plot dos dados brutos')
plt.axis('scaled')
# Figure 2 --------- Plotting our decimated data
plt.figure(2)
lito_ccnd.plot(column='Litologia')
plt.scatter(b_coords[0], b_coords[1], c=b_eU, s=0.3)
plt.colorbar()
plt.title('Redução de 676.766 para 23.736 pontos')
plt.axis('scaled')
# Figure 3
plt.figure(3)
plt.scatter(coords_1105[0], coords_1105[1], c=predicted, s=0.1)
plt.colorbar()
lito_ccnd.plot(column='Litologia')
plt.axis('scaled')
plt.title("Valores preditos para posições amostradas")
# Figure 4
plt.figure(4)
scale = vd.maxabs(residuals)
lito_ccnd.plot(column='Litologia')
plt.figure(figsize=(10, 10))
plt.scatter(*coords_1105, c=residuals,
            s=0.1, cmap="RdBu_r", vmin=-scale, vmax=scale)
plt.colorbar()
plt.title("Diferença entre valores amostrados e preditos.")
plt.axis('scaled')
# Figure 5 --- Plot grid
grid = spline.grid(spacing=500, data_names=['eU'])
plt.figure(5)
grid.eU.plot()
plt.axis('scaled')
plt.title("Predito para o grid sintético de 500 m.")
# grid.to_netcdf('~/graphite_git/resources/tif/verde/area14/a14_05k_eU.nc')
# Fugure 6
plt.figure(6)
plt.title('Blocked Train and Test data')
plt.plot(train[0][0], train[0][1], '.b', markersize=2)
plt.plot(test[0][0], test[0][1], '.r', markersize=2)

###############################################################################
