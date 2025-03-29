import streamlit as st
import pandas as pd
import locale
import re
from streamlit_echarts import st_echarts
import pydeck as pdk
from geopy.geocoders import Photon
from geopy.extra.rate_limiter import RateLimiter

# Configurar o locale para o formato de moeda
locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')

st.set_page_config(page_title="Car Sales Analysis Dashboard", page_icon="🚗", layout="wide",)

# carregando e limpando base de dados
@st.cache_data
def carregar_dados():
    df = pd.read_csv("db/car_sales.csv") 

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Engine"] = df["Engine"].str.replace(r"[^\w\s]", "", regex=True)

    df["Phone"] = df["Phone"].astype(str)
    df["Dealer_No"] = df["Dealer_No"].astype(str)

    text_columns = df.select_dtypes(include=["object"]).columns
    df[text_columns] = df[text_columns].apply(lambda x: x.str.strip())

    if "Latitude" not in df.columns or "Longitude" not in df.columns:
        geolocator = Photon(user_agent="meu_app_vendas", timeout=10)
        geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)

        cache_coordenadas = {}

        def obter_coordenadas(regiao):
            if regiao in cache_coordenadas:
                return cache_coordenadas[regiao]
            try:
                location = geocode(regiao)
                if location:
                    coordenadas = (location.latitude, location.longitude)
                else:
                    coordenadas = (None, None)
            except Exception:
                coordenadas = (None, None)
            
            cache_coordenadas[regiao] = coordenadas
            return coordenadas

        df["Latitude"], df["Longitude"] = zip(*df["Dealer_Region"].apply(obter_coordenadas))
        df = df.dropna(subset=["Latitude", "Longitude"]) 
    
    return df

df = carregar_dados()

# Função para formatar números
def format_number(num):
    if num >= 100000:
        return f"{str(num)[:len(str(num))-6]}M"
    return f"{num:,}"

# cards
qtd_vendas_total = df["Car_id"].nunique()
media_precos = round(df["Price ($)"].mean())
vendas_total = df["Price ($)"].sum()
quantidade_auto = df['Transmission'].value_counts()['Auto']
quantidade_manual = df['Transmission'].value_counts()['Manual']

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Qtd de vendas", f"{format_number(qtd_vendas_total)}")
col2.metric("Media de Preços", f"R$ {format_number(media_precos)}")
col3.metric("Vendas totais", f"R$ {format_number(vendas_total)}")
col4.metric("Carros Automaticos", f"{format_number(quantidade_auto)}")
col5.metric("Carros Manuais", f"{format_number(quantidade_manual)}")

# Vendas por mês
df["Month"] = df["Date"].dt.month
sales_by_month = df["Month"].value_counts().sort_index()
month_order = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
sales_by_month.index = sales_by_month.index.map(lambda x: month_order[x-1])

option = {
    "xAxis": {
        "type": "category",
        "data": sales_by_month.index.tolist(),
    },
    "yAxis": {"type": "value"},
    "series": [{"data": sales_by_month.values.tolist(), "type": "line"}],
}

st_echarts(
    options=option, height="400px",
)

# Quantidade de vendas por cor do carro
sales_by_color = df['Color'].value_counts()
sales_by_color_list = [{"value": value, "name": name} for name, value in sales_by_color.items()]

options = {
    "tooltip": {"trigger": "item"},
    "legend": {"orient": "vertical", "left": "left",},
    "series": [
        {
            "name": "Vendas por Cor",
            "type": "pie",
            "radius": "50%",
            "data": sales_by_color_list,
            "emphasis": {
                "itemStyle": {
                    "shadowBlur": 10,
                    "shadowOffsetX": 0,
                    "shadowColor": "rgba(0, 0, 0, 0.5)",
                }
            },
        }
    ],
}

st_echarts(
    options=options, height="600px",
)

# Vendas por Genero e agrupado por Anual Income

bins = list(range(0, 1000000, 100000)) + [float('inf')]
labels = [f"{i}-{i+100000}" for i in range(0, 900000, 100000)] + ["900k+"]

df["Income Category"] = pd.cut(df["Annual Income"], bins=bins, labels=labels, right=False)

income_by_gender = df.pivot_table(
    index="Income Category", 
    columns="Gender", 
    aggfunc="size", 
    fill_value=0, 
    observed=False
)

income_by_gender = income_by_gender.assign(Total=income_by_gender.sum(axis=1))
income_by_gender = income_by_gender.sort_values(by="Total", ascending=True)
income_by_gender = income_by_gender.drop(columns=["Total"]) 

male_counts = income_by_gender.get("Male", []).tolist()
female_counts = income_by_gender.get("Female", []).tolist()
index_income_by_gender = [re.sub(r"(\d{1,3})000", r"\1k", str(label)) for label in income_by_gender.index.tolist()]

options = {
    "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
    "legend": {
        "data": ["Male", "Female"]
    },
    "grid": {"left": "3%", "right": "4%", "bottom": "3%", "containLabel": True},
    "xAxis": {"type": "value"},
    "yAxis": {
        "type": "category",
        "data": index_income_by_gender,
    },
    "series": [
        {
            "name": "Male",
            "type": "bar",
            "stack": "total",
            "label": {"show": True},
            "emphasis": {"focus": "series"},
            "data": male_counts,
        },
        {
            "name": "Female",
            "type": "bar",
            "stack": "total",
            "label": {"show": True},
            "emphasis": {"focus": "series"},
            "data": female_counts,
        }
    ],
}
st_echarts(options=options, height="500px")

#Total de vendas por empresa

sales_by_company = df.groupby("Company")["Price ($)"].sum().sort_values(ascending=True)

companies_array = sales_by_company.index.tolist()  
sales_totals_array = sales_by_company.values.tolist()

options = {
    "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
    "legend": {
        "data": companies_array
    },
    "grid": {"left": "3%", "right": "4%", "bottom": "3%", "containLabel": True},
    "xAxis": {"type": "value"},
    "yAxis": {
        "type": "category",
        "data": companies_array,
    },
    "series": [
        {
            "name": "Sales",
            "type": "bar",
            "stack": "total",
            "label": {"show": True},
            "emphasis": {"focus": "series"},
            "data": sales_totals_array,
        }
    ],
}

st_echarts(options=options, height="500px")

view_state = pdk.ViewState(
    latitude=df["Latitude"].mean(),  # Centraliza no meio dos pontos
    longitude=df["Longitude"].mean(),
    zoom=4
)

# Camada de pontos
layer = pdk.Layer(
    "ScatterplotLayer",
    data=df,
    get_position="[Longitude, Latitude]",
    get_radius=30000,  # Tamanho do ponto no mapa
    get_color=[255, 0, 0, 150],  # Cor (vermelho semi-transparente)
    pickable=True
)

# Renderizar o mapa no Streamlit
r = pdk.Deck(layers=[layer], initial_view_state=view_state, tooltip={"text": "{Dealer_Region}\nVendas: {Price ($)}"})
st.pydeck_chart(r)