import streamlit as st
import pandas as pd
import os
import altair as alt

# 设置页面配置
st.set_page_config(
    page_title="上市公司数字化转型全景看板",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 常量
CSV_FILE = '1999-2023年数字化转型指数结果表.csv'
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, CSV_FILE)

# 自定义 CSS
st.markdown("""
    <style>
    /* 全局背景与字体 */
    .stApp {
        background-color: #f0f2f6;
    }
    
    /* 侧边栏优化 */
    section[data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e6e6e6;
    }
    
    /* 标题样式 */
    h1, h2, h3 {
        color: #1f2937;
        font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    }
    
    /* 指标卡片自定义 */
    div[data-testid="stMetric"] {
        background-color: white;
        padding: 15px 20px;
        border-radius: 8px;
        border-left: 5px solid #3b82f6;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    
    /* 图表容器背景 */
    .element-container canvas {
        background-color: white;
        border-radius: 8px;
    }
    
    /* 调整 Tab 样式 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        background-color: transparent;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #e5e7eb;
        border-radius: 4px;
        padding: 8px 16px;
        border: none;
    }
    .stTabs [aria-selected="true"] {
        background-color: #3b82f6 !important;
        color: white !important;
    }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data
def load_data():
    """加载并预处理数据"""
    if not os.path.exists(CSV_PATH):
        return None, None
    
    try:
        # 读取数据
        df = pd.read_csv(CSV_PATH, encoding='utf-8', dtype={'股票代码': str})
        
        # 数据清洗
        df['年份'] = pd.to_numeric(df['年份'], errors='coerce')
        df = df.dropna(subset=['年份'])
        df['年份'] = df['年份'].astype(int)
        
        # 计算市场年度平均值
        market_avg = df.groupby('年份')[['数字化转型指数(0-100分)', '总词频数']].mean().reset_index()
        market_avg.rename(columns={
            '数字化转型指数(0-100分)': '市场平均指数',
            '总词频数': '市场平均词频'
        }, inplace=True)
        
        return df, market_avg
    except Exception as e:
        st.error(f"数据加载失败: {e}")
        return None, None

def render_metric_card(title, value, delta=None, help_text=None):
    st.metric(label=title, value=value, delta=delta, help=help_text)

def main():
    df, market_avg_df = load_data()

    if df is None:
        st.error(f"无法找到数据文件: {CSV_PATH}")
        return

    # --- 侧边栏控制区 ---
    with st.sidebar:
        st.title("🎛️ 分析控制台")
        st.markdown("---")
        
        # 搜索模式
        search_mode = st.radio("检索方式", ["企业名称", "股票代码"], horizontal=True)
        
        # 搜索框
        if 'search_query' not in st.session_state:
            st.session_state.search_query = '平安银行' if search_mode == "企业名称" else "000001"
            
        query = st.text_input(f"输入{search_mode}", value=st.session_state.search_query)
        
        # 年份筛选
        min_year = int(df['年份'].min())
        max_year = int(df['年份'].max())
        selected_years = st.slider("分析时间段", min_year, max_year, (2010, max_year))
        
        st.markdown("---")
        st.markdown("### � 快速访问")
        top_companies = [("平安银行", "000001"), ("万科A", "000002"), ("美的集团", "000333"), ("比亚迪", "002594")]
        for name, code in top_companies:
            if st.button(f"{name} ({code})", use_container_width=True):
                st.session_state.search_query = name if search_mode == "企业名称" else code
                st.rerun()

    # --- 主内容区 ---
    st.title("� 上市公司数字化转型全景看板")
    st.markdown(f"**数据来源**: 上市公司年报文本分析 ({min_year}-{max_year})")
    
    # 筛选数据
    target_company = None
    if query:
        if search_mode == "股票代码":
            matches = df[df['股票代码'] == query]
        else:
            matches = df[df['企业名称'] == query]
            if matches.empty: # 模糊搜索
                matches = df[df['企业名称'].str.contains(query, na=False)]
        
        if not matches.empty:
            # 取匹配到的第一个公司（通常是最新的名字，或者代码对应的唯一公司）
            first_code = matches['股票代码'].iloc[0]
            target_company = df[df['股票代码'] == first_code].sort_values('年份')
            
            # 过滤年份
            mask = (target_company['年份'] >= selected_years[0]) & (target_company['年份'] <= selected_years[1])
            filtered_company = target_company[mask].copy()
            
            if filtered_company.empty:
                st.warning(f"该企业在 {selected_years[0]}-{selected_years[1]} 年间无数据。")
                return

            company_name = filtered_company['企业名称'].iloc[-1]
            stock_code = first_code
            
            # 顶部核心指标
            st.subheader(f"🏢 {company_name} ({stock_code})")
            
            latest_rec = filtered_company.iloc[-1]
            latest_idx = latest_rec['数字化转型指数(0-100分)']
            latest_yr = latest_rec['年份']
            
            # 计算同比
            prev_rec = filtered_company.iloc[-2] if len(filtered_company) > 1 else None
            idx_delta = round(latest_idx - prev_rec['数字化转型指数(0-100分)'], 2) if prev_rec is not None else 0
            
            # 市场排名
            current_market = df[df['年份'] == latest_yr]
            rank = current_market['数字化转型指数(0-100分)'].rank(ascending=False, method='min')
            my_rank = rank[df['股票代码'] == stock_code].iloc[0] if not rank[df['股票代码'] == stock_code].empty else "N/A"
            total_comps = len(current_market)
            
            # 指标卡片布局
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                render_metric_card("当前转型指数", f"{latest_idx:.1f}", f"{idx_delta} YoY")
            with col2:
                render_metric_card("市场排名", f"{int(my_rank)}", f"Top {int(my_rank/total_comps*100)}%")
            with col3:
                render_metric_card("数字化关键词频", f"{int(latest_rec['总词频数'])}")
            with col4:
                render_metric_card("数据年份", f"{latest_yr}")
            
            st.markdown("---")
            
            # 数据合并市场均值
            chart_df = pd.merge(filtered_company, market_avg_df, on='年份', how='left')
            
            # 布局：左侧主要趋势，右侧结构分布
            tab1, tab2, tab3 = st.tabs(["� 趋势洞察", "🔬 结构透视", "� 数据明细"])
            
            with tab1:
                col_chart_1, col_chart_2 = st.columns([2, 1])
                
                with col_chart_1:
                    st.markdown("#### 数字化转型指数走势 (vs 市场平均)")
                    # 构造 Altair 图表
                    base = alt.Chart(chart_df).encode(x=alt.X('年份:O', axis=alt.Axis(labelAngle=0)))
                    
                    line_company = base.mark_line(point=True, color='#3b82f6', strokeWidth=3).encode(
                        y=alt.Y('数字化转型指数(0-100分)', title='指数得分'),
                        tooltip=['年份', '数字化转型指数(0-100分)', '市场平均指数']
                    )
                    
                    line_market = base.mark_line(strokeDash=[5, 5], color='#9ca3af').encode(
                        y='市场平均指数'
                    )
                    
                    chart_trend = (line_company + line_market).interactive().properties(height=350)
                    st.altair_chart(chart_trend, use_container_width=True)
                
                with col_chart_2:
                    st.markdown("#### 转型动力分析 (最新年)")
                    # 词频构成的饼图/环形图
                    tech_cols = ['人工智能词频数', '大数据词频数', '云计算词频数', '区块链词频数', '数字技术运用词频数']
                    latest_tech_data = latest_rec[tech_cols].reset_index()
                    latest_tech_data.columns = ['技术领域', '词频']
                    latest_tech_data['技术领域'] = latest_tech_data['技术领域'].str.replace('词频数', '')
                    
                    pie_chart = alt.Chart(latest_tech_data).mark_arc(innerRadius=50).encode(
                        theta=alt.Theta(field="词频", type="quantitative"),
                        color=alt.Color(field="技术领域", type="nominal", scale=alt.Scale(scheme='category10')),
                        tooltip=['技术领域', '词频']
                    ).properties(height=350)
                    
                    st.altair_chart(pie_chart, use_container_width=True)

            with tab2:
                st.markdown("#### 技术关注点演变热力图")
                # 准备热力图数据
                heatmap_data = filtered_company[['年份'] + tech_cols].melt('年份', var_name='技术', value_name='词频')
                heatmap_data['技术'] = heatmap_data['技术'].str.replace('词频数', '')
                
                heatmap = alt.Chart(heatmap_data).mark_rect().encode(
                    x=alt.X('年份:O', axis=alt.Axis(labelAngle=0)),
                    y='技术:N',
                    color=alt.Color('词频:Q', scale=alt.Scale(scheme='blues')),
                    tooltip=['年份', '技术', '词频']
                ).properties(height=300)
                
                st.altair_chart(heatmap, use_container_width=True)
                
                st.markdown("#### 各维度相对权重堆叠图")
                bar_chart = alt.Chart(heatmap_data).mark_bar().encode(
                    x=alt.X('年份:O', axis=alt.Axis(labelAngle=0)),
                    y=alt.Y('词频', stack="normalize", title='相对占比'),
                    color=alt.Color('技术', scale=alt.Scale(scheme='category10')),
                    tooltip=['年份', '技术', '词频']
                ).properties(height=300)
                st.altair_chart(bar_chart, use_container_width=True)

            with tab3:
                st.markdown("#### 原始数据浏览")
                display_cols = ['年份', '企业名称', '数字化转型指数(0-100分)', '总词频数'] + tech_cols
                st.dataframe(
                    filtered_company[display_cols].sort_values('年份', ascending=False),
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "年份": st.column_config.NumberColumn(format="%d"),
                        "数字化转型指数(0-100分)": st.column_config.ProgressColumn("转型指数", min_value=0, max_value=100, format="%.1f")
                    }
                )
        else:
            st.info("未找到匹配企业，请尝试其他关键词。")
    else:
        st.info("👈 请在左侧输入股票代码或简称开始分析")
        
        # 首页：市场整体概览
        st.subheader("📊 市场整体趋势 (1999-2023)")
        
        overview_chart = alt.Chart(market_avg_df).mark_area(
            line={'color':'darkblue'},
            color=alt.Gradient(
                gradient='linear',
                stops=[alt.GradientStop(color='white', offset=0),
                       alt.GradientStop(color='darkblue', offset=1)],
                x1=1, x2=1, y1=1, y2=0
            )
        ).encode(
            x=alt.X('年份:O'),
            y=alt.Y('市场平均指数', title='全市场平均指数'),
            tooltip=['年份', '市场平均指数']
        ).properties(height=400)
        
        st.altair_chart(overview_chart, use_container_width=True)

if __name__ == "__main__":
    main()
