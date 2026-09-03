import streamlit as st
import csv
import os

# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Live GNSS GGA Dashboard",
    page_icon="📡",
    layout="wide"
)

# ============================================================
# FILE
# ============================================================

GGA_FILE = "gga_log.csv"

# ============================================================
# CSS
# ============================================================

st.markdown("""
<style>

.stApp {
    background-color: #F4F6F8;
}

.main .block-container {
    max-width: 1500px;
    padding-top: 25px;
}

.header {
    background-color: #12355B;
    padding: 22px 30px;
    border-radius: 10px;
    margin-bottom: 25px;
}

.title {
    color: white;
    font-size: 30px;
    font-weight: 700;
}

.subtitle {
    color: #DCE8F5;
    font-size: 15px;
    margin-top: 5px;
}

.section {
    color: #12355B;
    font-size: 21px;
    font-weight: 700;
    border-left: 5px solid #1E73BE;
    padding-left: 12px;
    margin-top: 25px;
    margin-bottom: 15px;
}

div[data-testid="stMetric"] {
    background-color: white;
    border: 1px solid #D9E0E7;
    border-radius: 10px;
    padding: 18px;
    box-shadow: 0px 2px 6px rgba(0,0,0,0.05);
}

div[data-testid="stMetricLabel"] {
    color: #64748B !important;
    font-weight: 600 !important;
}

div[data-testid="stMetricValue"] {
    color: #12355B !important;
    font-weight: 700 !important;
}

.gga-box {
    background-color: white;
    border: 1px solid #D9E0E7;
    border-radius: 10px;
    padding: 18px;
    font-family: monospace;
    color: #12355B;
    word-break: break-all;
}

</style>
""", unsafe_allow_html=True)


# ============================================================
# READ GGA CSV
# ============================================================

def load_gga():

    records = []

    if not os.path.exists(GGA_FILE):
        return records

    with open(
        GGA_FILE,
        "r",
        encoding="utf-8",
        errors="ignore"
    ) as file:

        reader = csv.reader(file)

        # Skip header
        next(reader, None)

        for row in reader:

            if len(row) < 2:
                continue

            timestamp = row[0]

            gga = ",".join(row[1:]).strip()

            if "$GNGGA" in gga or "$GPGGA" in gga:

                records.append({
                    "timestamp": timestamp,
                    "gga": gga
                })

    return records


# ============================================================
# LOAD DATA
# ============================================================

records = load_gga()

if not records:

    st.error("No GGA records found in gga_log.csv")

    st.stop()


# ============================================================
# SESSION STATE
# ============================================================

if "gga_index" not in st.session_state:

    st.session_state.gga_index = 0


# ============================================================
# CURRENT RECORD
# ============================================================

index = st.session_state.gga_index

current = records[index]

gga = current["gga"]

fields = gga.split(",")


# ============================================================
# EXTRACT GGA PARAMETERS
# ============================================================

utc_time = fields[1] if len(fields) > 1 else "-"

latitude = (
    fields[2] + " " + fields[3]
    if len(fields) > 3 else "-"
)

longitude = (
    fields[4] + " " + fields[5]
    if len(fields) > 5 else "-"
)

fix_quality = (
    fields[6] if len(fields) > 6 else "-"
)

satellites = (
    fields[7] if len(fields) > 7 else "-"
)

hdop = (
    fields[8] if len(fields) > 8 else "-"
)

altitude = (
    fields[9] + " m"
    if len(fields) > 9 else "-"
)

geoid = (
    fields[11] + " m"
    if len(fields) > 11 else "-"
)


# ============================================================
# HEADER
# ============================================================

st.markdown("""
<div class="header">

<div class="title">
📡 Live GNSS GGA Monitoring Dashboard
</div>

<div class="subtitle">
Recorded GGA Data Replay
</div>

</div>
""", unsafe_allow_html=True)


# ============================================================
# SYSTEM OVERVIEW
# ============================================================

st.markdown(
    '<div class="section">System Overview</div>',
    unsafe_allow_html=True
)

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.metric("System", "GNSS")

with c2:
    st.metric("Data Source", "Recorded GGA")

with c3:
    st.metric(
        "Total GGA Records",
        len(records)
    )

with c4:
    st.metric(
        "Current Record",
        f"{index + 1} / {len(records)}"
    )


# ============================================================
# LIVE GGA
# ============================================================

st.markdown(
    '<div class="section">Live GGA Data</div>',
    unsafe_allow_html=True
)

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.metric(
        "UTC Time",
        utc_time
    )

with c2:
    st.metric(
        "Satellites",
        satellites
    )

with c3:
    st.metric(
        "HDOP",
        hdop
    )

with c4:
    st.metric(
        "Fix Quality",
        fix_quality
    )


# ============================================================
# POSITION
# ============================================================

st.markdown(
    '<div class="section">Position Information</div>',
    unsafe_allow_html=True
)

c1, c2, c3 = st.columns(3)

with c1:
    st.metric(
        "Latitude",
        latitude
    )

with c2:
    st.metric(
        "Longitude",
        longitude
    )

with c3:
    st.metric(
        "Altitude",
        altitude
    )


# ============================================================
# GNSS PARAMETERS
# ============================================================

st.markdown(
    '<div class="section">GNSS Parameters</div>',
    unsafe_allow_html=True
)

c1, c2 = st.columns(2)

with c1:
    st.metric(
        "Geoid Separation",
        geoid
    )

with c2:
    st.metric(
        "GGA Timestamp",
        current["timestamp"]
    )


# ============================================================
# RAW GGA
# ============================================================

st.markdown(
    '<div class="section">Current GGA Message</div>',
    unsafe_allow_html=True
)

st.markdown(
    f"""
    <div class="gga-box">
    {gga}
    </div>
    """,
    unsafe_allow_html=True
)


# ============================================================
# NEXT RECORD BUTTON
# ============================================================

st.markdown(
    '<div class="section">Data Control</div>',
    unsafe_allow_html=True
)

if st.button(
    "▶ Load Next GGA",
    use_container_width=True
):

    st.session_state.gga_index += 1

    if st.session_state.gga_index >= len(records):

        st.session_state.gga_index = 0

    st.rerun()


st.info(
    "Click 'Load Next GGA' to replay the next recorded GGA message."
)