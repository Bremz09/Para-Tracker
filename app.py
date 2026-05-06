import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np

st.set_page_config(page_title="Para Tracker", layout="wide")
st.title("Para Tracker – Results")


def time_to_seconds(t):
    if pd.isnull(t):
        return None
    t_str = str(t)
    if "days" in t_str:
        t_str = t_str.split("days")[-1].strip()
    try:
        parts = t_str.split(":")
        if len(parts) == 1:
            # Already in seconds (e.g. 200m times stored as 10.728)
            return float(parts[0])
        h, m, s = float(parts[0]), float(parts[1]), float(parts[2])
        return h * 3600 + m * 60 + s
    except Exception:
        return None


def format_time(seconds, event):
    """Format seconds into event-appropriate time string."""
    if seconds is None or (isinstance(seconds, float) and pd.isna(seconds)):
        return ""
    if event in ("Kilo", "IP"):
        minutes = int(seconds // 60)
        remaining = seconds % 60
        secs = int(remaining)
        millis = round((remaining - secs) * 1000)
        return f"{minutes:02d}:{secs:02d}.{millis:03d}"
    elif event == "200m":
        secs = int(seconds)
        millis = round((seconds - secs) * 1000)
        return f"{secs}.{millis:03d}"
    else:
        minutes = int(seconds // 60)
        remaining = seconds % 60
        secs = int(remaining)
        millis = round((remaining - secs) * 1000)
        return f"{minutes:02d}:{secs:02d}.{millis:03d}"


@st.cache_data
def load_data():
    df = pd.read_excel("results.xlsx", sheet_name="data")
    df["Time_seconds"] = df["Time"].apply(time_to_seconds)
    df["Date"] = pd.to_datetime(df["Date"])
    return df


df = load_data()

# Pre-compute formatted time label per row (depends on Event)
df["Time_label"] = df.apply(
    lambda row: format_time(row["Time_seconds"], row["Event"]), axis=1
)

st.sidebar.header("Filters")

all_names = sorted(df["Name"].dropna().unique())
all_events = sorted(df["Event"].dropna().unique())

selected_names = st.sidebar.multiselect("Name", all_names, default=[])
selected_events = st.sidebar.multiselect("Event", all_events, default=all_events)

min_date = df["Date"].min().date()
max_date = df["Date"].max().date()
date_range = st.sidebar.date_input(
    "Date range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
)

# Apply filters – if no names selected, show nothing
filtered = df[
    df["Name"].isin(selected_names)
    & df["Event"].isin(selected_events)
]

if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
    start_date, end_date = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
    filtered = filtered[(filtered["Date"] >= start_date) & (filtered["Date"] <= end_date)]

if filtered.empty:
    st.warning("No results match the selected filters.")
else:
    filtered = filtered.sort_values("Date")

    colors = [
        "#636EFA", "#EF553B", "#00CC96", "#AB63FA", "#FFA15A",
        "#19D3F3", "#FF6692", "#B6E880", "#FF97FF", "#FECB52",
    ]
    name_list = sorted(filtered["Name"].unique())
    name_color = {n: colors[i % len(colors)] for i, n in enumerate(name_list)}
    event_list = sorted(filtered["Event"].unique())

    for event in event_list:
        event_data = filtered[filtered["Event"] == event]
        if event_data.empty:
            continue

        st.subheader(event)
        fig = go.Figure()

        for name in name_list:
            subset = event_data[event_data["Name"] == name]
            if subset.empty:
                continue
            fig.add_trace(go.Scatter(
                x=subset["Date"],
                y=subset["Time_seconds"],
                mode="lines+markers",
                name=name,
                marker=dict(symbol="circle", size=9, color=name_color[name]),
                line=dict(color=name_color[name]),
                customdata=list(zip(
                    subset["Name"],
                    subset["Event"],
                    subset["Competition"],
                    subset["Date"].dt.strftime("%d/%m/%Y"),
                    subset["Time_label"],
                )),
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>"
                    "Event: %{customdata[1]}<br>"
                    "Competition: %{customdata[2]}<br>"
                    "Date: %{customdata[3]}<br>"
                    "Time: %{customdata[4]}<extra></extra>"
                ),
            ))

        y_vals = event_data["Time_seconds"].dropna().values
        unique_y = np.unique(y_vals)
        tick_vals = list(np.linspace(unique_y.min(), unique_y.max(), min(10, len(unique_y))))
        tick_text = [format_time(v, event) for v in tick_vals]

        fig.update_yaxes(tickvals=tick_vals, ticktext=tick_text, title="Time")
        fig.update_xaxes(title="Date", tickformat="%d/%m/%Y")
        fig.update_layout(height=500)

        st.plotly_chart(fig, use_container_width=True)

    # Data table – always visible
    display = (
        filtered[["Name", "Event", "Competition", "Date", "Time_label"]]
        .copy()
        .rename(columns={"Time_label": "Time"})
    )
    display["Date"] = display["Date"].dt.strftime("%d/%m/%Y")
    st.dataframe(display.reset_index(drop=True), use_container_width=True)
