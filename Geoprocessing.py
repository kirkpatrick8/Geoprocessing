import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import folium_static
from shapely.geometry import Point, LineString, Polygon
import json
import tempfile
import os

def main():
    st.title("GeoSpatial File Viewer and Converter")
    
    st.markdown("""
    ## Introduction
    This Streamlit application allows you to view, edit, and convert shapefiles and GeoJSON files. 
    You can upload your files, view them on an interactive map, add new geometries, and convert between 
    shapefile and GeoJSON formats.
    
    ### Features:
    - Upload and view shapefiles or GeoJSON files
    - Display geometries on an interactive map
    - Add new points, lines, or polygons
    - Convert between shapefile and GeoJSON formats
    - Download the modified or converted files
    
    Get started by uploading a file using the file uploader below!
    """)
    
    uploaded_file = st.file_uploader("Choose a shapefile or GeoJSON file", type=["shp", "geojson"])
    
    if uploaded_file is not None:
        # Load and display the file
        gdf = load_geodata(uploaded_file)
        if gdf is not None:
            display_map(gdf)
            
            # Add geometry
            gdf = add_geometry(gdf)
            
            # Convert and download
            convert_and_download(gdf)
    
    st.markdown("---")
    st.markdown("Made by [mark.kirkpatrick@aecom.com](mailto:mark.kirkpatrick@aecom.com)")

def load_geodata(file):
    file_extension = file.name.split(".")[-1].lower()
    
    if file_extension == "shp":
        # For shapefiles, we need to handle multiple files
        with tempfile.TemporaryDirectory() as tmpdir:
            # Save the uploaded shapefile
            file_path = os.path.join(tmpdir, file.name)
            with open(file_path, "wb") as f:
                f.write(file.getbuffer())
            
            # Check for other required files (.dbf, .shx)
            required_extensions = ['.dbf', '.shx']
            for ext in required_extensions:
                required_file = st.file_uploader(f"Upload the {ext} file", type=[ext[1:]])
                if required_file is None:
                    st.error(f"Please upload the {ext} file associated with your shapefile.")
                    return None
                with open(os.path.join(tmpdir, file.name.replace('.shp', ext)), "wb") as f:
                    f.write(required_file.getbuffer())
            
            # Read the shapefile
            gdf = gpd.read_file(file_path)
    elif file_extension == "geojson":
        # For GeoJSON, we can read directly from the uploaded file
        gdf = gpd.read_file(file)
    else:
        st.error("Unsupported file format. Please upload a shapefile or GeoJSON file.")
        return None
    
    return gdf

def display_map(gdf):
    st.subheader("Map View")
    m = folium.Map(location=[gdf.geometry.centroid.y.mean(), gdf.geometry.centroid.x.mean()], zoom_start=10)
    folium.GeoJson(gdf).add_to(m)
    folium_static(m)

def add_geometry(gdf):
    st.subheader("Add Geometry")
    geometry_type = st.selectbox("Select geometry type to add", ["Point", "LineString", "Polygon"])
    
    if geometry_type == "Point":
        lat = st.number_input("Latitude", value=0.0)
        lon = st.number_input("Longitude", value=0.0)
        new_geometry = Point(lon, lat)
    elif geometry_type == "LineString":
        coords = st.text_area("Enter coordinates (lon,lat) separated by semicolons", "0,0; 1,1; 2,2")
        coord_list = [tuple(map(float, coord.split(","))) for coord in coords.split(";")]
        new_geometry = LineString(coord_list)
    elif geometry_type == "Polygon":
        coords = st.text_area("Enter coordinates (lon,lat) separated by semicolons", "0,0; 0,1; 1,1; 1,0; 0,0")
        coord_list = [tuple(map(float, coord.split(","))) for coord in coords.split(";")]
        new_geometry = Polygon(coord_list)
    
    if st.button("Add Geometry"):
        new_row = gpd.GeoDataFrame({"geometry": [new_geometry]}, crs=gdf.crs)
        gdf = gdf.append(new_row, ignore_index=True)
        st.success("Geometry added successfully!")
        display_map(gdf)
    
    return gdf

def convert_and_download(gdf):
    st.subheader("Convert and Download")
    output_format = st.selectbox("Select output format", ["GeoJSON", "Shapefile"])
    
    if output_format == "GeoJSON":
        output = gdf.to_json()
        filename = "converted.geojson"
        mime_type = "application/json"
    else:  # Shapefile
        # For shapefile, we need to create a zip file containing all components
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_shp = os.path.join(tmpdir, "converted.shp")
            gdf.to_file(tmp_shp, driver="ESRI Shapefile")
            # Create a zip file containing all shapefile components
            import shutil
            shp_zip = shutil.make_archive(os.path.join(tmpdir, "converted_shapefile"), 'zip', tmpdir)
            with open(shp_zip, "rb") as f:
                output = f.read()
        filename = "converted_shapefile.zip"
        mime_type = "application/zip"
    
    st.download_button(
        label="Download converted file",
        data=output,
        file_name=filename,
        mime=mime_type
    )

if __name__ == "__main__":
    main()
