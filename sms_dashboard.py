import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(layout="wide")
st.title("📊 SMS Dashboard")

# File upload
uploaded_file = st.file_uploader("Upload CSV file", type=["csv"])
if uploaded_file is None:
    st.warning("Please upload a CSV file containing SMS data.")
    st.stop()

# Read file and parse dates
df = pd.read_csv(uploaded_file, parse_dates=["Date / Time"])
st.success(f"File loaded: {uploaded_file.name}")

# Filter only SMS messages
df = df[df["Message Type"] == "SMS"].copy()
df["Date"] = df["Date / Time"].dt.date

COST_PER_SEGMENT = 0.0085  # Segment cost

# Map company numbers to names
company_name_map = (
    df[df["Sender Name"].notna() & df["Sender Name"].str.strip().ne("")][["Sender Number", "Sender Name"]]
    .drop_duplicates()
)
company_name_map = dict(zip(company_name_map["Sender Number"], company_name_map["Sender Name"]))

# Date range filter
min_date, max_date = df["Date"].min(), df["Date"].max()
date_range = st.date_input("Select date range", (min_date, max_date), min_value=min_date, max_value=max_date)
df_filtered = df[(df["Date"] >= date_range[0]) & (df["Date"] <= date_range[1])]

# Overall stats
st.subheader("📈 Overall Statistics")
col1, col2, col3 = st.columns(3)
col1.metric("📤 Segments Sent", int(df_filtered[df_filtered["Direction"] == "Outbound"]["Segment Count"].sum()))
col2.metric("📥 Segments Received", int(df_filtered[df_filtered["Direction"] == "Inbound"]["Segment Count"].sum()))
col3.metric("💰 Total Cost", f"${df_filtered['Segment Count'].sum() * COST_PER_SEGMENT:.2f}")

# Daily chart
st.subheader("📆 Daily Interactive Chart")
daily = df_filtered.groupby(["Date", "Direction"])["Segment Count"].sum().unstack().fillna(0)
st.bar_chart(daily)

# Company numbers breakdown per day
st.subheader("📅 Company Numbers Breakdown by Selected Day")
available_dates = sorted(df_filtered["Date"].unique())
selected_day = st.selectbox("Select a date", available_dates)
daily_df = df[df["Date"] == selected_day]

outbound = (
    daily_df[daily_df["Direction"] == "Outbound"]
    .groupby("Sender Number")["Segment Count"]
    .sum()
    .rename("Sent")
)
inbound = (
    daily_df[daily_df["Direction"] == "Inbound"]
    .groupby("Recipient Number")["Segment Count"]
    .sum()
    .rename("Received")
)
daily_company_stats = pd.concat([outbound, inbound], axis=1).fillna(0).astype(int)
daily_company_stats["Total"] = daily_company_stats["Sent"] + daily_company_stats["Received"]
daily_company_stats.index = daily_company_stats.index.map(lambda num: company_name_map.get(num, num))
daily_company_stats.index.name = "Company Name / Number"
st.dataframe(daily_company_stats.reset_index())

# Bar chart of company numbers
st.subheader("📊 Bar Chart of Company Numbers on Selected Day")
fig, ax = plt.subplots(figsize=(10, 4))
daily_company_stats[["Sent", "Received"]].plot(kind="bar", ax=ax)
ax.set_title(f"SMS by Company Number — {selected_day}")
ax.set_ylabel("Segments")
ax.set_xlabel("Number / Name")
plt.xticks(rotation=45)
fig.tight_layout()
st.pyplot(fig)

# Company numbers total stats
st.subheader("📌 Total Statistics by Company Numbers (Entire Period)")
outbound_total = (
    df[df["Direction"] == "Outbound"]
    .groupby("Sender Number")[["Segment Count"]]
    .sum()
    .rename(columns={"Segment Count": "Sent"})
)
inbound_total = (
    df[df["Direction"] == "Inbound"]
    .groupby("Recipient Number")[["Segment Count"]]
    .sum()
    .rename(columns={"Segment Count": "Received"})
)
company_total = pd.concat([outbound_total, inbound_total], axis=1).fillna(0)
company_total["Sent"] = company_total["Sent"].astype(int)
company_total["Received"] = company_total["Received"].astype(int)
company_total["Total"] = company_total["Sent"] + company_total["Received"]
company_total["Cost"] = (company_total["Total"] * COST_PER_SEGMENT).round(4)
company_total = company_total.reset_index()
company_total["Company Name / Number"] = company_total["index"].map(lambda num: company_name_map.get(num, num))
company_numbers = company_total["index"].tolist()
company_total = company_total[["Company Name / Number", "Sent", "Received", "Total", "Cost"]]
st.dataframe(company_total)

# Top 20 external numbers
st.subheader("🌍 Top 20 External Numbers by Interaction Volume")
external_out = (
    df[df["Direction"] == "Outbound"]
    .groupby("Recipient Number")["Segment Count"]
    .sum()
    .rename("Segments Received")
)
external_in = (
    df[df["Direction"] == "Inbound"]
    .groupby("Sender Number")["Segment Count"]
    .sum()
    .rename("Segments Sent")
)
external_total = pd.concat([external_out, external_in], axis=1).fillna(0).astype(int)
external_total["Total"] = external_total["Segments Received"] + external_total["Segments Sent"]
external_total["Cost"] = (external_total["Total"] * COST_PER_SEGMENT).round(4)
top_20_clients = external_total.sort_values("Total", ascending=False).head(20).reset_index()
top_20_clients = top_20_clients.rename(columns={"index": "Client Number"})
st.dataframe(top_20_clients)

# Top 10 external numbers for selected company number
st.subheader("📞 Top 10 External Numbers for Selected Company Number")
selected_company = st.selectbox(
    "Select company number",
    company_numbers,
    format_func=lambda num: f"{company_name_map.get(num, num)} ({num})"
)

outgoing = (
    df[(df["Direction"] == "Outbound") & (df["Sender Number"] == selected_company)]
    .groupby("Recipient Number")["Segment Count"]
    .sum()
    .rename("Sent")
)

incoming = (
    df[(df["Direction"] == "Inbound") & (df["Recipient Number"] == selected_company)]
    .groupby("Sender Number")["Segment Count"]
    .sum()
    .rename("Received")
)

top_numbers = pd.concat([outgoing, incoming], axis=1).fillna(0).astype(int)
top_numbers["Total"] = top_numbers["Sent"] + top_numbers["Received"]
top_numbers = top_numbers.sort_values("Total", ascending=False).head(10).reset_index()
top_numbers = top_numbers.rename(columns={"index": "Number"})
st.dataframe(top_numbers)
