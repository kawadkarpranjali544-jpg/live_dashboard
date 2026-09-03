import streamlit as st
import pandas as pd
import os
import time
from datetime import datetime


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="GNSS / RTCM Live Monitoring",
    page_icon="📡",
    layout="wide"
)


# ============================================================
# FILE SETTINGS
# ============================================================

RTCM_FILE = "rtcm_live_log.csv"
GGA_FILE = "gga_log.csv"


# ============================================================
# REQUIRED RTCM MESSAGE TYPES
# ============================================================

TARGET_MESSAGES = {
    1005: "Reference Station ARP",
    1006: "Reference Station ARP + Antenna Height",
    1008: "Antenna Descriptor & Serial Number",
    1013: "System Parameters",
    1019: "GPS Satellite Ephemeris",
    1020: "GLONASS Satellite Ephemeris",
    1029: "Unicode Text String",
    1032: "Physical Reference Station",
    1033: "Receiver & Antenna Descriptor",
    1042: "BeiDou Satellite Ephemeris",
    1044: "QZSS Satellite Ephemeris",
    1045: "Galileo F/NAV Ephemeris",
    1046: "Galileo I/NAV Ephemeris",
    1075: "GPS MSM5 Observation",
    1085: "GLONASS MSM5 Observation",
    1095: "Galileo MSM5 Observation",
    1115: "QZSS MSM5 Observation",
    1125: "BeiDou MSM5 Observation",
    1135: "NavIC/IRNSS MSM5 Observation",
    1230: "GLONASS Code-Phase Biases"
}


# ============================================================
# PROFESSIONAL CSS
# ============================================================

