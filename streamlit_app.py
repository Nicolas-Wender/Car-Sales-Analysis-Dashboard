import streamlit as st
import pandas as pd
import locale
import re
from streamlit_echarts import st_echarts
import pydeck as pdk
from geopy.geocoders import Photon
from geopy.extra.rate_limiter import RateLimiter


# Define a localização local para Português do Brasil
locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')

# Configuração da página do Streamlit
st.set_page_config(page_title="Car Sales Analysis Dashboard", page_icon="🚗", layout="wide",)

@st.cache_data
def carregar_dados():
    """Carrega e limpa a base de dados"""
    
    # Carrega o arquivo CSV com os dados das vendas de carros
    df = pd.read_csv("db/car_sales.csv") 

    # Converte a coluna "Date" para o formato datetime
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    # Remove caracteres especiais na coluna "Engine"
    df["Engine"] = df["Engine"].str.replace(r"[^\w\s]", "", regex=True)

    # Converte as colunas "Phone" e "Dealer_No" para string
    df["Phone"] = df["Phone"].astype(str)
    df["Dealer_No"] = df["Dealer_No"].astype(str)

    # Remove espaços em branco nas colunas de texto
    text_columns = df.select_dtypes(include=["object"]).columns
    df[text_columns] = df[text_columns].apply(lambda x: x.str.strip())

    # Verifica se as colunas "Latitude" e "Longitude" estão presentes, caso contrário, obtém coordenadas
    if "Latitude" not in df.columns or "Longitude" not in df.columns:
        geolocator = Photon(user_agent="meu_app_vendas", timeout=10)
        geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)

        # Cache para armazenar coordenadas geográficas
        cache_coordenadas = {}

        def obter_coordenadas(regiao):
            # Verifica se as coordenadas já estão no cache
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
            
            # Armazena as coordenadas no cache
            cache_coordenadas[regiao] = coordenadas
            return coordenadas

        # Obtém coordenadas para cada região do dealer
        df["Latitude"], df["Longitude"] = zip(*df["Dealer_Region"].apply(obter_coordenadas))
        # Remove registros com coordenadas inválidas
        df = df.dropna(subset=["Latitude", "Longitude"]) 
    
    return df

# Carrega os dados
df = carregar_dados()

def format_number(num):
    """Formata números para uma visualização simplificada."""
    if num >= 100000:
        return f"{str(num)[:len(str(num))-6]}M"
    return f"{num:,}"

def venda_por_mes(df):
    # Cria uma nova coluna "Month" baseada na coluna "Date"
    df["Month"] = df["Date"].dt.month
    # Conta o número de vendas por mês
    sales_by_month = df["Month"].value_counts().sort_index()
    # Define a ordem dos meses em português
    month_order = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
    # Mapeia os índices dos meses para os nomes dos meses
    sales_by_month.index = sales_by_month.index.map(lambda x: month_order[x-1])

    # Configuração do gráfico de linha
    option = {
        "xAxis": {
            "type": "category",
            "data": sales_by_month.index.tolist(),
        },
        "yAxis": {"type": "value"},
        "series": [{"data": sales_by_month.values.tolist(), "type": "line"}],
    }

    return option

