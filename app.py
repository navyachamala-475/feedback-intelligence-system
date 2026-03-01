
import os
import sys
import logging
import io
from datetime import datetime, timedelta, date

import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import APP_NAME, APP_VERSION, REPORTS_DIR, COMPANY_NAME, TARGET_APPS
from data_pipeline import DataPipeline
from analysis import IssueDetector, TrendAnalyzer
from reporting import generate_pdf_report

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="Feedback Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
    .main { background: #F8FAFC; }
    .kpi-card {
        background: white; border-radius: 16px; padding: 20px 24px;
        border: 1px solid #E2E8F0; box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    .kpi-label { font-size: 12px; font-weight: 600; color: #64748B; text-transform: uppercase; }
    .kpi-value { font-size: 32px; font-weight: 700; color: #0F172A; line-height: 1.2; margin: 4px 0; }
    .review-card {
        background: white; border-radius: 12px; padding: 16px;
        border: 1px solid #E2E8F0; margin-bottom: 8px;
    }
    .review-body { color: #334155; font-size: 14px; line-height: 1.6; }
    .review-meta { color: #94A3B8; font-size: 12px; margin-top: 8px; }
    .badge-gp  { background:#DBEAFE; color:#1D4ED8; padding:2px 10px; border-radius:12px; font-size:11px; font-weight:600; }
    .badge-as  { background:#D1FAE5; color:#065F46; padding:2px 10px; border-radius:12px; font-size:11px; font-weight:600; }
    .badge-csv { background:#FEF3C7; color:#92400E; padding:2px 10px; border-radius:12px; font-size:11px; font-weight:600; }
    .chip-pos  { background:#DCFCE7; color:#15803D; padding:2px 10px; border-radius:12px; font-size:11px; }
    .chip-neg  { background:#FEE2E2; color:#B91C1C; padding:2px 10px; border-radius:12px; font-size:11px; }
    .chip-neu  { background:#F1F5F9; color:#475569; padding:2px 10px; border-radius:12px; font-size:11px; }
    [data-testid="stSidebar"] { background: #0F172A !important; }
    [data-testid="stSidebar"] * { color: #CBD5E1 !important; }
    #MainMenu, footer, header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def get_pipeline():
    return DataPipeline()

@st.cache_data(ttl=3600, show_spinner=False)
def load_data(use_cache=True, csv_path=None):
    pipeline = get_pipeline()
    return pipeline.load_data(use_cache=use_cache, csv_path=csv_path)

def source_badge_html(source):
    css = {"Google Play": "badge-gp", "App Store": "badge-as"}.get(source, "badge-csv")
    return f'<span class="{css}">{source}</span>'

def sentiment_chip_html(label):
    css = {"Positive": "chip-pos", "Negative": "chip-neg"}.get(label, "chip-neu")
    return f'<span class="{css}">{label}</span>'


with st.sidebar:
    st.markdown("""
    <div style="padding:16px 0 24px;">
        <div style="font-size:22px;font-weight:800;color:white;">📊 FeedbackIQ</div>
        <div style="font-size:12px;color:#475569;">Feedback Intelligence System</div>
    </div>
    """, unsafe_allow_html=True)

    page = st.radio("", ["📈 Overview","🔍 Reviews Explorer","⚠️ Issues & Alerts","📉 Trend Analysis","📄 PDF Report"],
                    label_visibility="collapsed")

    st.markdown("---")
    today = date.today()
    date_from = st.date_input("From", value=today - timedelta(days=30))
    date_to   = st.date_input("To",   value=today)
    sources_filter   = st.multiselect("Sources",   ["Google Play","App Store","CSV Survey"], default=["Google Play","App Store","CSV Survey"])
    sentiment_filter = st.multiselect("Sentiment", ["Positive","Negative","Neutral"],        default=["Positive","Negative","Neutral"])
    rating_range     = st.slider("Rating", 1, 5, (1, 5))

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Refresh"):
            st.cache_data.clear()
            st.rerun()
    with col2:
        uploaded = st.file_uploader("+ CSV", type=["csv"], label_visibility="collapsed")

    if uploaded:
        csv_tmp = os.path.join(REPORTS_DIR, "uploaded_survey.csv")
        os.makedirs(REPORTS_DIR, exist_ok=True)
        with open(csv_tmp, "wb") as f:
            f.write(uploaded.read())
        st.success(f"✓ {uploaded.name}")
        st.session_state["uploaded_csv"] = csv_tmp


with st.spinner("Loading data from all sources..."):
    csv_path = st.session_state.get("uploaded_csv", None)
    df_all = load_data(use_cache=True, csv_path=csv_path)

df = df_all.copy()
df["date"] = pd.to_datetime(df["date"])
df = df[
    (df["date"].dt.date >= date_from) &
    (df["date"].dt.date <= date_to) &
    (df["source"].isin(sources_filter) if sources_filter else True) &
    (df["sentiment_label"].isin(sentiment_filter) if sentiment_filter else True) &
    (df["rating"] >= rating_range[0]) &
    (df["rating"] <= rating_range[1])
]

issue_det       = IssueDetector()
trend_ana       = TrendAnalyzer()
issue_summary   = issue_det.get_issue_summary(df)
daily_sentiment = trend_ana.get_daily_sentiment(df)
trend_directions= trend_ana.get_trend_direction(df)


if page == "📈 Overview":
    st.markdown('<h1 style="font-size:28px;font-weight:800;color:#0F172A;">Feedback Overview</h1>', unsafe_allow_html=True)

    if df.empty:
        st.warning("No data matches filters.")
        st.stop()

    k1,k2,k3,k4,k5 = st.columns(5)
    pos_pct = (df["sentiment_label"]=="Positive").sum()/len(df)*100
    neg_pct = (df["sentiment_label"]=="Negative").sum()/len(df)*100
    critical_count = issue_summary["is_critical"].sum() if not issue_summary.empty else 0

    for col, label, value in [
        (k1,"Total Reviews",f"{len(df):,}"),
        (k2,"Avg Rating",f"{df['rating'].mean():.2f} ⭐"),
        (k3,"Positive",f"{pos_pct:.1f}%"),
        (k4,"Negative",f"{neg_pct:.1f}%"),
        (k5,"Critical Issues",str(int(critical_count))),
    ]:
        col.markdown(f'<div class="kpi-card"><div class="kpi-label">{label}</div><div class="kpi-value">{value}</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    col_left, col_right = st.columns([1,2])

    with col_left:
        st.markdown("### 📊 Sentiment Split")
        sent_counts = df["sentiment_label"].value_counts()
        fig_donut = go.Figure(go.Pie(
            labels=sent_counts.index, values=sent_counts.values, hole=0.6,
            marker_colors=["#10B981","#EF4444","#94A3B8"], textinfo="percent",
        ))
        fig_donut.update_layout(height=280, margin=dict(t=0,b=40,l=0,r=0),
                                 paper_bgcolor="white", plot_bgcolor="white")
        st.plotly_chart(fig_donut, use_container_width=True, config={"displayModeBar":False})

    with col_right:
        st.markdown("### 📈 Sentiment Trend")
        if not daily_sentiment.empty:
            fig_line = px.line(daily_sentiment, x="date", y="avg_sentiment", color="source",
                               color_discrete_map={"Google Play":"#3B82F6","App Store":"#10B981","CSV Survey":"#F59E0B"},
                               markers=True)
            fig_line.add_hline(y=0, line_dash="dot", line_color="#94A3B8")
            fig_line.update_layout(height=280, paper_bgcolor="white", plot_bgcolor="#F8FAFC",
                                    margin=dict(t=8,b=8,l=8,r=8))
            st.plotly_chart(fig_line, use_container_width=True, config={"displayModeBar":False})

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("### ⭐ Rating Distribution")
        df["rating_int"] = df["rating"].round().clip(1,5).astype(int)
        rating_dist = df.groupby(["source","rating_int"]).size().reset_index(name="count")
        fig_bar = px.bar(rating_dist, x="rating_int", y="count", color="source", barmode="group",
                         color_discrete_map={"Google Play":"#3B82F6","App Store":"#10B981","CSV Survey":"#F59E0B"})
        fig_bar.update_layout(height=260, paper_bgcolor="white", plot_bgcolor="#F8FAFC",
                               xaxis=dict(tickvals=[1,2,3,4,5],ticktext=["1★","2★","3★","4★","5★"]),
                               margin=dict(t=8,b=8,l=8,r=8))
        st.plotly_chart(fig_bar, use_container_width=True, config={"displayModeBar":False})

    with col_b:
        st.markdown("### 📦 Volume by Source")
        vol = df.groupby("source").agg(count=("review_id","count")).reset_index()
        fig_vol = px.bar(vol, x="source", y="count", color="source", text="count",
                         color_discrete_map={"Google Play":"#3B82F6","App Store":"#10B981","CSV Survey":"#F59E0B"})
        fig_vol.update_traces(textposition="outside")
        fig_vol.update_layout(height=260, showlegend=False, paper_bgcolor="white",
                               plot_bgcolor="#F8FAFC", margin=dict(t=8,b=8,l=8,r=8))
        st.plotly_chart(fig_vol, use_container_width=True, config={"displayModeBar":False})


elif page == "🔍 Reviews Explorer":
    st.markdown('<h1 style="font-size:28px;font-weight:800;color:#0F172A;">Reviews Explorer</h1>', unsafe_allow_html=True)
    search  = st.text_input("🔍 Search reviews...", placeholder="Type keywords...")
    sort_by = st.selectbox("Sort by", ["Most Recent","Most Negative","Most Positive","Highest Rating","Lowest Rating"])
    sort_map = {"Most Recent":("date",False),"Most Negative":("compound",True),
                "Most Positive":("compound",False),"Highest Rating":("rating",False),"Lowest Rating":("rating",True)}

    df_view = df.copy()
    if search:
        mask = df_view["body"].str.contains(search,case=False,na=False) | df_view["title"].str.contains(search,case=False,na=False)
        df_view = df_view[mask]

    sort_col, sort_asc = sort_map[sort_by]
    df_view = df_view.sort_values(sort_col, ascending=sort_asc)

    PAGE_SIZE   = 20
    total_pages = max(1,(len(df_view)-1)//PAGE_SIZE+1)
    page_num    = st.number_input("Page",1,total_pages,1)
    page_df     = df_view.iloc[(page_num-1)*PAGE_SIZE:page_num*PAGE_SIZE]

    for _, row in page_df.iterrows():
        badge = source_badge_html(row["source"])
        sent  = sentiment_chip_html(row["sentiment_label"])
        body  = str(row["body"])[:400]
        date_str = row["date"].strftime("%b %d, %Y") if pd.notna(row["date"]) else ""
        st.markdown(f"""
        <div class="review-card">
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
                {badge} {sent}
                <span style="color:#94A3B8;font-size:12px;">⭐{row['rating']:.0f} · {date_str} · {row['author']}</span>
            </div>
            <div class="review-body">{body}</div>
            <div class="review-meta">Sentiment: <b>{row['compound']:.3f}</b> · Confidence: <b>{row.get('confidence',0):.1%}</b></div>
        </div>""", unsafe_allow_html=True)


elif page == "⚠️ Issues & Alerts":
    st.markdown('<h1 style="font-size:28px;font-weight:800;color:#0F172A;">Issues & Alerts</h1>', unsafe_allow_html=True)

    if issue_summary.empty:
        st.info("No issues detected.")
    else:
        critical = issue_summary[issue_summary["is_critical"]==True]

        if not critical.empty:
            st.markdown(f"""
            <div style="background:#FEF2F2;border:1px solid #FECACA;border-radius:12px;padding:16px 20px;margin-bottom:16px;">
                <div style="font-size:16px;font-weight:700;color:#DC2626;">🚨 {len(critical)} Critical Issue(s) Detected</div>
            </div>""", unsafe_allow_html=True)

        fig_bubble = px.scatter(issue_summary, x="avg_sentiment", y="neg_ratio",
                                size="mention_count", color="is_critical",
                                color_discrete_map={True:"#EF4444",False:"#3B82F6"},
                                hover_name="category", size_max=50)
        fig_bubble.add_vline(x=0, line_dash="dash", line_color="#94A3B8")
        fig_bubble.add_hline(y=0.6, line_dash="dash", line_color="#F59E0B")
        fig_bubble.update_layout(height=400, paper_bgcolor="white", plot_bgcolor="#F8FAFC")
        st.plotly_chart(fig_bubble, use_container_width=True, config={"displayModeBar":False})

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### 🔴 Critical Issues")
            if not critical.empty:
                for _, row in critical.iterrows():
                    st.markdown(f"""
                    <div style="background:#FEF2F2;border-left:4px solid #EF4444;border-radius:8px;padding:12px 16px;margin-bottom:8px;">
                        <div style="font-weight:700;">{row['category']}</div>
                        <div style="color:#64748B;font-size:12px;">{int(row['mention_count'])} mentions · {row['neg_ratio']*100:.1f}% negative</div>
                    </div>""", unsafe_allow_html=True)
            else:
                st.success("✅ No critical issues!")

        with col2:
            st.markdown("### 🟡 All Issues")
            display_df = issue_summary[["category","mention_count","neg_ratio","avg_sentiment"]].copy()
            display_df["neg_ratio"] = (display_df["neg_ratio"]*100).round(1).astype(str)+"%"
            display_df.columns = ["Category","Mentions","Neg %","Avg Sentiment"]
            st.dataframe(display_df, use_container_width=True, hide_index=True)


elif page == "📉 Trend Analysis":
    st.markdown('<h1 style="font-size:28px;font-weight:800;color:#0F172A;">Trend Analysis</h1>', unsafe_allow_html=True)

    if df.empty or daily_sentiment.empty:
        st.warning("Not enough data.")
        st.stop()

    metric = st.selectbox("Metric", ["avg_sentiment","avg_rating","positive_pct","negative_pct","review_count"])
    fig_trend = px.line(daily_sentiment, x="date", y=metric, color="source",
                        color_discrete_map={"Google Play":"#3B82F6","App Store":"#10B981","CSV Survey":"#F59E0B"},
                        markers=True, line_shape="spline")
    fig_trend.update_layout(height=380, paper_bgcolor="white", plot_bgcolor="#F8FAFC")
    st.plotly_chart(fig_trend, use_container_width=True, config={"displayModeBar":False})

    st.markdown("### 💬 Top Words")
    wc1, wc2 = st.columns(2)
    with wc1:
        st.markdown("**Negative Reviews**")
        neg_words = trend_ana.get_top_words(df, sentiment="Negative", top_n=15)
        if neg_words:
            wdf = pd.DataFrame(neg_words, columns=["Word","Count"])
            fig = px.bar(wdf, x="Count", y="Word", orientation="h", color_discrete_sequence=["#EF4444"])
            fig.update_layout(height=350, paper_bgcolor="white", plot_bgcolor="#F8FAFC",
                              yaxis=dict(categoryorder="total ascending"), margin=dict(t=0,b=0))
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})

    with wc2:
        st.markdown("**Positive Reviews**")
        pos_words = trend_ana.get_top_words(df, sentiment="Positive", top_n=15)
        if pos_words:
            wdf = pd.DataFrame(pos_words, columns=["Word","Count"])
            fig = px.bar(wdf, x="Count", y="Word", orientation="h", color_discrete_sequence=["#10B981"])
            fig.update_layout(height=350, paper_bgcolor="white", plot_bgcolor="#F8FAFC",
                              yaxis=dict(categoryorder="total ascending"), margin=dict(t=0,b=0))
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})


elif page == "📄 PDF Report":
    st.markdown('<h1 style="font-size:28px;font-weight:800;color:#0F172A;">PDF Report Generator</h1>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        report_app     = st.text_input("App Name", value=TARGET_APPS["google_play"]["app_name"])
        report_company = st.text_input("Company Name", value=COMPANY_NAME)
    with col2:
        st.markdown("**Report includes:**")
        st.markdown("✓ Executive Summary\n✓ KPI Table\n✓ Sentiment Charts\n✓ Critical Issues\n✓ Sample Reviews")

    if st.button("🔃 Generate PDF Report"):
        if df.empty:
            st.error("No data available.")
        else:
            with st.spinner("Generating PDF..."):
                try:
                    ts       = datetime.now().strftime("%Y%m%d_%H%M")
                    out_path = os.path.join(REPORTS_DIR, f"feedback_report_{ts}.pdf")
                    os.makedirs(REPORTS_DIR, exist_ok=True)
                    generate_pdf_report(
                        df=df, issue_summary=issue_summary,
                        trend_data=daily_sentiment, output_path=out_path,
                        app_name=report_app, company=report_company,
                    )
                    with open(out_path,"rb") as f:
                        pdf_bytes = f.read()
                    st.success("✅ Report generated!")
                    st.download_button("⬇️ Download PDF", data=pdf_bytes,
                                       file_name=f"feedback_report_{ts}.pdf", mime="application/pdf")
                except Exception as e:
                    st.error(f"Failed: {e}")