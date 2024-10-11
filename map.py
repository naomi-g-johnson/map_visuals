# -*- coding: utf-8 -*-
"""
Created on Fri Oct 11 15:04:53 2024

@author: NAOJOH
"""

import dash
from dash import dcc, html
import geopandas as gpd
import plotly.express as px
import json
import pandas as pd

# Step 1: Load NSW postcode CSV data and filter for NSW
postcode_file = 'postcodes.csv'
df = pd.read_csv(postcode_file)
df = df[df['State'] == 'NSW'][['Pcode', 'Locality']].reset_index(drop=True)
df.columns = ['postcode', 'suburb']

# Step 2: Load NSW suburb boundary GeoJSON data
nsw_suburbs_file = 'nsw_suburbs.json'
with open(nsw_suburbs_file, 'r') as file:
    nsw_suburbs_data = json.load(file)

suburb_geodf = gpd.GeoDataFrame.from_features(nsw_suburbs_data['features'])[['geometry', 'lc_ply_pid', 'nsw_loca_2']]
suburb_geodf.columns = ['geometry', 'suburb_id', 'suburb']

# Step 3: Load LGA boundary GeoJSON data for Sydney
sydney_lga_file = 'sydney_lgas.json'
with open(sydney_lga_file, 'r') as file:
    sydney_lga_data = json.load(file)

lga_geodf = gpd.GeoDataFrame.from_features(sydney_lga_data['features'])[['geometry', 'LG_PLY_PID', 'NSW_LGA__3']]
lga_geodf.columns = ['geometry', 'lga_id', 'lga']

# Step 4: Merge suburb and postcode data, then perform a spatial join
suburb_geodf = suburb_geodf.merge(df, how='left', on='suburb')
geodf = gpd.sjoin(suburb_geodf, lga_geodf, how="inner", predicate="intersects").drop(columns=['index_right']).reset_index(drop=True)

# Step 4.5: Load customer report data and clean it for the first plot
customer_report_file = 'customer_report_all.csv'
customer_df = pd.read_csv(customer_report_file)

df_unique = customer_df.drop_duplicates(subset='Owner Id', keep='first').reset_index(drop=True)
nsw_df = df_unique[df_unique['State'] == 'NSW'][['P/Code']].reset_index(drop=True)
nsw_df.columns = ['postcode']

postcode_counts_df = nsw_df.groupby('postcode').size().reset_index(name='postcode_count')

# Step 5: Merge geometries with postcode counts for the first map
merged_geodf = geodf.merge(postcode_counts_df, how='left', on='postcode')
merged_geodf['postcode_count'] = merged_geodf['postcode_count'].fillna(0)
merged_geodf['geometry'] = merged_geodf['geometry'].simplify(tolerance=0.001, preserve_topology=True)

# Step 6: Create and configure the first choropleth map
desired_point = {"lat": -33.86, "lon": 151.20}
longitude_shift = 0.7
new_center = {"lat": desired_point["lat"], "lon": desired_point["lon"] - longitude_shift}

fig = px.choropleth_mapbox(
    merged_geodf,
    geojson=merged_geodf.geometry.__geo_interface__,
    locations=merged_geodf.index,
    color="postcode_count",
    hover_name="suburb",
    mapbox_style="white-bg",
    center=new_center,
    zoom=9,
    opacity=0.5,
    labels={'postcode_count': 'Postcode Count'}
)

# Update layout for the first map
fig.update_layout(
    height=800, 
    width=1200,
    margin={"r": 50, "t": 50, "l": 50, "b": 50},
    legend_title_text='Postcode Count',
    hovermode='closest',
    title="Amount of customers in each suburb",
    shapes=[{
        'type': 'rect',
        'xref': 'paper',
        'yref': 'paper',
        'x0': 0,
        'y0': 0,
        'x1': 1,
        'y1': 1,
        'line': {
            'color': 'black',
            'width': 2,
        },
    }]
)
fig.update_geos(fitbounds="locations", visible=False)

########################### Second Map for Franchise Data ###########################

# Clean data for the second plot
valid_franchises = ['BMW', 'KAWASAKI', 'KTM']

def recode_franchise(franchise):
    if pd.isnull(franchise):
        return 'NONE'
    elif franchise.upper() in valid_franchises:
        return franchise.upper()
    else:
        return 'NONE'

postcode_df = customer_df[customer_df['State'] == 'NSW'][['P/Code', 'Franchise']].copy()
postcode_df['Franchise'] = postcode_df['Franchise'].apply(recode_franchise)

grouped = postcode_df.groupby(['P/Code', 'Franchise']).size().reset_index(name='count')
dominant_franchise = grouped.sort_values(['P/Code', 'count'], ascending=[True, False]).drop_duplicates('P/Code')
dominant_franchise = dominant_franchise.rename(columns={'P/Code': 'postcode', 'Franchise': 'franchise', 'count': 'franchise_count'})
dominant_franchise = dominant_franchise.drop(columns=['franchise_count'])

# Merge geometries with franchise data
merged_geodf_franchise = geodf.merge(dominant_franchise, how='left', on='postcode')
merged_geodf_franchise['geometry'] = merged_geodf_franchise['geometry'].simplify(tolerance=0.001, preserve_topology=True)

# Fill NaN values in franchise column with 'NONE'
merged_geodf_franchise['franchise'] = merged_geodf_franchise['franchise'].fillna('NONE')

# Create the second choropleth map
fig2 = px.choropleth_mapbox(
    merged_geodf_franchise,
    geojson=merged_geodf_franchise.geometry.__geo_interface__,
    locations=merged_geodf_franchise.index,
    color="franchise",
    hover_name="suburb",
    mapbox_style="white-bg",
    center=new_center,
    zoom=9,
    opacity=0.5,
    labels={'franchise': 'Franchise'},
    color_discrete_map={
        'BMW': '#0166B1',
        'KAWASAKI': '#6BBF23',
        'KTM': '#FF6600',
        'NONE': 'lightgrey'  # Color for areas with no franchise data
    }
)

# Update layout for the second map
fig2.update_layout(
    height=800,
    width=1200,
    margin={"r": 50, "t": 50, "l": 50, "b": 50},
    legend_title_text='Franchise',
    hovermode='closest',
    title="Most popular franchise in each suburb",
    shapes=[{
        'type': 'rect',
        'xref': 'paper',
        'yref': 'paper',
        'x0': 0,
        'y0': 0,
        'x1': 1,
        'y1': 1,
        'line': {
            'color': 'black',
            'width': 2,
        },
    }]
)
fig2.update_geos(fitbounds="locations", visible=False)

# Step 7: Build the Dash app with both maps
app = dash.Dash(__name__)

app.layout = html.Div([
    html.H1("Geographical Customer Analysis"),
    
    # First map with a thin black border
    html.Div(
        dcc.Graph(figure=fig)
    ),
    
    # Second map with a thin black border
    html.Div(
        dcc.Graph(figure=fig2)
    )
])

# Run the Dash app
if __name__ == '__main__':
    app.run_server(debug=True)
