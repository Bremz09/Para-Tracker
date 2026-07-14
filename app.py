import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np

st.set_page_config(page_title="Para Tracker", layout="wide")
st.title("Para Tracker – Results")

PLACE_EVENTS = {"Elimination", "Scratch"}


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


def format_place(place):
    if place is None or (isinstance(place, float) and pd.isna(place)):
        return ""
    if isinstance(place, (int, np.integer)):
        return str(place)
    if isinstance(place, (float, np.floating)):
        if float(place).is_integer():
            return str(int(place))
        return str(place)
    return str(place)


@st.cache_data
def load_data():
    df = pd.read_excel("para race results.xlsx", sheet_name="data")
    df["Time_seconds"] = df["Time"].apply(time_to_seconds)
    df["Place_value"] = pd.to_numeric(df["Place"], errors="coerce")
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
all_competition_types = sorted(df["Competition"].dropna().unique())

selected_names = st.sidebar.multiselect("Name", all_names, default=["BRIGGS Devon","MURRAY Nicole","FOY Emma", "TERRY Siobhan","TAYLOR Anna"])
selected_events = st.sidebar.multiselect("Event", all_events, default=all_events)
selected_competition_types = st.sidebar.multiselect(
    "Competition type",
    all_competition_types,
    default=all_competition_types,
)

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
    & df["Competition"].isin(selected_competition_types)
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

    event_tabs = st.tabs(event_list)

    for tab, event in zip(event_tabs, event_list):
        event_data = filtered[filtered["Event"] == event]
        if event_data.empty:
            continue

        y_column = "Place_value" if event in PLACE_EVENTS else "Time_seconds"
        y_title = "Place" if event in PLACE_EVENTS else "Time"

        plot_data = event_data.dropna(subset=[y_column])

        with tab:
            if plot_data.empty:
                st.warning(f"No {y_title.lower()} data is available for {event}.")
                continue

            fig = go.Figure()

            for name in name_list:
                subset = plot_data[plot_data["Name"] == name]
                if subset.empty:
                    continue

                if event in PLACE_EVENTS:
                    customdata = list(zip(
                        subset["Name"],
                        subset["Event"],
                        subset["Competition"],
                        subset["Location"],
                        subset["Date"].dt.strftime("%d/%m/%Y"),
                        subset["Place"].apply(format_place),
                    ))
                    hovertemplate = (
                        "<b>%{customdata[0]}</b><br>"
                        "Event: %{customdata[1]}<br>"
                        "Competition: %{customdata[2]}<br>"
                        "Location: %{customdata[3]}<br>"
                        "Date: %{customdata[4]}<br>"
                        "Place: %{customdata[5]}<extra></extra>"
                    )
                else:
                    customdata = list(zip(
                        subset["Name"],
                        subset["Event"],
                        subset["Competition"],
                        subset["Location"],
                        subset["Date"].dt.strftime("%d/%m/%Y"),
                        subset["Time_label"],
                    ))
                    hovertemplate = (
                        "<b>%{customdata[0]}</b><br>"
                        "Event: %{customdata[1]}<br>"
                        "Competition: %{customdata[2]}<br>"
                        "Location: %{customdata[3]}<br>"
                        "Date: %{customdata[4]}<br>"
                        "Time: %{customdata[5]}<extra></extra>"
                    )

                fig.add_trace(go.Scatter(
                    x=subset["Date"],
                    y=subset[y_column],
                    mode="lines+markers",
                    name=name,
                    marker=dict(symbol="circle", size=9, color=name_color[name]),
                    line=dict(color=name_color[name]),
                    customdata=customdata,
                    hovertemplate=hovertemplate,
                ))

            y_vals = plot_data[y_column].dropna().values
            unique_y = np.unique(y_vals)

            if event in PLACE_EVENTS:
                tick_vals = unique_y.tolist()
                tick_text = [format_place(v) for v in tick_vals]
                fig.update_yaxes(
                    tickvals=tick_vals,
                    ticktext=tick_text,
                    title=y_title,
                )
            else:
                tick_vals = list(np.linspace(unique_y.min(), unique_y.max(), min(10, len(unique_y))))
                tick_text = [format_time(v, event) for v in tick_vals]
                fig.update_yaxes(tickvals=tick_vals, ticktext=tick_text, title=y_title)

            fig.update_xaxes(title="Date", tickformat="%d/%m/%Y")
            fig.update_layout(height=500)

            st.plotly_chart(fig, use_container_width=True)

    # Data table – always visible
    display = (
        filtered[["Name", "Event", "Competition", "Location", "Date", "Time_label"]]
        .copy()
        .rename(columns={"Time_label": "Time"})
    )
    display["Date"] = display["Date"].dt.strftime("%d/%m/%Y")
    st.dataframe(display.reset_index(drop=True), use_container_width=True)
