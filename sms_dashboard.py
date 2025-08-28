import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(layout="wide")
st.title("📊 SMS Dashboard")

# 📥 Загрузка SMS-файла
uploaded_file = st.file_uploader("Загрузите CSV-файл", type=["csv"])
if uploaded_file is None:
    st.warning("Пожалуйста, загрузите CSV-файл, содержащий данные SMS.")
    st.stop()

df = pd.read_csv(uploaded_file, parse_dates=["Date / Time"])
st.success(f"Загружен файл: {uploaded_file.name}")

df = df[df["Message Type"] == "SMS"].copy()
df["Date"] = df["Date / Time"].dt.date

COST_PER_SEGMENT = 0.0085  # 💵 стоимость одного сегмента

# 🧭 Сопоставление номеров и имён
company_name_map = (
    df[df["Sender Name"].notna() & df["Sender Name"].str.strip().ne("")]
    [["Sender Number", "Sender Name"]]
    .drop_duplicates()
)
company_name_map = dict(zip(company_name_map["Sender Number"], company_name_map["Sender Name"]))

# 📅 Диапазон дат
min_date, max_date = df["Date"].min(), df["Date"].max()
date_range = st.date_input("Выберите диапазон дат", (min_date, max_date), min_value=min_date, max_value=max_date)
df_filtered = df[(df["Date"] >= date_range[0]) & (df["Date"] <= date_range[1])]

# 📈 Общая статистика
st.subheader("📈 Общая статистика")
col1, col2, col3 = st.columns(3)
col1.metric("📤 Отправлено сегментов", int(df_filtered[df_filtered["Direction"] == "Outbound"]["Segment Count"].sum()))
col2.metric("📥 Получено сегментов", int(df_filtered[df_filtered["Direction"] == "Inbound"]["Segment Count"].sum()))
col3.metric("💰 Общая стоимость", f"${df_filtered['Segment Count'].sum() * COST_PER_SEGMENT:.2f}")

# 📊 График по дням
st.subheader("📆 Интерактивный график по дням")
daily = df_filtered.groupby(["Date", "Direction"])["Segment Count"].sum().unstack().fillna(0)
st.bar_chart(daily)

# 📌 Разбивка по номерам компании за день
st.subheader("📅 Разбивка по номерам компании за выбранный день")
available_dates = sorted(df_filtered["Date"].unique())
selected_day = st.selectbox("Выберите дату", available_dates)
daily_df = df[df["Date"] == selected_day]

outbound = (
    daily_df[daily_df["Direction"] == "Outbound"]
    .groupby("Sender Number")["Segment Count"]
    .sum()
    .rename("Отправлено")
)
inbound = (
    daily_df[daily_df["Direction"] == "Inbound"]
    .groupby("Recipient Number")["Segment Count"]
    .sum()
    .rename("Получено")
)
daily_company_stats = pd.concat([outbound, inbound], axis=1).fillna(0).astype(int)
daily_company_stats["Всего"] = daily_company_stats["Отправлено"] + daily_company_stats["Получено"]
daily_company_stats.index = daily_company_stats.index.map(lambda num: company_name_map.get(num, num))
daily_company_stats.index.name = "Имя/Номер компании"
st.dataframe(daily_company_stats.reset_index())

# 📊 График по номерам компании
st.subheader("📊 График по номерам компании за выбранный день")
fig, ax = plt.subplots(figsize=(10, 4))
daily_company_stats[["Отправлено", "Получено"]].plot(kind="bar", ax=ax)
ax.set_title(f"SMS по номерам компании — {selected_day}")
ax.set_ylabel("Сегментов")
ax.set_xlabel("Номер / Имя")
plt.xticks(rotation=45)
fig.tight_layout()
st.pyplot(fig)

# 🧾 Общая статистика по всем номерам компании
st.subheader("📌 Общая статистика по номерам компании (весь период)")
outbound_total = (
    df[df["Direction"] == "Outbound"]
    .groupby("Sender Number")[["Segment Count"]]
    .sum()
    .rename(columns={"Segment Count": "Отправлено"})
)
inbound_total = (
    df[df["Direction"] == "Inbound"]
    .groupby("Recipient Number")[["Segment Count"]]
    .sum()
    .rename(columns={"Segment Count": "Получено"})
)
company_total = pd.concat([outbound_total, inbound_total], axis=1).fillna(0)
company_total["Отправлено"] = company_total["Отправлено"].astype(int)
company_total["Получено"] = company_total["Получено"].astype(int)
company_total["Всего"] = company_total["Отправлено"] + company_total["Получено"]
company_total["Стоимость"] = (company_total["Всего"] * COST_PER_SEGMENT).round(4)
company_total = company_total.reset_index()
company_total["Имя/Номер компании"] = company_total["index"].map(lambda num: company_name_map.get(num, num))
company_total = company_total[["Имя/Номер компании", "Отправлено", "Получено", "Всего", "Стоимость"]]
st.dataframe(company_total)

# 🌍 ТОП-20 внешних номеров
st.subheader("🌎 ТОП-20 внешних номеров по сумме взаимодействий")
external_out = (
    df[df["Direction"] == "Outbound"]
    .groupby("Recipient Number")["Segment Count"]
    .sum()
    .rename("Сегментов получено")
)
external_in = (
    df[df["Direction"] == "Inbound"]
    .groupby("Sender Number")["Segment Count"]
    .sum()
    .rename("Сегментов отправлено")
)
external_total = pd.concat([external_out, external_in], axis=1).fillna(0).astype(int)
external_total["Всего"] = external_total["Сегментов получено"] + external_total["Сегментов отправлено"]
external_total["Стоимость"] = (external_total["Всего"] * COST_PER_SEGMENT).round(4)
top_20_clients = external_total.sort_values("Всего", ascending=False).head(20).reset_index()
top_20_clients = top_20_clients.rename(columns={"index": "Номер клиента"})
st.dataframe(top_20_clients)

# 🔍 Поиск по номеру
st.subheader("🔍 Поиск по номеру (любой: клиент или компания)")
search_number = st.text_input("Введите номер, например: 13134843120")

if search_number:
    sent = df[(df["Recipient Number"] == search_number)]
    received = df[(df["Sender Number"] == search_number)]

    st.write(f"📤 Отправлено на этот номер: {len(sent)} сообщений ({sent['Segment Count'].sum()} сегментов)")
    st.write(f"📥 Получено от этого номера: {len(received)} сообщений ({received['Segment Count'].sum()} сегментов)")

    with st.expander("📤 Исходящие этому номеру"):
        st.dataframe(sent[["Date / Time", "Sender Number", "Recipient Number", "Segment Count"]])

    with st.expander("📥 Входящие от этого номера"):
        st.dataframe(received[["Date / Time", "Sender Number", "Recipient Number", "Segment Count"]])
