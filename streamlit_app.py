import streamlit as st
import pandas as pd
import locale
import re
from streamlit_echarts import st_echarts

# Configurar o locale para o formato de moeda
locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')

st.set_page_config(page_title="Car Sales Analysis Dashboard", page_icon="🚗", layout="wide",)

# carregando e limpando base de dados
df = pd.read_csv("db/car_sales.csv") 

df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
df["Engine"] = df["Engine"].str.replace(r"[^\w\s]", "", regex=True)

df["Phone"] = df["Phone"].astype(str)
df["Dealer_No"] = df["Dealer_No"].astype(str)

text_columns = df.select_dtypes(include=["object"]).columns
df[text_columns] = df[text_columns].apply(lambda x: x.str.strip())

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

# Vendas de carro por Genero e agrupado por Anual Income

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