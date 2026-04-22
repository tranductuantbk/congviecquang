import streamlit as st
import pandas as pd

st.title("💰 MODULE: TÍNH GIÁ SẢN XUẤT")
st.write("---")

# --- GIAO DIỆN CHIA CỘT ---
col_input, col_result = st.columns([1.2, 1])

with col_input:
    st.subheader("📥 1. NHẬP THÔNG SỐ")
    
    with st.expander("🍀 NHÁNH 1: NGUYÊN VẬT LIỆU", expanded=True):
        c1, c2 = st.columns(2)
        trong_luong = c1.number_input("Trọng lượng (gram)", min_value=0.0, value=34.0)
        gia_nhua = c2.number_input("Đơn giá nhựa (VNĐ/kg)", min_value=0, value=23000)
        cp_nvl_1sp = (trong_luong / 1000) * gia_nhua

    with st.expander("⚙️ NHÁNH 2: MÁY SẢN XUẤT", expanded=True):
        c3, c4 = st.columns(2)
        gia_may_ca = c3.number_input("Giá máy / Ca 8h (VNĐ)", min_value=0, value=1700000)
        chu_ky = c4.number_input("Chu kỳ (giây)", min_value=1.0, value=40.0)
        sp_khuon = st.number_input("Số SP / Khuôn", min_value=1, value=2)
        sl_ca = (8 * 3600 / chu_ky) * sp_khuon
        cp_may_1sp = gia_may_ca / sl_ca if sl_ca > 0 else 0

    with st.expander("📦 NHÁNH 3: CHI PHÍ KHÁC", expanded=True):
        bao_bi = st.number_input("Bao bì (VNĐ/SP)", value=10)
        phu_kien = st.number_input("Phụ kiện (VNĐ/SP)", value=100)
        khau_hao = st.number_input("Khấu hao khuôn (VNĐ/SP)", value=0)
        cp_khac = bao_bi + phu_kien + khau_hao

# --- TÍNH TOÁN ---
gvhb = cp_nvl_1sp + cp_may_1sp + cp_khac

with col_result:
    st.subheader("📊 2. KẾT QUẢ")
    ln_percent = st.slider("Lợi nhuận mong muốn (%)", 0, 200, 60)
    tien_ln = gvhb * (ln_percent / 100)
    gia_ban = gvhb + tien_ln

    st.metric(label="GIÁ BÁN DỰ KIẾN", value=f"{round(gia_ban):,} VNĐ")
    
    df_logic = pd.DataFrame({
        "Hạng mục": ["Nguyên Vật Liệu", "Máy sản xuất", "Chi phí khác", "GIÁ VỐN (GVHB)", "Lợi nhuận"],
        "Số tiền (VNĐ)": [f"{cp_nvl_1sp:,.0f}", f"{cp_may_1sp:,.0f}", f"{cp_khac:,.0f}", f"{gvhb:,.0f}", f"{tien_ln:,.0f}"]
    })
    st.table(df_logic)