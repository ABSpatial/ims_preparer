import tempfile

import geopandas as gpd
import pendulum
import rasterio
import requests
from rasterio.enums import Resampling
from rasterio.features import rasterize
from rasterio.mask import mask
from rasterio.warp import calculate_default_transform, reproject
from tqdm import tqdm


def prepare(input_layer_path, input_layername, raster_date, output_crs, type_codes, output_layer_path):
    if not input_layer_path:
        raise ValueError('There must be at least source layer.')
    if input_layer_path:
        if not input_layername:
            raise ValueError('There must be a source layer name.')
    raster_date = pendulum.parse(raster_date, strict=False)
    now_date = pendulum.now()
    if raster_date >= now_date:
        raise ValueError('The raster date must be yesterday or earlier.')

    raster_date_day, raster_date_month, raster_date_year = raster_date.day, raster_date.month, raster_date.year
    raster_prd_uri = f"https://usicecenter.gov/File/DownloadArchive?prd=66{str(raster_date_month).zfill(2)}{str(raster_date_day).zfill(2)}{raster_date_year}"
    raster_response = requests.get(raster_prd_uri, stream=True)
    total_size = int(raster_response.headers.get('content-length', 0))
    with tqdm(total=total_size, unit='MB', unit_scale=True, unit_divisor=1024, desc='Downloading IMS raster') as pbar:
        with tempfile.NamedTemporaryFile(mode='wb', delete=False) as temp_file:
            for data in raster_response.iter_content(chunk_size=1024):
                temp_file.write(data)
                pbar.update(len(data))

    with rasterio.open(f'/vsigzip/{temp_file.name}', mode='r') as src:
        mask_data = gpd.read_file(input_layer_path, layername=input_layername)
        mask_data = mask_data.to_crs(src.crs.data)
        geoms = mask_data.geometry.values
        geometry = [geom.__geo_interface__ for geom in geoms]
        out_image, out_transform = mask(src, geometry, crop=True)
        out_meta = src.meta.copy()
        out_meta.update({
            "driver": "GTiff",
            "height": out_image.shape[1],
            "width": out_image.shape[2],
            "transform": out_transform
        })
        out_temp = tempfile.NamedTemporaryFile(mode='w', delete=False)
        with rasterio.open(out_temp.name, "w", **out_meta) as dest:
            dest.write(out_image)
        with rasterio.open(out_temp.name) as src:
            transform, width, height = calculate_default_transform(
                src.crs, output_crs, src.width, src.height, *src.bounds)
            kwargs = src.meta.copy()
            kwargs.update({
                'crs': output_crs,
                'transform': transform,
                'width': width,
                'height': height
            })
            out_temp_reprojected = tempfile.NamedTemporaryFile(mode='w', delete=False)
            with rasterio.open(out_temp_reprojected.name, 'w', **kwargs) as dst:
                for i in range(1, src.count + 1):
                    reproject(
                        source=rasterio.band(src, i),
                        destination=rasterio.band(dst, i),
                        src_transform=src.transform,
                        src_crs=src.crs,
                        dst_transform=transform,
                        dst_crs=output_crs,
                        resampling=Resampling.nearest)
        with rasterio.open(out_temp_reprojected.name) as src:
            image = src.read(1)
            transform = src.transform
        results = (
            {'properties': {'TYPE_CODE': v if v not in type_codes else type_codes[v], "TYPE": v, 'DATE': raster_date}, 'geometry': s}
            for i, (s, v) in enumerate(
            rasterio.features.shapes(
                image, transform=transform)) if v > 0)
        gdf = gpd.GeoDataFrame.from_features(list(results))
        gdf.crs = src.crs

        type_code_values = list(type_codes.values())
        extracted_gdf = gdf[gdf['TYPE_CODE'].isin(type_code_values)].dissolve(by='TYPE_CODE')
        extracted_gdf.to_file(output_layer_path)

        out_temp_reprojected.close()


