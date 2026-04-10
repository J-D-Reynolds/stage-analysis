import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go

@st.cache_data(ttl=86400) # strictly cache for 1 day
def get_sp500_tickers():
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    # Wikipedia blocks default python agents, so we spoof a standard browser via storage_options
    tables = pd.read_html(url, storage_options={'User-Agent': 'Mozilla/5.0'})
    df = tables[0]
    tickers = df['Symbol'].tolist()
    # Clean tickers for yfinance compatibility (e.g. BRK.B -> BRK-B)
    tickers = sorted([t.replace('.', '-') for t in tickers])
    return tickers

# Set page layout to wide and dark mode (Streamlit defaults to matching system, but we configure layout)
st.set_page_config(
    page_title="Algorithmic Trading Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Sidebar settings
with st.sidebar:
    st.title("Antigravity Trading")
    
    # Stock Choice
    sp500_options = get_sp500_tickers()
    stock_options = sp500_options + ["Custom..."]
    
    # Safely assign AAPL as the default selection
    default_index = stock_options.index("AAPL") if "AAPL" in stock_options else 0
    ticker_choice = st.selectbox("Select S&P 500 Ticker", options=stock_options, index=default_index)
    
    if ticker_choice == "Custom...":
        ticker = st.text_input("Enter Custom Ticker", value="AMD").upper()
    else:
        ticker = ticker_choice
        
    period = st.selectbox("Visual Time Period", options=["1mo", "3mo", "6mo", "1y", "2y", "5y", "max"], index=3)
    st.button("Deploy Strategy", type="primary")

st.title(f"{ticker} / USD - Interactive Chart")

# Fetch data
@st.cache_data(ttl=3600)  # highly robust data loader cache
def load_data(ticker):
    # Always fetch 'max' data so our 200 Moving Average has enough historical data to calculate accurately
    df = yf.download(ticker, period="max", interval="1d", progress=False)
    if not df.empty:
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        # Calculate original request 200-day moving average
        df['200_DMA'] = df['Close'].rolling(window=200).mean()
        
        # Calculate Weinstein Stage Analysis (150-day = 30-week MA)
        df['150_DMA'] = df['Close'].rolling(window=150).mean()
        # 20-day rate of change of the 150-DMA to determine direction
        df['150_DMA_slope'] = df['150_DMA'].diff(20)
        
        # Identify Stages mathematically
        df['Stage'] = 0
        stage_2 = (df['Close'] > df['150_DMA']) & (df['150_DMA_slope'] > 0)
        stage_4 = (df['Close'] < df['150_DMA']) & (df['150_DMA_slope'] < 0)
        
        df.loc[stage_2, 'Stage'] = 2
        df.loc[stage_4, 'Stage'] = 4
        
        # Tag contiguous blocks so Plotly can draw distinct background rectangles
        df['Stage_Group'] = (df['Stage'] != df['Stage'].shift(1)).cumsum()
    return df

with st.spinner(f"Fetching data for {ticker}..."):
    full_df = load_data(ticker)

if full_df.empty:
    st.error(f"No data found for {ticker}")
else:
    # Filter dataframe down to the user's requested visual period
    if period != "max":
        # Convert period string to pandas DateOffset
        period_map = {
            "1mo": pd.DateOffset(months=1),
            "3mo": pd.DateOffset(months=3),
            "6mo": pd.DateOffset(months=6),
            "1y": pd.DateOffset(years=1),
            "2y": pd.DateOffset(years=2),
            "5y": pd.DateOffset(years=5),
        }
        start_date = full_df.index.max() - period_map[period]
        df = full_df[full_df.index >= start_date]
    else:
        df = full_df

    # Build a gorgeous Plotly interactive candlestick chart
    fig = go.Figure()
    
    # Add Candlestick trace
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['Open'],
        high=df['High'],
        low=df['Low'],
        close=df['Close'],
        name='Price',
        increasing_line_color='#26a69a', 
        decreasing_line_color='#ef5350'
    ))
    
    # Add 200 DMA trace
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df['200_DMA'],
        mode='lines',
        name='200 DMA',
        line=dict(color='#ffb74d', width=2)
    ))

    # Add 150 DMA trace for Stage Analysis reference
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df['150_DMA'],
        mode='lines',
        name='150 DMA (30wk)',
        line=dict(color='#ab47bc', width=1, dash='dash')
    ))

    # Add background shading for Stage 2 (Green) and Stage 4 (Red)
    for stage_info, group in df.groupby(['Stage', 'Stage_Group']):
        stage_num = stage_info[0]
        if stage_num == 0 or len(group) < 2:
            continue
            
        start_date = group.index[0]
        end_date = group.index[-1]
        
        color = "rgba(38, 166, 154, 0.15)" if stage_num == 2 else "rgba(239, 83, 80, 0.15)"
        
        fig.add_vrect(
            x0=start_date, x1=end_date,
            fillcolor=color, opacity=1,
            layer="below", line_width=0,
        )
        
        # Calculate & display trade metrics for Stage 2 Runs!
        if stage_num == 2:
            entry_price = group['Close'].iloc[0]
            exit_price = group['Close'].iloc[-1]
            profit_pct = ((exit_price - entry_price) / entry_price) * 100
            
            time_in_days = (end_date - start_date).days
            
            # Position at the center-date of the block
            mid_index = int(len(group) / 2)
            mid_date = group.index[mid_index]
            
            # Color logic
            profit_color = "#26a69a" if profit_pct >= 0 else "#ef5350"
            profit_sign = "+" if profit_pct > 0 else ""
            
            metrics_html = f"<span style='color:{profit_color}; font-weight:bold;'>{profit_sign}{profit_pct:.1f}%</span><br><span style='color:#a3a6af; font-size:11px;'>{time_in_days}d</span>"
            
            fig.add_annotation(
                x=mid_date,
                y=0.02, # Stick it beautifully right near the bottom X axis timeline
                yref="paper",
                text=metrics_html,
                showarrow=False,
                bgcolor="rgba(0,0,0,0.6)", # dark glassmorphism
                bordercolor="rgba(255,255,255,0.1)",
                borderwidth=1,
                borderpad=4
            )

    # Customize the layout for a premium dark-mode TradingView feel
    fig.update_layout(
        xaxis_rangeslider_visible=False,
        height=650,
        margin=dict(l=0, r=0, t=10, b=0),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#d1d4dc'),
        xaxis=dict(showgrid=True, gridcolor='rgba(42, 46, 57, 0.4)', showline=False),
        yaxis=dict(showgrid=True, gridcolor='rgba(42, 46, 57, 0.4)', showline=False, side='right'),
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01, bgcolor="rgba(0,0,0,0)")
    )

    st.plotly_chart(fig, use_container_width=True)
