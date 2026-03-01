# Feedback Intelligence System 📊

A production-style multi-source feedback analytics dashboard that aggregates reviews from Google Play Store, Apple App Store, and CSV surveys with AI-powered sentiment analysis, trend detection, issue prioritization, and PDF report generation.

## 🚀 How to Run

### 1. Install dependencies
pip install -r requirements.txt

### 2. Run the dashboard
streamlit run app.py

Open browser at http://localhost:8501

## 📁 Project Structure

feedback_intelligence/
├── app.py                      # Main Streamlit dashboard
├── config.py                   # Configuration
├── data_pipeline.py            # Data orchestration
├── requirements.txt
├── fetchers/
│   ├── google_play_fetcher.py  # Google Play reviews
│   ├── app_store_fetcher.py    # App Store reviews
│   └── csv_fetcher.py          # CSV survey loader
├── analysis/
│   ├── sentiment_analyzer.py   # VADER sentiment analysis
│   └── issue_detector.py       # Issue detection + trends
└── reporting/
    └── pdf_reporter.py         # PDF report generation

## ✨ Features

- Multi-Source Integration: Google Play, App Store, CSV
- Sentiment Analysis: VADER with confidence scores
- Trend Detection: Daily trends and rolling averages
- Issue Prioritization: 10 categories with critical flagging
- Streamlit Dashboard: 5 pages with filters
- PDF Reports: Professional weekly reports
- Demo Mode: 300 realistic reviews if APIs unavailable

## 📊 Dashboard Pages

1. Overview - KPI cards, sentiment charts, trends
2. Reviews Explorer - Search and filter reviews
3. Issues and Alerts - Critical issue detection
4. Trend Analysis - Time series and word frequency
5. PDF Report - Generate stakeholder reports

## 🔧 Tech Stack

- Streamlit - Dashboard UI
- VADER Sentiment - Sentiment analysis
- Plotly - Interactive charts
- ReportLab - PDF generation
- Pandas - Data processing
- Google Play Scraper - Play Store reviews
- App Store Scraper - App Store reviews

## 📦 Requirements

- Python 3.10 or higher
- All dependencies in requirements.txt

## 👩‍💻 Built By

Navya Chamala
Feedback Intelligence System v1.0
