import streamlit as st
import pandas as pd

# 設置網頁標題與佈局
st.set_page_config(page_title="特賣會多場次獨立計算工具", layout="wide")

st.title("⛺ 特賣會各分點獨立開銷試算")
st.write("請在下方表格中，針對每個場次填寫其**專屬的開銷**（租金、人事、電費等）。點擊表格下方的 **+** 號可新增場次。")

# --- 1. 全域參數設定 (會套用到所有分點) ---
with st.expander("⚙️ 全域參數設定 (預設稅率與耗材)"):
    col_a, col_b = st.columns(2)
    with col_a:
        global_tax_rate = st.number_input("發票稅率 (%)", value=5.0) / 100
    with col_b:
        global_pkg_rate = st.number_input("平均耗材率 (%)", value=0.0) / 100

# --- 2. 建立初始資料結構 (使用 session_state 保持資料) ---
if 'df_special' not in st.session_state:
    st.session_state.df_special = pd.DataFrame([
        {
            "場次名稱": "台北 A 場", 
            "預估營業額": 600000, 
            "商品毛利率": 0.35, 
            "場地租金": 120000, 
            "現場人事": 45000, 
            "水電物流": 5000, 
            "該場廣告費": 20000,
            "場地抽成率": 0.05
        },
        {
            "場次名稱": "台中 B 場", 
            "預估營業額": 400000, 
            "商品毛利率": 0.40, 
            "場地租金": 60000, 
            "現場人事": 30000, 
            "水電物流": 3000, 
            "該場廣告費": 10000,
            "場地抽成率": 0.00
        },
    ])

# --- 3. 互動式編輯區 ---
st.subheader("📝 各場次明細填寫")
edited_df = st.data_editor(
    st.session_state.df_special,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "場次名稱": st.column_config.TextColumn("場次名稱", help="請輸入分點場地名稱"),
        "預估營業額": st.column_config.NumberColumn("預估營收", format="$%d"),
        "商品毛利率": st.column_config.NumberColumn("毛利率", format="%.2f", help="扣除進貨成本後的毛利率"),
        "場地租金": st.column_config.NumberColumn("場地租金", format="$%d"),
        "現場人事": st.column_config.NumberColumn("現場人事", format="$%d"),
        "水電物流": st.column_config.NumberColumn("雜支/水電", format="$%d"),
        "該場廣告費": st.column_config.NumberColumn("廣告費", format="$%d"),
        "場地抽成率": st.column_config.NumberColumn("場地抽成率", format="%.2f", help="若場地有額外抽成百分比"),
    }
)

# --- 4. 計算邏輯 (包含錯誤處理與類型轉換) ---
def process_detailed_calc(df):
    calc_df = df.copy()
    
    # 強制轉換數值欄位為數字，防止新增行時產生的 TypeError
    numeric_cols = [
        "預估營業額", "商品毛利率", "場地租金", 
        "現場人事", "水電物流", "該場廣告費", "場地抽成率"
    ]
    for col in numeric_cols:
        calc_df[col] = pd.to_numeric(calc_df[col], errors='coerce').fillna(0)
    
    # A. 計算毛利金額
    calc_df["毛利總額"] = calc_df["預估營業額"] * calc_df["商品毛利率"]
    
    # B. 計算變動成本總額 (稅 + 耗材 + 場地抽成)
    calc_df["變動成本"] = calc_df["預估營業額"] * (global_tax_rate + global_pkg_rate + calc_df["場地抽成率"])
    
    # C. 計算固定開銷合計
    calc_df["固定開銷合計"] = (
        calc_df["場地租金"] + 
        calc_df["現場人事"] + 
        calc_df["水電物流"] + 
        calc_df["該場廣告費"]
    )
    
    # D. 最終預估淨利
    calc_df["預估淨利"] = calc_df["毛利總額"] - calc_df["變動成本"] - calc_df["固定開銷合計"]
    
    # E. 損益兩平點 (打平所需營收)
    # 公式：固定開銷 / (毛利率 - 變動費率)
    def get_be_rev(row):
        denom = row["商品毛利率"] - (global_tax_rate + global_pkg_rate + row["場地抽成率"])
        return row["固定開銷合計"] / denom if denom > 0 else 0
    
    calc_df["打平所需營收"] = calc_df.apply(get_be_rev, axis=1)
    
    # F. ROI (%)
    # 總成本估算 = (營收 - 毛利) + 變動成本 + 固定開銷
    total_cost = (calc_df["預估營業額"] - calc_df["毛利總額"]) + calc_df["變動成本"] + calc_df["固定開銷合計"]
    calc_df["投報率 ROI (%)"] = (calc_df["預估淨利"] / total_cost * 100).fillna(0)
    
    return calc_df

# 執行計算
result_df = process_detailed_calc(edited_df)

# --- 5. 呈現結果 ---
st.divider()
st.header("📊 獲利分析彙整")

# 總結卡片
total_rev = result_df["預估營業額"].sum()
total_net = result_df["預估淨利"].sum()
avg_roi = result_df["投報率 ROI (%)"].mean()

c1, c2, c3 = st.columns(3)
c1.metric("所有場次總營收", f"${total_rev:,.0f}")
c2.metric("預計總淨利", f"${total_net:,.0f}", delta=f"{total_net:,.0f}")
c3.metric("平均場次 ROI", f"{avg_roi:.1f}%")

# 顯示明細報表 (使用 format 避免 matplotlib 依賴)
st.subheader("🔍 分點損益明細表")
show_cols = ["場次名稱", "預估營業額", "毛利總額", "固定開銷合計", "預估淨利", "打平所需營收", "投報率 ROI (%)"]

st.dataframe(
    result_df[show_cols].style.format({
        "預估營業額": "${:,.0f}",
        "毛利總額": "${:,.0f}",
        "固定開銷合計": "${:,.0f}",
        "預估淨利": "${:,.0f}",
        "打平所需營收": "${:,.0f}",
        "投報率 ROI (%)": "{:.1f}%"
    }),
    use_container_width=True
)

# --- 6. 匯出功能 ---
st.divider()
csv = result_df.to_csv(index=False).encode('utf-8-sig')
st.download_button(
    label="📥 下載完整結算報表 (Excel 可開 CSV)",
    data=csv,
    file_name='特賣會分點結算.csv',
    mime='text/csv',
)

st.info("💡 **小撇步**：\n1. 若某場次淨利為負，請參考『打平所需營收』來重新評估該場地的租金或人力配置。\n2. 點擊表格標題可以進行排序，快速找出最賺錢的場次。")