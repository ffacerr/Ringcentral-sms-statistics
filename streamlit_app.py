import streamlit as st
import pandas as pd


def main():
    st.title("SMS Statistics")
    uploaded_file = st.file_uploader("Загрузите CSV", type=["csv"])
    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file, parse_dates=["Date / Time"])
        st.write(df)


if __name__ == "__main__":
    main()
