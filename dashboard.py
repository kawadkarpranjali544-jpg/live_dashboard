import streamlit as st
import pandas as pd
import plotly.express as px

# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="GNSS RTCM Monitoring Dashboard",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="collapsed"
)


# ============================================================
# CUSTOM CSS - PROFESSIONAL OFFICE STYLE
# ============================================================

st.markdown("""
<style>

    /* -------------------- Overall Page -------------------- */

    .stApp {
        background-color: #F4F6F8;
        color: #1F2937;
    }

    .main .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
        max-width: 1500px;
    }


    /* -------------------- Header -------------------- */

    .dashboard-header {
        background: linear-gradient(
            90deg,
            #12355B 0%,
            #1E5A92 100%
        );

        padding: 22px 30px;
        border-radius: 10px;
        margin-bottom: 25px;

        box-shadow:
            0 3px 10px rgba(0,0,0,0.08);
    }

    .dashboard-title {
        color: white;
        font-size: 30px;
        font-weight: 700;
        margin-bottom: 5px;
    }

    .dashboard-subtitle {
        color: #DCE8F5;
        font-size: 15px;
        margin-top: 0px;
    }


    /* -------------------- KPI Cards -------------------- */

    div[data-testid="stMetric"] {

        background-color: white;

        border: 1px solid #D9E0E7;

        border-radius: 10px;

        padding: 18px;

        box-shadow:
            0 2px 7px rgba(0,0,0,0.06);

        min-height: 110px;
    }

    div[data-testid="stMetricLabel"] {
        color: #64748B !important;
        font-size: 14px !important;
        font-weight: 600 !important;
    }

    div[data-testid="stMetricValue"] {
        color: #12355B !important;
        font-size: 30px !important;
        font-weight: 700 !important;
    }


    /* -------------------- Section Headers -------------------- */

    .section-title {
        color: #12355B;
        font-size: 21px;
        font-weight: 700;

        border-left: 5px solid #1E73BE;

        padding-left: 12px;

        margin-top: 25px;
        margin-bottom: 15px;
    }


    /* -------------------- Information Cards -------------------- */

    .info-card {

        background-color: white;

        border: 1px solid #D9E0E7;

        border-radius: 9px;

        padding: 15px 18px;

        margin-bottom: 10px;

        box-shadow:
            0 2px 6px rgba(0,0,0,0.04);
    }

    .info-label {
        color: #64748B;
        font-size: 13px;
        font-weight: 600;
    }

    .info-value {
        color: #12355B;
        font-size: 18px;
        font-weight: 700;
    }


    /* -------------------- Tables -------------------- */

    thead tr th {
        background-color: #12355B !important;
        color: white !important;
        text-align: center !important;
        font-weight: 600 !important;
    }

    tbody tr:hover {
        background-color: #F1F6FB !important;
    }


    /* -------------------- Status -------------------- */

    .status-active {

        background-color: #E8F5E9;

        color: #2E7D32;

        padding: 5px 12px;

        border-radius: 15px;

        font-weight: 600;
    }

    .status-inactive {

        background-color: #FDECEC;

        color: #C62828;

        padding: 5px 12px;

        border-radius: 15px;

        font-weight: 600;
    }


    /* -------------------- Footer -------------------- */

    .footer {

        text-align: center;

        color: #64748B;

        font-size: 12px;

        padding-top: 25px;

        margin-top: 30px;

        border-top: 1px solid #D9E0E7;
    }

</style>
""", unsafe_allow_html=True)


# ============================================================
# HEADER
# ============================================================

st.markdown("""
<div class="dashboard-header">

    <div class="dashboard-title">
        GNSS RTCM Monitoring Dashboard
    </div>

    <div class="dashboard-subtitle">
        Real-Time GNSS Correction Message Monitoring and Analysis
    </div>

</div>
""", unsafe_allow_html=True)


# ============================================================
# DATA
# ============================================================

table1 = pd.DataFrame({

    "RTCM Message ID": [
        1006, 1008, 1019, 1020, 1029,
        1033, 1042, 1046, 1075, 1095, 1125
    ],

    "Description": [
        "Station ARP / Reference Station Position",
        "Reference Station Antenna Information",
        "GPS Satellite Ephemeris",
        "GLONASS Satellite Ephemeris",
        "Unicode Text / Broadcast Message",
        "Receiver / Antenna Descriptor",
        "BeiDou Satellite Ephemeris",
        "Galileo Satellite Ephemeris",
        "GPS MSM5 Observation Corrections",
        "QZSS MSM5 Observation Corrections",
        "BeiDou MSM5 Observation Corrections"
    ],

    "Status": [
        "YES", "YES", "YES", "YES", "YES",
        "YES", "YES", "YES", "YES", "YES", "YES"
    ],

    "Count": [
        69, 69, 62, 18, 3,
        69, 62, 60, 69, 69, 69
    ]

})


table2 = pd.DataFrame({

    "RTCM Message ID": [
        1006, 1008, 1019, 1020, 1029,
        1033, 1042, 1046, 1075, 1095, 1125
    ],

    "Description": [
        "Station ARP / Reference Station Position",
        "Reference Station Antenna Information",
        "GPS Satellite Ephemeris",
        "GLONASS Satellite Ephemeris",
        "Unicode Text / Broadcast Message",
        "Receiver / Antenna Descriptor",
        "BeiDou Satellite Ephemeris",
        "Galileo Satellite Ephemeris",
        "GPS MSM5 Observation Corrections",
        "QZSS MSM5 Observation Corrections",
        "BeiDou MSM5 Observation Corrections"
    ],

    "Status": [
        "YES", "YES", "YES", "YES", "YES",
        "YES", "YES", "YES", "NO", "NO", "NO"
    ],

    "Count": [
        47, 47, 31, 1, 2,
        47, 38, 47, 0, 0, 0
    ]

})


