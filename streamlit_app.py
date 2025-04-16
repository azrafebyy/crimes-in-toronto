# Import library
import streamlit as st
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.colors as mcolors
import folium
from folium.features import GeoJsonTooltip
import plotly.graph_objs as go
import altair as alt
import plotly.express as px
import gdown
import os

# Page configuration
st.set_page_config(
    page_title="Crimes in Toronto Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded")

alt.themes.enable("dark")

# Cek apakah file sudah ada
if not os.path.exists("major-crime-indicators.csv"):
    file_id = "1Yda-fY9I60L_dAUha5Fk31iUC-sB_GGz"
    url = f"https://drive.google.com/uc?id={file_id}"
    gdown.download(url, "major-crime-indicators.csv", quiet=False)
# Load data
df_crime = pd.read_csv("major-crime-indicators.csv")
geo_df = gpd.read_file('toronto_neighborhoods140.geojson')

# Preprocessing
# Hapus baris yang memiliki nilai kosong
df_crime = df_crime.dropna()

# Hapus baris yang mengandung kode 'NSA' pada kolom terkait
df_crime = df_crime[
    (df_crime['HOOD_158'] != 'NSA') &
    (df_crime['NEIGHBOURHOOD_158'] != 'NSA') &
    (df_crime['HOOD_140'] != 'NSA') &
    (df_crime['NEIGHBOURHOOD_140'] != 'NSA')
]

# Hapus duplikasi
df_crime = df_crime.drop_duplicates()

# Plots
def bubble(df):
    category_counts = df['MCI_CATEGORY'].value_counts()
    categories = category_counts.index.tolist()
    counts = category_counts.values.tolist()

    plot_data = pd.DataFrame({
        'Category': categories,
        'Count': counts,
        'Size': [count * 5 for count in counts],
        'X': [i * 0.8 for i in range(len(categories))],
        'Y': [1] * len(categories)
    })

    fig = px.scatter(
        plot_data,
        x='X',
        y='Y',
        size='Size',
        color='Count',
        hover_data={
            'X': False,
            'Y': False,
            'Category': False,
            'Count': False
        },
        custom_data=['Category', 'Count'],
        color_continuous_scale='Reds',
        size_max=180
    )

    fig.update_layout(
        xaxis=dict(
            tickmode='array',
            tickvals=plot_data['X'],
            ticktext=plot_data['Category'],
            showgrid=False,
            tickfont=dict(size=12)
        ),
        yaxis=dict(showticklabels=False),
        xaxis_title='',
        yaxis_title='',
        showlegend=False,
        width=800,
        height=400,
        coloraxis_colorbar=dict(title='Total Crimes')
    )

    fig.update_traces(
        marker=dict(line=dict(width=1, color='grey')),
        hovertemplate="<b>Kategori:</b> %{customdata[0]}<br><b>Jumlah:</b> %{customdata[1]}<extra></extra>",
        mode='markers+text',
    )

    st.plotly_chart(fig, use_container_width=True)

def bar_hor(df):
    premises_counts = df['PREMISES_TYPE'].value_counts()
    types = premises_counts.index.tolist()
    counts = premises_counts.values.tolist()

    n_bars = len(counts)
    cmap = cm.get_cmap('Reds_r', n_bars)
    colors = [mcolors.to_hex(cmap(i)) for i in range(n_bars)]

    bar = go.Bar(
        x=counts,
        y=types,
        orientation='h',
        marker=dict(color=colors),
        hovertemplate='Tempat: <b>%{y}</b><br>Jumlah: %{x}<extra></extra>',
        hoverlabel=dict(
            bgcolor='red',
            font=dict(color='white', size=14)
        )
    )

    layout = go.Layout(
        xaxis=dict(title='Banyaknya Kejadian', color='white'),
        yaxis=dict(title='Jenis Tempat Kejadian', autorange='reversed', color='white'),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )

    fig = go.Figure(data=[bar], layout=layout)
    fig.update_layout(width=800, height=400)
    st.plotly_chart(fig, use_container_width=True)

