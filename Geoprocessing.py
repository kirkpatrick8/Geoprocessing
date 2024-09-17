import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import folium_static
from folium.plugins import Draw
from shapely.geometry import Point, LineString, Polygon, shape
import json
import tempfile
import os
import zipfile
import shutil

def main():
    st.title("GeoSpatial File Viewer and Editor")
    
    st.markdown("""
    ## Introduction
    This Streamlit application allows you to view, edit, and convert shapefiles and GeoJSON files. 
    You can upload your files, view them on an interactive map, add new geometries by drawing on the map, 
    and convert between shapefile and GeoJSON formats.
    
    ### Features:
    - Upload and view shapefiles or GeoJSON files
    - Display geometries on an interactive map
    - Draw new points, lines, or polygons directly on the map
    - Convert between shapefile and GeoJSON formats
    - Download the modified or converted files
    
    Get started by uploading a file using the file uploader below!
    """)
    
    uploaded_file = st.file_uploader("Choose a shapefile (.zip) or GeoJSON file", type=["zip", "geojson"])
    
    if uploaded_file is not None:
        # Load and display the file
        gdf = load_geodata(uploaded_file)
        if gdf is not None:
            gdf = display_map_with_draw(gdf)
            
            # Convert and download
            convert_and_download(gdf)
    
    st.markdown("---")
    st.markdown("Made by [mark.kirkpatrick@aecom.com](mailto:mark.kirkpatrick@aecom.com)")

def load_geodata(file):
    file_extension = file.name.split(".")[-1].lower()
    
    if file_extension == "zip":
        # For zipped shapefiles
        with tempfile.TemporaryDirectory() as tmpdir:
            with zipfile.ZipFile(file, 'r') as zip_ref:
                zip_ref.extractall(tmpdir)
            # Find the .shp file in the extracted contents
            shp_files = [f for f in os.listdir(tmpdir) if f.endswith('.shp')]
            if not shp_files:
                st.error("No .shp file found in the uploaded zip.")
                return None
            shp_path = os.path.join(tmpdir, shp_files[0])
            gdf = gpd.read_file(shp_path)
    elif file_extension == "geojson":
        # For GeoJSON, we can read directly from the uploaded file
        gdf = gpd.read_file(file)
    else:
        st.error("Unsupported file format. Please upload a zipped shapefile or GeoJSON file.")
        return None
    
    # Set CRS to EPSG:4326 (WGS84) if it's not already set
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4326")
    else:
        gdf = gdf.to_crs("EPSG:4326")
    
    return gdf

def display_map_with_draw(gdf):
    st.subheader("Map View")
    
    # Calculate the center of the map
    center_lat = gdf.geometry.centroid.y.mean()
    center_lon = gdf.geometry.centroid.x.mean()
    
    # Create a map centered on the data
    m = folium.Map(location=[center_lat, center_lon], zoom_start=10)
    
    # Add the GeoDataFrame to the map
    folium.GeoJson(
        gdf.__geo_interface__,
        style_function=lambda feature: {
            'fillColor': 'blue',
            'color': 'black',
            'weight': 2,
            'fillOpacity': 0.7,
        }
    ).add_to(m)
    
    # Add draw control
    draw = Draw(
        draw_options={
            'polyline': True,
            'rectangle': True,
            'polygon': True,
            'circle': False,
            'marker': True,
            'circlemarker': False
        },
        edit_options={'edit': False}
    )
    draw.add_to(m)
    
    # Fit the map to the bounds of the data
    m.fit_bounds(m.get_bounds())
    
    # Display the map
    map_data = folium_static(m)
    
    # Check for new geometries
    if map_data:
        new_features = map_data.get('all_drawings', [])
        if new_features:
            for feature in new_features:
                geom = shape(feature['geometry'])
                new_row = gpd.GeoDataFrame({'geometry': [geom]}, crs="EPSG:4326")
                gdf = gdf.append(new_row, ignore_index=True)
            st.success(f"Added {len(new_features)} new geometries to the data.")
            # Redisplay the map with new geometries
            display_map_with_draw(gdf)
    
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