# ============================================================
# KPI CALCULATIONS
# ============================================================

total_yes = (
    table2["Status"] == "YES"
).sum()

total_no = (
    table2["Status"] == "NO"
).sum()

total_messages = (
    table2["Count"].sum()
)

total_message_types = len(table2)

availability = (
    total_yes / total_message_types
) * 100


# ============================================================
# SYSTEM INFORMATION
# ============================================================

st.markdown(
    '<div class="section-title">System Overview</div>',
    unsafe_allow_html=True
)

info1, info2, info3, info4 = st.columns(4)

with info1:

    st.markdown("""
    <div class="info-card">
        <div class="info-label">System</div>
        <div class="info-value">GNSS / RTCM</div>
    </div>
    """, unsafe_allow_html=True)


with info2:

    st.markdown("""
    <div class="info-card">
        <div class="info-label">Monitoring Mode</div>
        <div class="info-value">NTRIP</div>
    </div>
    """, unsafe_allow_html=True)


with info3:

    st.markdown("""
    <div class="info-card">
        <div class="info-label">Target Message Types</div>
        <div class="info-value">11</div>
    </div>
    """, unsafe_allow_html=True)


with info4:

    st.markdown("""
    <div class="info-card">
        <div class="info-label">Monitoring Status</div>
        <div class="info-value">Active</div>
    </div>
    """, unsafe_allow_html=True)


# ============================================================
# KPI CARDS
# ============================================================

st.markdown(
    '<div class="section-title">Key Performance Indicators</div>',
    unsafe_allow_html=True
)

c1, c2, c3, c4 = st.columns(4)


c1.metric(
    "Active RTCM Messages",
    total_yes
)

c2.metric(
    "Inactive RTCM Messages",
    total_no
)

c3.metric(
    "Total Message Count",
    total_messages
)

c4.metric(
    "Message Availability",
    f"{availability:.1f}%"
)


# ============================================================
# SESSION 1
# ============================================================

st.markdown(
    '<div class="section-title">RTCM Message Summary — Session 1</div>',
    unsafe_allow_html=True
)

st.dataframe(
    table1,
    use_container_width=True,
    hide_index=True,
    height=430,
    column_config={

        "RTCM Message ID":
            st.column_config.NumberColumn(
                "RTCM Message ID"
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
# SESSION 2
# ============================================================

st.markdown(
    '<div class="section-title">RTCM Message Summary — Session 2</div>',
    unsafe_allow_html=True
)

st.dataframe(
    table2,
    use_container_width=True,
    hide_index=True,
    height=430,
    column_config={

        "RTCM Message ID":
            st.column_config.NumberColumn(
                "RTCM Message ID"
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
# MESSAGE COUNT CHART
# ============================================================

st.markdown(
    '<div class="section-title">RTCM Message Distribution</div>',
    unsafe_allow_html=True
)

chart_data = table2.copy()

chart_data["RTCM Message ID"] = (
    chart_data["RTCM Message ID"].astype(str)
)

fig = px.bar(

    chart_data,

    x="RTCM Message ID",

    y="Count",

    text="Count",

    title="RTCM Message Counts — Session 2",

    labels={
        "RTCM Message ID": "RTCM Message Type",
        "Count": "Number of Messages"
    }
)

fig.update_layout(

    paper_bgcolor="white",

    plot_bgcolor="white",

    font=dict(
        color="#1F2937"
    ),

    title_font=dict(
        size=18,
        color="#12355B"
    ),

    xaxis=dict(
        showgrid=False
    ),

    yaxis=dict(
        gridcolor="#E5E7EB"
    ),

    margin=dict(
        l=30,
        r=30,
        t=60,
        b=30
    )
)

fig.update_traces(
    textposition="outside"
)

st.plotly_chart(
    fig,
    use_container_width=True
)


# ============================================================
# STATUS ANALYSIS
# ============================================================

st.markdown(
    '<div class="section-title">Message Availability Analysis</div>',
    unsafe_allow_html=True
)

analysis_col1, analysis_col2 = st.columns(2)


with analysis_col1:

    active_messages = table2[
        table2["Status"] == "YES"
    ]

    st.markdown(
        "### Available RTCM Messages"
    )

    st.dataframe(
        active_messages[
            [
                "RTCM Message ID",
                "Count"
            ]
        ],
        use_container_width=True,
        hide_index=True
    )


with analysis_col2:

    inactive_messages = table2[
        table2["Status"] == "NO"
    ]

    st.markdown(
        "### Unavailable RTCM Messages"
    )

    st.dataframe(
        inactive_messages[
            [
                "RTCM Message ID",
                "Count"
            ]
        ],
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# PROJECT STATUS
# ============================================================

st.markdown(
    '<div class="section-title">Project Status</div>',
    unsafe_allow_html=True
)

if total_no == 0:

    st.success(
        "All monitored RTCM message types are currently available."
    )

else:

    st.warning(
        f"{total_no} monitored RTCM message type(s) "
        "are currently unavailable in Session 2."
    )


# ============================================================
# FOOTER
# ============================================================

st.markdown("""
<div class="footer">

GNSS RTCM Monitoring System &nbsp; | &nbsp;
NTRIP Correction Stream Analysis &nbsp; | &nbsp;
RTCM Message Monitoring

</div>
""", unsafe_allow_html=True)