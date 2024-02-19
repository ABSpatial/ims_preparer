import pendulum

from ims.preparer import prepare

input_layer = "/ims/ims/preparer/central_asia_boundary.gpkg"
layer_name = "central_asia_boundary"
raster_date = pendulum.now("UTC").subtract(days=1).format("YYYY-MM-DD")
output_crs = "EPSG:3857"
type_codes = {
    3: "Ice",
    4: "Snow"
}
output_path = f"/tmp/{raster_date}.gpkg"
NGW_LAYER_URL = "https://gis.abspatial.com/resource/1052"
NGW_LAYER_NAME = "IMS_vector_multipolygon"
login="user" # сделать хранение более безопасным
password="password" # сделать хранение более безопасным


prepare(input_layer, layer_name, raster_date, output_crs, type_codes, output_path)

cmd = [
    "ogr2ogr",
    "-f", "NGW",
    "-nln", NGW_LAYER_NAME,
    "-append",
    "-doo", f"USERPWD={login}:{password}",
    "-doo", "BATCH_SIZE=100",  # вообще не понял этот параметр
    "-t_srs", "EPSG:3857",
    f"NGW:{NGW_LAYER_URL}",
    output_path
#    tempfile_ims_preparer_out
#    mem_ims
]

subprocess.run(cmd, check=True)

os.remove(output_path)
