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
import pandas as pd

def main():
    st.title("GeoSpatial File Viewer and Editor")
    
    st.markdown("""
    ## Introduction
    This Streamlit application allows you to view, edit, and convert shapefiles and GeoJSON files. 
    You can upload your files, view them on an interactive map, add new geometries by drawing on the map, 
    commit your changes, and download the edited file.
    
    ### Features:
    - Upload and view shapefiles or GeoJSON files
    - Display geometries on an interactive map
    - Draw new points, lines, or polygons directly on the map
    - Commit changes made to the data
    - Download the edited file
    - Convert between shapefile and GeoJSON formats
    
    Get started by uploading a file using the file uploader below!
    """)
    
    uploaded_file = st.file_uploader("Choose a shapefile (.zip) or GeoJSON file", type=["zip", "geojson"])
    
    if 'gdf' not in st.session_state:
        st.session_state.gdf = None
    if 'new_features' not in st.session_state:
        st.session_state.new_features = []

    if uploaded_file is not None:
        try:
            # Load and display the file
            st.session_state.gdf = load_geodata(uploaded_file)
            if st.session_state.gdf is not None:
                st.session_state.gdf, st.session_state.new_features = display_map_with_draw(st.session_state.gdf)
                
                # Commit Changes button
                if st.button("Commit Changes"):
                    if st.session_state.new_features:
                        st.session_state.gdf = commit_changes(st.session_state.gdf, st.session_state.new_features)
                        st.success("Changes committed successfully!")
                        st.session_state.new_features = []  # Clear new features after committing
                    else:
                        st.warning("No changes to commit. Draw some geometries on the map first.")

                # Download Edited File button
                if st.session_state.gdf is not None:
                    download_edited_file(st.session_state.gdf)
                
                # Convert and download
                convert_and_download(st.session_state.gdf)
        except Exception as e:
            st.error(f"An error occurred while processing the file: {str(e)}")
            st.error("Please try uploading the file again or contact support if the issue persists.")
    
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
    
    try:
        # Project to a suitable CRS for centroid calculation
        gdf_projected = gdf.to_crs(epsg=3857)  # Web Mercator projection
        
        # Calculate the center of the map
        center_lat = gdf_projected.geometry.centroid.y.mean()
        center_lon = gdf_projected.geometry.centroid.x.mean()
        
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
        st.write("Displaying map...")
        folium_static(m)
        
        # For now, we'll use a placeholder for new features
        # In a production app, you'd need to implement a way to capture drawn features
        new_features = []
        st.info("Drawing features is currently not fully implemented. This is a placeholder for future functionality.")
        
    except Exception as e:
        st.error(f"An error occurred while displaying the map: {str(e)}")
        st.error("Please try refreshing the page or contact support if the issue persists.")
    
    return gdf, new_features

# The rest of the functions (commit_changes, download_edited_file, convert_and_download) remain the same

if __name__ == "__main__":
    main()