def venda_por_cor(df):
    # Conta o número de vendas por cor do carro
    sales_by_color = df['Color'].value_counts()
    # Formata os dados para o gráfico de pizza
    sales_by_color_list = [{"value": value, "name": name} for name, value in sales_by_color.items()]

    # Configuração do gráfico de pizza
    options = {
        "tooltip": {"trigger": "item"},
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

    return options

def venda_por_genero(df):
    # Define as faixas de renda anual
    bins = list(range(0, 1000000, 100000)) + [float('inf')]
    labels = [f"{i}-{i+100000}" for i in range(0, 900000, 100000)] + ["900k+"]

    # Cria uma nova coluna "Income Category" baseada na coluna "Annual Income"
    df["Income Category"] = pd.cut(df["Annual Income"], bins=bins, labels=labels, right=False)

    # Cria uma tabela pivô para contar as vendas por categoria de renda e gênero
    income_by_gender = df.pivot_table(
        index="Income Category", 
        columns="Gender", 
        aggfunc="size", 
        fill_value=0, 
        observed=False
    )

    # Adiciona uma coluna total e ordena os dados
    income_by_gender = income_by_gender.assign(Total=income_by_gender.sum(axis=1))
    income_by_gender = income_by_gender.sort_values(by="Total", ascending=True)
    income_by_gender = income_by_gender.drop(columns=["Total"]) 

    # Separa os dados por gênero
    male_counts = income_by_gender.get("Male", []).tolist()
    female_counts = income_by_gender.get("Female", []).tolist()
    # Formata os rótulos das categorias de renda
    index_income_by_gender = [re.sub(r"(\d{1,3})000", r"\1k", str(label)) for label in income_by_gender.index.tolist()]

    # Configuração do gráfico de barras empilhadas
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

    return options

def total_de_vendas_por_empresa(df):
    # Agrupa as vendas por empresa e soma os valores
    sales_by_company = df.groupby("Company")["Price ($)"].sum().sort_values(ascending=True)

    # Prepara os dados para o gráfico de barras
    companies_array = sales_by_company.index.tolist()  
    sales_totals_array = sales_by_company.values.tolist()

    # Configuração do gráfico de barras
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

    return options

def mapa_de_vendas(df):
    # Define a visualização inicial do mapa
    view_state = pdk.ViewState(
        latitude=df["Latitude"].mean(),  
        longitude=df["Longitude"].mean(),
        zoom=4
    )

    # Cria uma camada de pontos de venda
    layer = pdk.Layer(
        "ScatterplotLayer",
        data=df,
        get_position="[Longitude, Latitude]",
        get_radius=30000, 
        get_color=[255, 0, 0, 150],  
        pickable=True
    )

    # Configuração do mapa com a camada de pontos de venda
    r = pdk.Deck(layers=[layer], initial_view_state=view_state, tooltip={"text": "{Dealer_Region}\nVendas: {Price ($)}"})

    return r

# Calcula as métricas principais para exibição
qtd_vendas_total = df["Car_id"].nunique()
media_precos = round(df["Price ($)"].mean())
vendas_total = df["Price ($)"].sum()
quantidade_auto = df['Transmission'].value_counts()['Auto']
quantidade_manual = df['Transmission'].value_counts()['Manual']

# Exibe as métricas principais
col1a, col2a, col3a, col4a, col5a = st.columns(5)
col1a.metric("Qtd de vendas", f"{format_number(qtd_vendas_total)}")
col2a.metric("Media de Preços", f"R$ {format_number(media_precos)}")
col3a.metric("Vendas totais", f"R$ {format_number(vendas_total)}")
col4a.metric("Vendas por Carros Automaticos", f"{format_number(quantidade_auto)}")
col5a.metric("Vendas por Carros Manuais", f"{format_number(quantidade_manual)}")

st.divider()

# Exibe os gráficos de vendas por mês, cor do carro e o mapa de vendas
col1b, col2b, col3b = st.columns(3)

with col1b:
    st.write("Gráfico de Vendas por Mês")
    st_echarts(
        options=venda_por_mes(df), height="400px",
    )
with col2b:
    st.write("Gráfico de Vendas por Cor do Carro")
    st_echarts(
        options=venda_por_cor(df), height="400px",
    )

with col3b:
    st.write("Mapa de Vendas")
    st.pydeck_chart(mapa_de_vendas(df))

st.divider()

# Exibe os gráficos de vendas por gênero e por fabricante
col1c, col2c = st.columns(2)

with col1c:
    st.write("Total de vendas por gênero")
    st_echarts(options=venda_por_genero(df), height="500px")

with col2c:
    st.write("Total de vendas por fabricante")
    st_echarts(options=total_de_vendas_por_empresa(df), height="500px")