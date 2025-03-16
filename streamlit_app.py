import streamlit as st
import pandas as pd
import locale

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