def pie_ch(df):
    year_counts_raw = df['OCC_YEAR'].value_counts()
    year_counts_sorted = year_counts_raw.sort_index()

    total = year_counts_sorted.sum()
    percentages = year_counts_sorted / total

    # Gabungkan tahun <1% ke kategori "Others"
    mask_major = percentages >= 0.01
    major_years = year_counts_sorted[mask_major]
    minor_years = year_counts_sorted[~mask_major]

    if not minor_years.empty:
        major_years['Others'] = minor_years.sum()

    year_counts = major_years
    percentages = year_counts / year_counts.sum()

    # Ranking untuk pewarnaan
    ranking = year_counts.rank(method='min', ascending=False).to_dict()
    num_years = len(year_counts)
    step = (1.0 - 0.05) / (num_years - 1) if num_years > 1 else 0
    rank_to_color_value = {
        rank: 1.0 - ((rank - 1) * step)
        for rank in range(1, num_years + 1)
    }

    # Konversi ke hex color
    colors = [mcolors.to_hex(cm.Reds(rank_to_color_value[ranking[year]])) for year in year_counts.index]

    pie = go.Pie(
        labels=year_counts.index.astype(str),
        values=year_counts.values,
        marker=dict(colors=colors, line=dict(color='white', width=1)),
        hovertemplate='<b>Tahun %{label}</b><br>Jumlah: %{value} (%{percent})<extra></extra>',
        hoverlabel=dict(
            bgcolor='red',
            font=dict(color='white', size=14)
        ),
        sort=False,
        direction='clockwise',
        textinfo='percent'
    )

    fig = go.Figure(data=[pie])
    st.plotly_chart(fig, use_container_width=True)

def line_ch(df_crime):
    day_counts = df_crime['OCC_DAY'].value_counts().sort_index()

    fig = go.Figure(data=go.Scatter(
        x=day_counts.index,
        y=day_counts.values,
        mode='lines+markers',
        marker=dict(color='red'),
        line=dict(color='red'),
        hovertemplate='Tanggal: %{x}<br>Banyaknya Kejadian Kriminal: %{y}<extra></extra>'
    ))

    fig.update_layout(
        xaxis_title='Tanggal',
        yaxis_title='Banyaknya Kejadian Kriminal',
        template='plotly_dark',  # agar cocok dengan tema gelap
        width=900,
        height=600,
        font=dict(color='white')  # Semua teks putih
    )

    st.plotly_chart(fig, use_container_width=True)

def line2_ch(df_crime):
    # Mapping nama bulan ke Bahasa Indonesia
    month_translation = {
        'January': 'Januari', 'February': 'Februari', 'March': 'Maret', 'April': 'April',
        'May': 'Mei', 'June': 'Juni', 'July': 'Juli', 'August': 'Agustus',
        'September': 'September', 'October': 'Oktober', 'November': 'November', 'December': 'Desember'
    }
    ordered_months = list(month_translation.values())

    # Terjemahkan bulan
    df_crime['Month_Indo'] = df_crime['OCC_MONTH'].map(month_translation)

    # Hitung jumlah kejadian tiap bulan
    month_counts = df_crime['Month_Indo'].value_counts().reindex(ordered_months, fill_value=0)

    # Buat line chart
    fig = go.Figure(data=go.Scatter(
        x=month_counts.index,
        y=month_counts.values,
        mode='lines+markers',
        marker=dict(color='red'),
        line=dict(color='red'),
        hovertemplate='Bulan: %{x}<br>Banyaknya Kejadian Kriminal: %{y}<extra></extra>'
    ))

    fig.update_layout(
        xaxis_title='Bulan',
        yaxis_title='Banyaknya Kejadian Kriminal',
        template='plotly_dark',  # tema gelap
        width=900,
        height=600,
        font=dict(color='white')  # teks putih
    )

    st.plotly_chart(fig, use_container_width=True)

def line3_ch(df_crime):
    # Bersihkan dan ubah nama hari ke Bahasa Indonesia
    df_crime['OCC_DOW'] = df_crime['OCC_DOW'].str.strip().str.title()
    days_translation = {
        'Monday': 'Senin', 'Tuesday': 'Selasa', 'Wednesday': 'Rabu', 'Thursday': 'Kamis',
        'Friday': 'Jumat', 'Saturday': 'Sabtu', 'Sunday': 'Minggu'
    }
    ordered_days = list(days_translation.values())

    df_crime['Days_Indo'] = df_crime['OCC_DOW'].map(days_translation)

    # Hitung jumlah kejadian per hari
    day_counts = df_crime['Days_Indo'].value_counts().reindex(ordered_days, fill_value=0)

    # Buat grafik line chart
    fig = go.Figure(data=go.Scatter(
        x=day_counts.index,
        y=day_counts.values,
        mode='lines+markers',
        marker=dict(color='red'),
        line=dict(color='red'),
        hovertemplate='Hari: %{x}<br>Banyaknya Kejadian Kriminal: %{y}<extra></extra>'
    ))

    fig.update_layout(
        xaxis_title='Hari',
        yaxis_title='Banyaknya Kejadian Kriminal',
        template='plotly_dark',  # tema gelap
        width=900,
        height=600,
        font=dict(color='white')  # semua teks putih
    )

    st.plotly_chart(fig, use_container_width=True)

