#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Oct 10 22:33:24 2024

@author: naomijohnson
"""
import dash
from dash import dcc, html
import geopandas as gpd
import plotly.express as px
import json

# Step 1: Load the NSW Postcode and Sydney LGA Boundaries JSON files
nsw_postcode_file = 'nsw_postcode_boundaries.json'
with open(nsw_postcode_file, 'r') as file:
    nsw_postcode_data = json.load(file)
    
sydney_lga_file = 'sydney_lga_boundaries.json'
with open(sydney_lga_file, 'r') as file:
    sydney_lga_data = json.load(file)

# Step 2: Convert the 'features' list from both JSON files into GeoDataFrames
nsw_postcode_gdf = gpd.GeoDataFrame.from_features(nsw_postcode_data['features'])
nsw_postcode_gdf['loc_pid'] = nsw_postcode_gdf['loc_pid'].apply(
    lambda x: x[3:] if isinstance(x, str) and x.startswith('NSW') and x[3:].isdigit() else None
)

# Step 3: Clean the Sydney LGA GeoDataFrame
sydney_lga_gdf = gpd.GeoDataFrame.from_features(sydney_lga_data['features'])
lgas_to_remove = ['WOLLONDILLY', 'BLUE MOUNTAINS', 'HAWKESBURY', 'CENTRAL COAST']
sydney_lga_gdf = sydney_lga_gdf[~sydney_lga_gdf['NSW_LGA__3'].isin(lgas_to_remove)].reset_index(drop=True)

# Step 4: Perform a spatial join to find postcodes that intersect with Sydney LGAs
postcode_lga_gdf = gpd.sjoin(nsw_postcode_gdf, sydney_lga_gdf, how="inner", predicate="intersects")

# Step 5: Filter postcodes that are within St Peters LGAs
stpeters_lgas = [
    'CANTERBURY-BANKSTOWN', 'BAYSIDE', 'RANDWICK', 'INNER WEST',
    'SYDNEY', 'WOOLLAHRA', 'WAVERLEY', 'CANADA BAY',
    'BURWOOD', 'STRATHFIELD'
]
stpeters_postcodes_gdf = postcode_lga_gdf[postcode_lga_gdf['NSW_LGA__3'].isin(stpeters_lgas)]
stpeters_postcodes = stpeters_postcodes_gdf['nsw_loca_2'].unique().tolist()

# Step 6: Define Hornsby LGAs correctly as strings
hornsby_lgas = [
    'RYDE', 'PARRAMATTA', 'LANE COVE', 'HUNTERS HILL',
    'NORTH SYDNEY', 'MOSMAN MUNICIPAL COUNCIL',
    'NORTHERN BEACHES', 'KU-RING-GAI', 'HORNSBY',
    'THE HILLS SHIRE'
]

# Step 7: Filter postcodes that are within Hornsby LGAs
hornsby_postcodes_gdf = postcode_lga_gdf[postcode_lga_gdf['NSW_LGA__3'].isin(hornsby_lgas)]
hornsby_postcodes = hornsby_postcodes_gdf['nsw_loca_2'].unique().tolist()

# Step 8: List of postcodes to remove
postcodes_to_remove = ['BLUE MOUNTAINS NATIONAL PARK']
postcode_lga_gdf = postcode_lga_gdf[~postcode_lga_gdf['nsw_loca_2'].isin(postcodes_to_remove)].reset_index(drop=True)

# Step 9: Assign colors based on whether the postcode is in St Peters or Hornsby
def assign_color(postcode):
    if postcode in stpeters_postcodes:
        return 'St Peters'
    elif postcode in hornsby_postcodes:
        return 'Hornsby'
    else:
        return 'Other'

postcode_lga_gdf['color'] = postcode_lga_gdf['nsw_loca_2'].apply(assign_color)

# Step 10: Create the choropleth map for postcodes
postcode_geojson = json.loads(postcode_lga_gdf.to_json())

# Define a color mapping
color_mapping = {
    'St Peters': 'red',
    'Hornsby': 'blue',
    'Other': 'rgba(0,0,0,0)'  # Transparent
}

# Map the color column to the actual colors
postcode_lga_gdf['color_code'] = postcode_lga_gdf['color'].map(color_mapping)

# Create a new column for the color in the GeoJSON properties
for feature in postcode_geojson['features']:
    postcode = feature['properties']['nsw_loca_2']
    if postcode in stpeters_postcodes:
        feature['properties']['color'] = 'red'
    elif postcode in hornsby_postcodes:
        feature['properties']['color'] = 'blue'
    else:
        feature['properties']['color'] = 'rgba(0,0,0,0)'

# Create the choropleth_mapbox with customized hover information
fig = px.choropleth_mapbox(
    postcode_lga_gdf,
    geojson=postcode_geojson,
    locations='nsw_loca_2',  # Use the postcode identifier
    color='color',  # Use the categorical color column
    featureidkey='properties.nsw_loca_2',
    mapbox_style="carto-positron",  # Use a free Mapbox style
    zoom=10,  # Fixed zoom level
    center={"lat": -33.8688, "lon": 151.2093},  # Fixed center on Sydney
    opacity=0.4,  # Reduced opacity for better visibility of base map
    color_discrete_map=color_mapping,
)

fig.update_traces(hovertemplate='%{customdata[0]}<extra></extra>')
fig.update_traces(customdata=postcode_lga_gdf[['nsw_loca_2']])

# Step 11: Update the layout to remove the color gradient bar and maintain fixed zoom and center
fig.update_layout(
    margin={"r":100, "t":50, "l":60, "b":60},
    coloraxis_showscale=False  # Removes the color gradient bar on the right
)

# Step 12: Build the Dash app
app = dash.Dash(__name__)

# Define the layout of the app
app.layout = html.Div(style={'height': '100vh', 'width': '100vw'}, children=[
    html.H1("Procycles St Peters vs Procycles Hornsby Sales Regions", style={'textAlign': 'center'}),
    dcc.Graph(
        figure=fig,
        style={'height': '90vh', 'width': '100vw'}
    )
])

# Run the Dash app
if __name__ == '__main__':
    app.run_server(debug=True)



