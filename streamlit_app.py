import streamlit as st
import pandas as pd

st.set_page_config(page_title="Car Sales Analysis Dashboard", page_icon="🚗")

# carregando e limpando base de dados
df = pd.read_csv("db/car_sales.csv") 

df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
df["Engine"] = df["Engine"].str.replace(r"[^\w\s]", "", regex=True)

df["Phone"] = df["Phone"].astype(str)
df["Dealer_No"] = df["Dealer_No"].astype(str)

text_columns = df.select_dtypes(include=["object"]).columns
df[text_columns] = df[text_columns].apply(lambda x: x.str.strip())