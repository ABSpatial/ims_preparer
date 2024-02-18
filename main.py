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

prepare(input_layer, layer_name, raster_date, output_crs, type_codes, output_path)