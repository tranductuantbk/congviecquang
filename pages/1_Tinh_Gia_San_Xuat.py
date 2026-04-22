import streamlit as st
import pandas as pd

# --- KHỞI TẠO BỘ NHỚ LƯU TRỮ ---
if 'danh_sach_sp' not in st.session_state:
    st.session_state.danh_sach_sp = []

st.title("💰 MODULE: TÍNH GIÁ SẢN XUẤT")
st.write("---")

# --- TẠO 2 TAB ---
tab_tinh_toan, tab_danh_sach = st.tabs(["🧮 1. TÍNH TOÁN & NHẬP LIỆU", "📋 2. DANH SÁCH SẢN PHẨM"])

# ==========================================
# TAB 1: TÍNH TOÁN VÀ NHẬP LIỆU
# ==========================================
with tab_tinh_toan:
    st.subheader("📝 THÔNG TIN SẢN PHẨM")
    col_info1, col_info2 = st.columns(2)
    ma_sp = col_info1.text_input("1. Mã Sản Phẩm", placeholder="VD: SP001")
    ten_sp = col_info2.text_input("2. Tên Sản Phẩm", placeholder="VD: Khay nhựa đen")
    
    st.markdown("---")

    col_input, col_result = st.columns([1.2, 1])

    with col_input:
        st.subheader("📥 THÔNG SỐ ĐẦU VÀO")
        
        # Nhánh 1: Nguyên Vật Liệu
        with st.expander("🍀 NHÁNH 1: NGUYÊN VẬT LIỆU", expanded=True):
            c1, c2 = st.columns(2)
            trong_luong = c1.number_input("Trọng lượng (gram)", min_value=0.0, value=34.0, step=0.1)
            gia_nhua = c2.number_input("Đơn giá nhựa (VNĐ/kg)", min_value=0, value=23000, step=500)
            cp_nvl_1sp = (trong_luong / 1000) * gia_nhua

        # Nhánh 2: Chi phí Sản xuất (Máy)
        with st.expander("⚙️ NHÁNH 2: MÁY SẢN XUẤT", expanded=True):
            c3, c4 = st.columns(2)
            gia_may_ca = c3.number_input("Giá máy / Ca 8h (VNĐ)", min_value=0, value=1700000, step=50000)
            chu_ky = c4.number_input("Chu kỳ (giây)", min_value=1.0, value=40.0, step=1.0)
            sp_khuon = st.number_input("Số SP / Khuôn", min_value=1, value=2)
            sl_ca = (8 * 3600 / chu_ky) * sp_khuon
            cp_may_1sp = gia_may_ca / sl_ca if sl_ca > 0 else 0

        # Nhánh 3: Chi phí khác & Khấu hao
        with st.expander("📦 NHÁNH 3: CHI PHÍ KHÁC & KHẤU HAO", expanded=True):
            bao_bi = st.number_input("Bao bì (VNĐ/SP)", value=10)
            phu_kien = st.number_input("Phụ kiện (VNĐ/SP)", value=100)
            
            st.markdown("**Tính Khấu hao khuôn:**")
            ck1, ck2 = st.columns(2)
            gia_tri_khuon = ck1.number_input("Giá trị khuôn (VNĐ)", min_value=0, value=0, step=1000000)
            sl_khuon_sx = ck2.number_input("SL khuôn sản xuất (Cái)", min_value=1, value=10000)
            khau_hao = gia_tri_khuon / sl_khuon_sx
            cp_khac = bao_bi + phu_kien + khau_hao

    # --- LOGIC TÍNH TOÁN ---
    gvhb = cp_nvl_1sp + cp_may_1sp + cp_khac

    with col_result:
        st.subheader("📊 KẾT QUẢ TÍNH GIÁ")
        
        # --- PHẦN 1: GIÁ ĐẠI LÝ ---
        st.markdown("### **Giá Đại Lý**")
        hs_dl = st.number_input("Hệ số LN ĐL", min_value=0.01, max_value=1.0, value=0.6, step=0.01, key="hs_dl")
        gia_dai_ly = gvhb / hs_dl
        tien_ln_dl = gia_dai_ly - gvhb
        
        st.metric(label="Giá Đại Lý", value=f"{round(gia_dai_ly):,} VNĐ")
        st.markdown(f"<p style='color: #555; font-size: 0.9em; margin-bottom: 0px;'>Giá đại lý được tính bằng: {round(gvhb):,} / {hs_dl}</p>", unsafe_allow_html=True)
        st.write(f"💰 Tiền lợi nhuận: **{round(tien_ln_dl):,} VNĐ**")

        st.write("---")

        # --- PHẦN 2: GIÁ TIÊU CHUẨN (Tính dựa trên Giá đại lý) ---
        st.markdown("### **Giá Tiêu Chuẩn**")
        hs_tc = st.number_input("Hệ số LN TC", min_value=0.01, max_value=1.0, value=0.6, step=0.01, key="hs_tc")
        gia_tieu_chuan = gia_dai_ly / hs_tc
        tien_ln_tc = gia_tieu_chuan - gvhb
        
        st.metric(label="Giá Tiêu Chuẩn", value=f"{round(gia_tieu_chuan):,} VNĐ")
        st.markdown(f"<p style='color: #555; font-size: 0.9em; margin-bottom: 0px;'>Giá tiêu chuẩn được tính bằng: {round(gia_dai_ly):,} / {hs_tc}</p>", unsafe_allow_html=True)
        st.write(f"💰 Tiền lợi nhuận: **{round(tien_ln_tc):,} VNĐ**")
        
        st.write("---")

        # --- PHẦN 3: CHỐT GIÁ ---
        st.markdown("### **Chốt Giá**")
        gia_chot = st.number_input("Nhập giá chốt bán thực tế (VNĐ)", min_value=0, value=int(round(gia_dai_ly)), step=100)
        
        st.write("---")
        
        if st.button("💾 LƯU SẢN PHẨM NÀY", use_container_width=True):
            if ma_sp == "" or ten_sp == "":
                st.warning("⚠️ Vui lòng nhập Mã và Tên sản phẩm!")
            else:
                san_pham_moi = {
                    "Mã SP": ma_sp,
                    "Tên Sản Phẩm": ten_sp,
                    "Giá Vốn": round(gvhb),
                    "Giá Đại Lý": round(gia_dai_ly),
                    "Giá Tiêu Chuẩn": round(gia_tieu_chuan),
                    "Giá Chốt": gia_chot
                }
                st.session_state.danh_sach_sp.append(san_pham_moi)
                st.success(f"✅ Đã lưu: {ten_sp}")

# ==========================================
# TAB 2: DANH SÁCH SẢN PHẨM ĐÃ LƯU
# ==========================================
with tab_danh_sach:
    st.subheader("📋 BẢNG TỔNG HỢP GIÁ")
    if len(st.session_state.danh_sach_sp) > 0:
        df_danh_sach = pd.DataFrame(st.session_state.danh_sach_sp)
        st.dataframe(
            df_danh_sach, 
            use_container_width=True,
            column_config={
                "Giá Vốn": st.column_config.NumberColumn("Giá Vốn", format="%d ₫"),
                "Giá Đại Lý": st.column_config.NumberColumn("Giá Đại Lý", format="%d ₫"),
                "Giá Tiêu Chuẩn": st.column_config.NumberColumn("Giá Tiêu Chuẩn", format="%d ₫"),
                "Giá Chốt": st.column_config.NumberColumn("Giá Chốt", format="%d ₫"),
            }
        )
        if st.button("🗑️ Xóa toàn bộ danh sách"):
            st.session_state.danh_sach_sp = []
            st.rerun()
    else:
        st.info("ℹ️ Chưa có dữ liệu sản phẩm.")
