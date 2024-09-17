import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import folium_static
from folium.plugins import Draw
from shapely.geometry import shape
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

    if uploaded_file is not None:
        try:
            # Load and display the file
            st.session_state.gdf = load_geodata(uploaded_file)
            if st.session_state.gdf is not None:
                display_map_with_draw(st.session_state.gdf)
                
                # Commit Changes button
                if st.button("Commit Changes"):
                    drawn_features = st.session_state.get('drawn_features', None)
                    if drawn_features:
                        st.session_state.gdf = commit_changes(st.session_state.gdf, drawn_features)
                        st.success("Changes committed successfully!")
                        st.session_state['drawn_features'] = None  # Clear drawn features after committing
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

        # Add custom JavaScript to capture drawn features
        m.get_root().html.add_child(folium.Element("""
        <script>
        var drawnItems = new L.FeatureGroup();
        map.addLayer(drawnItems);

        map.on(L.Draw.Event.CREATED, function (event) {
            var layer = event.layer;
            drawnItems.addLayer(layer);
            document.getElementById('drawn_data').value = JSON.stringify(drawnItems.toGeoJSON());
        });

        map.on('draw:edited', function (event) {
            var layers = event.layers;
            layers.eachLayer(function (layer) {
                drawnItems.addLayer(layer);
            });
            document.getElementById('drawn_data').value = JSON.stringify(drawnItems.toGeoJSON());
        });

        map.on('draw:deleted', function (event) {
            var layers = event.layers;
            layers.eachLayer(function (layer) {
                drawnItems.removeLayer(layer);
            });
            document.getElementById('drawn_data').value = JSON.stringify(drawnItems.toGeoJSON());
        });
        </script>
        """))

        # Add a hidden input to store drawn features
        m.get_root().html.add_child(folium.Element(
            '<input type="hidden" id="drawn_data" value="{}">'
        ))

        # Fit the map to the bounds of the data
        m.fit_bounds(m.get_bounds())
        
        # Display the map
        st.write("Displaying map...")
        folium_static(m)
        
        # Retrieve drawn features
        drawn_data = st.components.v1.html(
            """
            <script>
            var drawnDataElement = document.getElementById('drawn_data');
            if (drawnDataElement) {
                var drawnData = drawnDataElement.value;
                if (drawnData) {
                    window.parent.postMessage({type: "drawn_data", data: drawnData}, "*");
                }
            }
            </script>
            """,
            height=0,
        )
        
        # Store drawn features in session state
        if drawn_data:
            st.session_state['drawn_features'] = json.loads(drawn_data)
        
    except Exception as e:
        st.error(f"An error occurred while displaying the map: {str(e)}")
        st.error("Please try refreshing the page or contact support if the issue persists.")

def commit_changes(gdf, drawn_features):
    if drawn_features and 'features' in drawn_features:
        new_features = drawn_features['features']
        st.write(f"Committing {len(new_features)} new features.")
        for feature in new_features:
            try:
                geom = shape(feature['geometry'])
                new_row = gpd.GeoDataFrame({'geometry': [geom]}, crs="EPSG:4326")
                gdf = gpd.GeoDataFrame(pd.concat([gdf, new_row], ignore_index=True), crs=gdf.crs)
                st.success(f"Added new {geom.geom_type}")
            except Exception as e:
                st.error(f"Error adding feature: {str(e)}")
        st.write(f"GeoDataFrame now has {len(gdf)} features.")
    else:
        st.warning("No new features to commit.")
    return gdf

def download_edited_file(gdf):
    st.subheader("Download Edited File")
    file_format = st.selectbox("Select file format for download", ["GeoJSON", "Shapefile"])
    
    try:
        if file_format == "GeoJSON":
            output = gdf.to_json()
            filename = "edited_file.geojson"
        else:  # Shapefile
            with tempfile.TemporaryDirectory() as tmpdir:
                tmp_shp = os.path.join(tmpdir, "edited_file.shp")
                gdf.to_file(tmp_shp, driver="ESRI Shapefile")
                shp_zip = shutil.make_archive(os.path.join(tmpdir, "edited_file_shapefile"), 'zip', tmpdir)
                with open(shp_zip, "rb") as f:
                    output = f.read()
            filename = "edited_file_shapefile.zip"
        
        st.download_button(
            label="Download Edited File",
            data=output,
            file_name=filename
        )
    except Exception as e:
        st.error(f"An error occurred while preparing the file for download: {str(e)}")
        st.error("Please try again or contact support if the issue persists.")

def convert_and_download(gdf):
    st.subheader("Convert and Download")
    output_format = st.selectbox("Select output format for conversion", ["GeoJSON", "Shapefile"])
    
    try:
        if output_format == "GeoJSON":
            output = gdf.to_json()
            filename = "converted.geojson"
        else:  # Shapefile
            with tempfile.TemporaryDirectory() as tmpdir:
                tmp_shp = os.path.join(tmpdir, "converted.shp")
                gdf.to_file(tmp_shp, driver="ESRI Shapefile")
                shp_zip = shutil.make_archive(os.path.join(tmpdir, "converted_shapefile"), 'zip', tmpdir)
                with open(shp_zip, "rb") as f:
                    output = f.read()
            filename = "converted_shapefile.zip"
        
        st.download_button(
            label="Download Converted File",
            data=output,
            file_name=filename
        )
    except Exception as e:
        st.error(f"An error occurred while converting the file: {str(e)}")
        st.error("Please try again or contact support if the issue persists.")

if __name__ == "__main__":
    main()
