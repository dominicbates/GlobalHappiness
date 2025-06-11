import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import geopandas as gpd
from matplotlib.colors import LinearSegmentedColormap
import json

# ---- Load your data at the beginning ----
@st.cache_data
def load_data():
    # Replace this with your actual CSV file path
    # df = pd.read_csv("data/combined_v0.1/stats.csv")
    df = pd.read_csv("data/stats_v0.1.csv")
    return df
df = load_data()

# Load regions
with open("regions.json") as f:
    regions = json.load(f)
    
# Load mapping
mapping = {'Gambia':'The Gambia',
           'Russia':'Russian Federation',
           'North Korea':'Dem. Rep. Korea',
           'South Korea':'Republic of Korea',
           'Ivory Coast':"Côte d'Ivoire",
           'Eswatini':'Kingdom of eSwatini',
           'Laos':'Lao PDR', 
           'Brunei':'Brunei Darussalam',
           'Czechia':'Czech Republic'}



# ---- App Title and Description ----
st.title("Global Happiness Over Time")
st.markdown("""
This app lets you explore global happiness as a function of time. Happiness is calculated in several categories, and then averaged to compute "overall" happiness. Values have been estimated by an expert historian (role-played by gpt-4.5-mini) for each region and time. The model was sampled from ~20 times and averaged to compute mean values and confidence intervals. It was prompted to include explanations, so values should encorporate historical context (at least as much as the LLM understands these factors). I may add these at a later date. 
""")

# ---- Economic Category Selection ----
metrics_list = df['metric'].unique()  # or a static list like ['GDP', 'Population', ...]
selected_metric = st.selectbox("Select Happiness Metric", metrics_list)

# ---- Layout Split: Left | Right ----
left_col, right_col = st.columns(2)

# ---- Left Panel ----
with left_col:

    st.write(f"#### Global: {selected_metric.replace('Subset: ','')}")

    selected_year = st.slider(
        "Select Year",
        min_value=-1000,
        max_value=2000,
        step=100,
        value=0
    )
    st.markdown("<div style='margin-bottom: 20px;'></div>",
                unsafe_allow_html=True)


    # ----------
    m_geo_plot = (df['dates_start'] == selected_year) & (df['metric'] == selected_metric)
    countries = []
    country_values = []
    
    # Create lists of countries and values
    for n in range(m_geo_plot.sum()):
        r = df[m_geo_plot]['region'].iloc[n]
        for m in range(len(regions)):
            if regions[m]['region'] == r:
                countries += regions[m]['countries']
                country_values += [df[m_geo_plot]['mean'].iloc[n]]*len(regions[m]['countries'])
                if 'Canada' in regions[m]['countries']:
                    countries += ['Greenland']
                    country_values += [df[m_geo_plot]['mean'].iloc[n]]
    countries = [mapping.get(c, c) for c in countries]

    # Your input data
    data = pd.DataFrame({'name': countries, 'value': country_values})
    # Load shapefile manually from downloaded path
    # shapefile_path = '/Users/dominicbates/Documents/Github/GlobalHappiness/data/maps/ne_110m_admin_0_countries/ne_110m_admin_0_countries.shp'
    shapefile_path = 'data/maps/ne_110m_admin_0_countries/ne_110m_admin_0_countries.shp'

    world = gpd.read_file(shapefile_path)
    world = world.merge(data, left_on='NAME_LONG', right_on='name', how='left')
    # Create custom red-yellow-green colormap
    cmap = LinearSegmentedColormap.from_list('custom_red_yellow_green', ['red', 'yellow', 'green'])
    
    # Plot
    fig, ax = plt.subplots(figsize=(4.5,3))   
    # ax = fig.add_subplot(1, 1, 1)
    world.plot(column='value', cmap=cmap, linewidth=0.3, edgecolor='black',
               missing_kwds={"color": "lightgrey"}, ax=ax, 
               vmin = df['mean'][df['metric'] == selected_metric].min(),
               vmax = df['mean'][df['metric'] == selected_metric].max())
    ax.set_xlim(-170, 180)
    ax.set_ylim(-58, 85) 
    ax.set_title(f"Year: {selected_year}")
    ax.set_axis_off()
    st.pyplot(fig)
    


    
# ---- Right Panel ----
with right_col:
    st.write(f"#### Time Series")
    region_list = df['region'].unique()  # or a custom sorted list
    selected_region = st.selectbox("Select Country", region_list)
    st.markdown("<div style='margin-bottom: 31px;'></div>",
                unsafe_allow_html=True)
    
        
    # Placeholder for country plot
    fig2, ax2 = plt.subplots(figsize=(4.5,2.2))
    ax2.set_title(f"{selected_region}")
    
    m_time_series = (df['region'] == selected_region) & (df['metric'] == selected_metric)
    plt.plot(df[m_time_series]['dates_start'], df[m_time_series]['mean'], color='C0')
    plt.fill_between(df[m_time_series]['dates_start'], 
                     df[m_time_series]['err_neg'],
                     df[m_time_series]['err_pos'], color='C0',alpha=0.3)
    plt.fill_between([selected_year, selected_year+50],
                     df[m_time_series]['err_neg'].min(), 
                     df[m_time_series]['err_pos'].max(),
                     alpha=0.1, color='k')
    plt.xlabel('Year')
    plt.ylabel(f'{selected_metric.replace('Subset: ','')}')
    st.pyplot(fig2)