def radar_ch(df_crime):
    hour_counts = df_crime['OCC_HOUR'].value_counts().sort_index()

    categories = hour_counts.index.tolist()
    values = hour_counts.values.tolist()

    # Tutup loop untuk radar chart
    categories += [categories[0]]
    values += [values[0]]

    fig = go.Figure()

    fig.add_trace(go.Scatterpolar(
        r=values,
        theta=[str(c) for c in categories],
        mode='lines+markers',
        fill='toself',
        hoverinfo='text',
        text=[f'Jam: {cat}<br>Banyaknya: {val}' for cat, val in zip(categories, values)],
        line=dict(color='red'),
        marker=dict(color='red')
    ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, color='white'),
            angularaxis=dict(rotation=90, direction='clockwise', color='white')
        ),
        showlegend=False,
        font=dict(color='white'),
        template='plotly_dark',
        width=500,
        height=450
    )
    st.plotly_chart(fig, use_container_width=True)

def maps(df, gdf):
    # Hitung jumlah kejahatan per HOOD_140
    count = df.groupby('HOOD_140').size().reset_index(name='count')

    # Gabungkan data dengan geodataframe
    merged = gdf.merge(count, left_on='AREA_SHORT_CODE', right_on='HOOD_140')

    # Buat choropleth mapbox
    fig = px.choropleth_mapbox(
        merged,
        geojson=merged.geometry.__geo_interface__,
        locations=merged.index,
        color='count',
        color_continuous_scale='Reds',
        mapbox_style='carto-positron',
        zoom=10,
        center={"lat": 43.7, "lon": -79.4},
        opacity=0.6,
        hover_name='AREA_NAME'
    )

    fig.update_traces(
        hovertemplate="<b>%{hovertext}</b><br>Total Kejahatan: %{z}<extra></extra>"
    )

    fig.update_layout(
        template='plotly_dark',
        plot_bgcolor='rgba(0, 0, 0, 0)',
        paper_bgcolor='rgba(0, 0, 0, 0)',
        margin=dict(l=0, r=0, t=0, b=0),
        height=550
    )

    st.plotly_chart(fig, use_container_width=True)

# ========== MAIN CONTENT ==========
st.title("📊 Kejahatan di Toronto")
st.markdown("Visualisai chart berdasarkan data Crimes in Toronto di Kaggle.")

col1, col2 = st.columns(2)

with col1:
    st.subheader("🔴 Kategori Kejahatan")
    bubble(df_crime)

with col2:
    st.subheader("🏠 Lokasi Kejahatan")
    bar_hor(df_crime)

st.subheader("🕒 Waktu Kejadian")

tab1, tab2 = st.tabs(["📅 Tahunan & Jam", "📈 Harian & Bulanan"])

with tab1:
    col1, col2 = st.columns(2)
    with col1:
        pie_ch(df_crime)  # Pie Chart
    with col2:
        radar_ch(df_crime)

with tab2:
    option = st.selectbox("Pilih jenis waktu:", ["per hari (tanggal)", "per bulan", "per hari dalam minggu"])
    if option == "per hari (tanggal)":
        line_ch(df_crime)
    elif option == "per bulan":
        line2_ch(df_crime)
    else:
        line3_ch(df_crime)

st.subheader("🗺️ Peta Persebaran Kejahatan")
maps(df_crime, geo_df)  # Choropleth Map

st.markdown(
    """
    <hr style="margin-top: 3rem; margin-bottom: 1rem; border-top: 1px solid #BBB;" />

    <div style="display: flex; justify-content: space-between; align-items: flex-start; font-size: 15px; color: gray; gap: 2rem;">
        <div style="max-width: 60%;">
            <strong>👥 Kelompok 7:</strong> 1. Azra Feby Awfiyah – 13101223300<br>
            <div style="margin-left: 107px;">
                2. Diva Sanjaya Wardani – 1301223167<br>
                3. Farah Saraswati – 1301223401<br>
                4. Nasywa Alif Widyasari – 1301223357
            </div>
        </div>
        <div style="text-align: right;">
            <strong>📊 Tugas Besar UTS Visualisasi Data:</strong> Dashboard Kejahatan di Toronto
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

