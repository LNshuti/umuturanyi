import logging
import numpy as np
import folium
from folium.plugins import MarkerCluster
import plotly.express as px
import pandas as pd
import gradio as gr
from voyager import Index, Space

# Logger setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =====================================
# Voyager Nearest Neighbor Search
# =====================================

# Create an empty index for latitude and longitude (2D space)
index = Index(space=Space.Euclidean, num_dimensions=2, max_elements=1000)

# Function to add locations (latitude and longitude) to the index
def add_locations_to_index(df):
    for i, row in df.iterrows():
        location_vector = np.array([row['latitude'], row['longitude']], dtype=np.float32)
        index.add_item(location_vector, id=i)
    logger.info("Added all locations to Voyager index.")

# Function to find nearest neighbors based on latitude and longitude
def find_nearest_neighbors(latitude, longitude, k=3):
    query_vector = np.array([latitude, longitude], dtype=np.float32)
    neighbor_ids, distances = index.query(query_vector, k=k)
    return neighbor_ids, distances

# =====================================
# Load and Process Data
# =====================================

# Load a sample dataset of auto repair businesses with latitude and longitude data
data = {
    'name': ['AutoZone', 'Napa Auto Parts', 'O’Reilly Auto', 'Advance Auto', 'Firestone'],
    'latitude': [35.1495, 36.1627, 35.0456, 35.5197, 36.1745],
    'longitude': [-90.0490, -86.7816, -85.3097, -87.3595, -86.7670],
    'address': ['Memphis, TN', 'Nashville, TN', 'Chattanooga, TN', 'Huntsville, AL', 'Clarksville, TN']
}
df_locations = pd.DataFrame(data)

# Add all locations to the Voyager index for nearest neighbor search
add_locations_to_index(df_locations)

# =====================================
# Population Comparison Plot Function
# =====================================

def plot_population_comparison(df_population_comparison):
    df_melted = df_population_comparison.melt(
        id_vars='County',
        value_vars=['Population_2010', 'Population_2020'],
        var_name='Year',
        value_name='Population'
    )
    fig = px.bar(
        df_melted,
        x='County',
        y='Population',
        color='Year',
        barmode='group',
        title="Tennessee Population Comparison: 2010 vs 2020"
    )
    fig.update_layout(xaxis={'categoryorder': 'total descending'}, template='plotly_white')
    return fig

# =====================================
# Map Creation Function
# =====================================

def create_map(geo_layer="All"):
    m = folium.Map(location=[35.8601, -86.6602], zoom_start=7)
    marker_cluster = MarkerCluster().add_to(m)
    
    # Add markers for each location
    for _, row in df_locations.iterrows():
        folium.Marker(
            location=[row['latitude'], row['longitude']],
            popup=f"{row['name']}<br>{row['address']}",
            icon=folium.Icon(color='blue', icon='info-sign')
        ).add_to(marker_cluster)

    folium.LayerControl().add_to(m)
    return m._repr_html_()

# =====================================
# Nearest Neighbor Search and Map Update
# =====================================

def nearest_auto_shop(latitude, longitude):
    neighbor_ids, distances = find_nearest_neighbors(latitude, longitude)
    nearest_shops = df_locations.iloc[neighbor_ids].copy()
    nearest_shops['distance'] = distances

    # Create a map to show the query location and nearest shops
    m = folium.Map(location=[latitude, longitude], zoom_start=10)
    folium.Marker([latitude, longitude], popup="Your Location", icon=folium.Icon(color='red')).add_to(m)
    
    for _, row in nearest_shops.iterrows():
        folium.Marker(
            location=[row['latitude'], row['longitude']],
            popup=f"{row['name']}<br>{row['address']}<br>Distance: {row['distance']:.2f} units",
            icon=folium.Icon(color='blue', icon='info-sign')
        ).add_to(m)

    return nearest_shops[['name', 'address', 'distance']], m._repr_html_()

# =====================================
# Gradio Dashboard Setup
# =====================================

def launch_dashboard():
    with gr.Blocks() as app:
        gr.Markdown("# 🚗 Tennessee Auto Repair Nearest Neighbor Search Dashboard")
        
        with gr.Tab("Overview"):
            gr.Markdown("## 📊 Population Statistics and Auto Repair Locations")

            # Load population data
            df_population_2010 = pd.DataFrame({
                'County': ['Shelby', 'Davidson', 'Knox'],
                'Population_2010': [927644, 626681, 432226]
            })
            df_population_2020 = pd.DataFrame({
                'County': ['Shelby', 'Davidson', 'Knox'],
                'Population_2020': [929744, 715884, 478971]
            })
            df_population_comparison = pd.merge(df_population_2010, df_population_2020, on='County')

            gr.Plot(plot_population_comparison(df_population_comparison))
            gr.Markdown("### 📍 Interactive Map of Auto Shops")
            map_html = gr.HTML(create_map())

        with gr.Tab("Nearest Auto Shop Search"):
            gr.Markdown("## Find Nearest Auto Shop by Your Location")

            latitude_input = gr.Number(label="Latitude", value=35.1495)
            longitude_input = gr.Number(label="Longitude", value=-90.0490)

            result_table = gr.DataFrame(headers=["Name", "Address", "Distance"])
            map_output = gr.HTML()

            search_button = gr.Button("Find Nearest Auto Shops")
            search_button.click(fn=nearest_auto_shop, inputs=[latitude_input, longitude_input], outputs=[result_table, map_output])

    app.launch()

# =====================================
# Main Execution
# =====================================

if __name__ == "__main__":
    launch_dashboard()