st.markdown(
    """
    <style>

    .stApp {
        background-color: #F4F6F8;
    }

    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }

    h1 {
        color: #12355B;
        font-weight: 700;
    }

    h2, h3 {
        color: #12355B;
        font-weight: 650;
    }

    .section-title {
        color: #12355B;
        font-size: 22px;
        font-weight: 700;
        border-left: 5px solid #1976D2;
        padding-left: 12px;
        margin-top: 20px;
        margin-bottom: 15px;
    }

    .card {
        background-color: white;
        border: 1px solid #D7DEE7;
        border-radius: 10px;
        padding: 18px;
        min-height: 105px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.06);
    }

    .card-title {
        color: #607080;
        font-size: 14px;
        margin-bottom: 8px;
    }

    .card-value {
        color: #12355B;
        font-size: 27px;
        font-weight: 700;
    }

    .status-active {
        color: #188038;
        font-weight: 700;
    }

    .status-inactive {
        color: #C62828;
        font-weight: 700;
    }

    .footer {
        text-align: center;
        color: #6B7785;
        font-size: 13px;
        margin-top: 30px;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# HEADER
# ============================================================

st.title("📡 GNSS / RTCM Live Monitoring Dashboard")

st.markdown(
    "Real-time monitoring of recorded GGA driven NTRIP correction data."
)

st.markdown("---")


# ============================================================
# LOAD RTCM DATA
# ============================================================

if os.path.exists(RTCM_FILE):

    try:
        df = pd.read_csv(RTCM_FILE)

    except Exception:
        df = pd.DataFrame()

else:

    df = pd.DataFrame()


# ============================================================
# LOAD GGA DATA
# ============================================================

if os.path.exists(GGA_FILE):

    try:
        gga_df = pd.read_csv(GGA_FILE)

    except Exception:
        gga_df = pd.DataFrame()

else:

    gga_df = pd.DataFrame()


# ============================================================
# BASIC RTCM INFORMATION
# ============================================================

if not df.empty:

    # Convert message ID to numeric
    df["RTCM_Message_ID"] = pd.to_numeric(
        df["RTCM_Message_ID"],
        errors="coerce"
    )

    df = df.dropna(
        subset=["RTCM_Message_ID"]
    )

    df["RTCM_Message_ID"] = (
        df["RTCM_Message_ID"]
        .astype(int)
    )


    # --------------------------------------------------------
    # Unique RTCM messages
    # --------------------------------------------------------

    unique_messages = sorted(
        df["RTCM_Message_ID"]
        .unique()
        .tolist()
    )


    # --------------------------------------------------------
    # Total RTCM records
    # --------------------------------------------------------

    total_messages = len(df)


    # --------------------------------------------------------
    # Active target messages
    # --------------------------------------------------------

    active_targets = sum(
        1
        for msg in TARGET_MESSAGES
        if msg in unique_messages
    )


    # --------------------------------------------------------
    # Inactive target messages
    # --------------------------------------------------------

    inactive_targets = (
        len(TARGET_MESSAGES)
        - active_targets
    )


    # --------------------------------------------------------
    # Message availability
    # --------------------------------------------------------

    availability = (
        active_targets
        / len(TARGET_MESSAGES)
        * 100
    )

else:

    unique_messages = []

    total_messages = 0

    active_targets = 0

    inactive_targets = len(
        TARGET_MESSAGES
    )

    availability = 0


# ============================================================
# LAST RTCM TIME
# ============================================================

last_rtcm_time = "Waiting for data"

if not df.empty and "Timestamp" in df.columns:

    try:

        # Convert timestamp if possible
        timestamp_series = pd.to_datetime(
            df["Timestamp"],
            errors="coerce"
        )

        if timestamp_series.notna().any():

            latest_index = timestamp_series.idxmax()

            last_rtcm_time = str(
                df.loc[latest_index, "Timestamp"]
            )

        else:

            last_rtcm_time = str(
                df["Timestamp"].iloc[-1]
            )

    except Exception:

        pass


# ============================================================
# GGA INFORMATION
# ============================================================

gga_count = len(gga_df)

if gga_count > 0:

    gga_status = "Recorded GGA Available"

else:

    gga_status = "GGA File Not Found"

# ============================================================
# SYSTEM OVERVIEW
# ============================================================

st.markdown(
    '<div class="section-title">System Overview</div>',
    unsafe_allow_html=True
)

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown(
        '<div class="card">'
        '<div class="card-title">System</div>'
        '<div class="card-value">GNSS / RTCM</div>'
        '</div>',
        unsafe_allow_html=True
    )

with c2:
    st.markdown(
        '<div class="card">'
        '<div class="card-title">Monitoring Mode</div>'
        '<div class="card-value">NTRIP</div>'
        '</div>',
        unsafe_allow_html=True
    )

with c3:
    st.markdown(
        '<div class="card">'
        '<div class="card-title">Target Message Types</div>'
        f'<div class="card-value">{len(TARGET_MESSAGES)}</div>'
        '</div>',
        unsafe_allow_html=True
    )

with c4:

    if total_messages > 0:
        status_text = "Active"
        status_class = "status-active"
    else:
        status_text = "Waiting"
        status_class = "status-inactive"

    st.markdown(
        '<div class="card">'
        '<div class="card-title">Monitoring Status</div>'
        f'<div class="card-value {status_class}">{status_text}</div>'
        '</div>',
        unsafe_allow_html=True
    )


# ============================================================
# KEY PERFORMANCE INDICATORS
# ============================================================

st.markdown(
    '<div class="section-title">Key Performance Indicators</div>',
    unsafe_allow_html=True
)

k1, k2, k3, k4 = st.columns(4)

with k1:
    st.markdown(
        '<div class="card">'
        '<div class="card-title">Active RTCM Messages</div>'
        f'<div class="card-value">{active_targets}</div>'
        '</div>',
        unsafe_allow_html=True
    )

with k2:
    st.markdown(
        '<div class="card">'
        '<div class="card-title">Inactive RTCM Messages</div>'
        f'<div class="card-value">{inactive_targets}</div>'
        '</div>',
        unsafe_allow_html=True
    )

with k3:
    st.markdown(
        '<div class="card">'
        '<div class="card-title">Total RTCM Messages</div>'
        f'<div class="card-value">{total_messages}</div>'
        '</div>',
        unsafe_allow_html=True
    )

with k4:
    st.markdown(
        '<div class="card">'
        '<div class="card-title">Message Availability</div>'
        f'<div class="card-value">{availability:.1f}%</div>'
        '</div>',
        unsafe_allow_html=True
    )

# ============================================================
# GGA STATUS
# ============================================================

st.markdown(
    '<div class="section-title">GGA Data Status</div>',
    unsafe_allow_html=True
)


g1, g2, g3 = st.columns(3)


with g1:

    st.metric(
        "Recorded GGA Messages",
        gga_count
    )


with g2:

    st.metric(
        "GGA Source",
        "gga_log.csv"
    )


with g3:

    st.metric(
        "RTCM Last Update",
        last_rtcm_time
    )


# ============================================================
# TARGET RTCM MESSAGE TABLE
# ============================================================

st.markdown(
    '<div class="section-title">RTCM Message Status</div>',
    unsafe_allow_html=True
)


rows = []


for message_id, description in TARGET_MESSAGES.items():

    if not df.empty:

        count = int(
            (
                df["RTCM_Message_ID"]
                == message_id
            ).sum()
        )

    else:

        count = 0


    if count > 0:

        status = "YES"

    else:

        status = "NO"


    rows.append(
        {
            "RTCM Message ID": message_id,
            "Description": description,
            "Status": status,
            "Count": count
        }
    )


target_df = pd.DataFrame(rows)


st.dataframe(
    target_df,
    use_container_width=True,
    hide_index=True,
    height=760,

    column_config={

        "RTCM Message ID":
            st.column_config.NumberColumn(
                "RTCM Message ID"
            ),

        "Description":
            st.column_config.TextColumn(
                "Description"
            ),

        "Status":
            st.column_config.TextColumn(
                "Status"
            ),

        "Count":
            st.column_config.NumberColumn(
                "Count"
            )
    }
)


# ============================================================
# ALL RTCM MESSAGE TYPES
# ============================================================

st.markdown(
    '<div class="section-title">All RTCM Messages Received</div>',
    unsafe_allow_html=True
)


if not df.empty:

    all_counts = (
        df[
            "RTCM_Message_ID"
        ]

        .value_counts()

        .sort_index()

        .reset_index()
    )


    all_counts.columns = [
        "RTCM Message ID",
        "Count"
    ]


    all_counts["Type"] = (
        all_counts[
            "RTCM Message ID"
        ]

        .apply(
            lambda x:

            "TARGET"
            if x in TARGET_MESSAGES
            else "OTHER"
        )
    )


    st.dataframe(
        all_counts,
        use_container_width=True,
        hide_index=True
    )


else:

    st.info(
        "Waiting for RTCM data from rtcm_monitor.py..."
    )


# ============================================================
# LATEST RTCM ACTIVITY
# ============================================================

st.markdown(
    '<div class="section-title">Latest RTCM Activity</div>',
    unsafe_allow_html=True
)


if not df.empty:

    recent_columns = [
        "Timestamp",
        "RTCM_Message_ID",
        "Description",
        "Count",
        "Message_Length",
        "Status"
    ]


    available_columns = [
        col
        for col in recent_columns
        if col in df.columns
    ]


    # --------------------------------------------------------
    # NEW LOGIC
    #
    # Find the newest RTCM batch using the highest Count.
    # Only that batch is displayed.
    #
    # Older counts are hidden.
    # --------------------------------------------------------

    if "Count" in df.columns:

        count_numeric = pd.to_numeric(
            df["Count"],
            errors="coerce"
        )


        if count_numeric.notna().any():

            latest_count = int(
                count_numeric.max()
            )


            latest_df = df[
                count_numeric
                == latest_count
            ].copy()


            # ------------------------------------------------
            # Sort newest timestamps first if available
            # ------------------------------------------------

            if "Timestamp" in latest_df.columns:

                timestamp_values = pd.to_datetime(
                    latest_df["Timestamp"],
                    errors="coerce"
                )

                latest_df["_sort_time"] = (
                    timestamp_values
                )

                latest_df = (
                    latest_df
                    .sort_values(
                        "_sort_time",
                        ascending=False
                    )
                    .drop(
                        columns=["_sort_time"]
                    )
                )


            recent_df = latest_df[
                available_columns
            ]


            st.caption(
                f"Showing latest RTCM batch only — Count: {latest_count}"
            )


            st.dataframe(
                recent_df,
                use_container_width=True,
                hide_index=True
            )


        else:

            # If Count cannot be interpreted,
            # show only the latest available record(s)

            recent_df = df[
                available_columns
            ].tail(1).iloc[::-1]


            st.dataframe(
                recent_df,
                use_container_width=True,
                hide_index=True
            )


    else:

        # If Count column does not exist,
        # show only the latest record

        recent_df = df[
            available_columns
        ].tail(1).iloc[::-1]


        st.dataframe(
            recent_df,
            use_container_width=True,
            hide_index=True
        )


else:

    st.info(
        "No RTCM activity available yet."
    )


# ============================================================
# FOOTER
# ============================================================

st.markdown("---")


st.markdown(
    f"""
    <div class="footer">

        GNSS / RTCM Monitoring System |

        Last dashboard refresh:
        {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

    </div>
    """,
    unsafe_allow_html=True
)


# ============================================================
# AUTO REFRESH
# ============================================================

time.sleep(3)

st.rerun()