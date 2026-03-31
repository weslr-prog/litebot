"""
Phase 3A Real-Time Dashboard
Shows Enhanced Regime Detection + Signal Confidence in action
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta

# Import your Phase 3A systems
from core.regime_detector import RegimeDetector
from core.signal_confidence import SignalConfidenceScorer

def main():
    st.set_page_config(
        page_title="Phase 3A Enhanced Trading System",
        page_icon="🚀",
        layout="wide"
    )
    
    st.title("🚀 Phase 3A Enhanced Trading System")
    st.markdown("**Enhanced Regime Detection + ML Signal Confidence**")
    
    # Sidebar
    st.sidebar.header("Settings")
    symbol = st.sidebar.text_input("Stock Symbol", value="AAPL")
    period = st.sidebar.selectbox("Period", ["1mo", "3mo", "6mo", "1y"], index=3)
    
    if st.sidebar.button("Analyze"):
        with st.spinner(f"Analyzing {symbol}..."):
            analyze_stock(symbol, period)

def analyze_stock(symbol, period):
    """Analyze stock with Phase 3A systems"""
    
    try:
        # Get data
        ticker = yf.Ticker(symbol)
        data = ticker.history(period=period)
        
        if data.empty:
            st.error(f"No data found for {symbol}")
            return
        
        # Convert format
        stock_data = pd.DataFrame({
            'close': data['Close'],
            'high': data['High'],
            'low': data['Low'], 
            'volume': data['Volume']
        })
        
        # Initialize systems
        regime_detector = RegimeDetector()
        confidence_scorer = SignalConfidenceScorer()
        
        # Analysis
        regime = regime_detector.detect_regime(stock_data)
        regime_score = 0.8 if regime == 'bullish' else (0.7 if regime == 'volatile' else 0.3)
        
        features = confidence_scorer.extract_features(stock_data, 0.02, regime_score)
        confidence = confidence_scorer.calculate_confidence(features)
        
        # Display results
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Regime", regime.upper(), 
                     f"Score: {regime_score:.1%}")
        
        with col2:
            st.metric("Confidence", f"{confidence.overall_confidence:.1%}",
                     confidence.recommendation)
        
        with col3:
            st.metric("Current Price", f"${stock_data['close'].iloc[-1]:.2f}",
                     f"{features.momentum_21d:.1%}")
        
        # Detailed metrics
        st.subheader("📊 Detailed Analysis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Signal Components:**")
            st.write(f"• Momentum Strength: {confidence.momentum_strength:.1%}")
            st.write(f"• Regime Alignment: {confidence.regime_alignment:.1%}")
            st.write(f"• Technical Quality: {confidence.technical_quality:.1%}")
            st.write(f"• Risk Assessment: {confidence.risk_assessment:.1%}")
        
        with col2:
            st.markdown("**Market Features:**")
            st.write(f"• 21d Momentum: {features.momentum_21d:.1%}")
            st.write(f"• Volatility: {features.volatility_21d:.1%}")
            st.write(f"• Volume Ratio: {features.volume_ratio:.2f}")
            st.write(f"• Price vs 52w High: {features.price_vs_52w_high:.1%}")
        
        # Chart
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=data.index,
            y=data['Close'],
            mode='lines',
            name='Price',
            line=dict(color='blue')
        ))
        
        fig.update_layout(
            title=f"{symbol} Price Chart with Regime: {regime.upper()}",
            xaxis_title="Date",
            yaxis_title="Price ($)",
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Trading signal
        signal_color = {
            'STRONG_BUY': '🟢',
            'BUY': '🟡', 
            'HOLD': '⚪',
            'WEAK': '🔴'
        }.get(confidence.recommendation, '⚪')
        
        st.markdown(f"### {signal_color} Trading Signal: **{confidence.recommendation}**")
        st.markdown(f"**Confidence Level: {confidence.overall_confidence:.1%}**")
        
    except Exception as e:
        st.error(f"Error analyzing {symbol}: {e}")

if __name__ == "__main__":
    st.markdown("## 🔧 Setup Instructions")
    st.markdown("To run this dashboard:")
    st.code("pip install streamlit plotly")
    st.code("streamlit run phase3_dashboard.py")
    st.markdown("---")
    main()
