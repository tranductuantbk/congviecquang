import streamlit as st
import pandas as pd

# --- KHỞI TẠO BỘ NHỚ LƯU TRỮ ---
if 'danh_sach_sp' not in st.session_state:
    st.session_state.danh_sach_sp = []

st.title("💰 MODULE: TÍNH GIÁ SẢN XUẤT")
st.write("---")

# --- TẠO 3 TAB ---
tab_tinh_toan, tab_danh_sach, tab_ghep_bo = st.tabs([
    "🧮 1. TÍNH TOÁN & NHẬP LIỆU", 
    "📋 2. DANH SÁCH SẢN PHẨM", 
    "🧩 3. GHÉP BỘ"
])

# ==========================================
# TAB 1: TÍNH TOÁN VÀ NHẬP LIỆU (Đơn lẻ)
# ==========================================
with tab_tinh_toan:
    st.subheader("📝 THÔNG TIN SẢN PHẨM ĐƠN LẺ")
    col_info1, col_info2 = st.columns(2)
    ma_sp = col_info1.text_input("1. Mã Sản Phẩm", placeholder="VD: SP001", key="ma_don")
    ten_sp = col_info2.text_input("2. Tên Sản Phẩm", placeholder="VD: Khay nhựa đen", key="ten_don")
    
    st.markdown("---")
    col_input, col_result = st.columns([1.2, 1])

    with col_input:
        st.subheader("📥 THÔNG SỐ ĐẦU VÀO")
        with st.expander("🍀 NHÁNH 1: NGUYÊN VẬT LIỆU", expanded=True):
            c1, c2 = st.columns(2)
            trong_luong = c1.number_input("Trọng lượng (gram)", min_value=0.0, value=34.0, step=0.1)
            gia_nhua = c2.number_input("Đơn giá nhựa (VNĐ/kg)", min_value=0, value=23000, step=500)
            cp_nvl_1sp = (trong_luong / 1000) * gia_nhua

        with st.expander("⚙️ NHÁNH 2: MÁY SẢN XUẤT", expanded=True):
            c3, c4 = st.columns(2)
            gia_may_ca = c3.number_input("Giá máy / Ca 8h (VNĐ)", min_value=0, value=1700000, step=50000)
            chu_ky = c4.number_input("Chu kỳ (giây)", min_value=1.0, value=40.0, step=1.0)
            sp_khuon = st.number_input("Số SP / Khuôn", min_value=1, value=2)
            sl_ca = (8 * 3600 / chu_ky) * sp_khuon
            cp_may_1sp = gia_may_ca / sl_ca if sl_ca > 0 else 0

        with st.expander("📦 NHÁNH 3: CHI PHÍ KHÁC & KHẤU HAO", expanded=True):
            bao_bi = st.number_input("Bao bì (VNĐ/SP)", value=10, key="bb_don")
            phu_kien = st.number_input("Phụ kiện (VNĐ/SP)", value=100, key="pk_don")
            gia_tri_khuon = st.number_input("Giá trị khuôn (VNĐ)", min_value=0, value=0, step=1000000, key="gt_khuon_don")
            sl_khuon_sx = st.number_input("SL khuôn sản xuất (Cái)", min_value=1, value=10000, key="sl_khuon_don")
            khau_hao = gia_tri_khuon / sl_khuon_sx
            cp_khac = bao_bi + phu_kien + khau_hao

    gvhb = cp_nvl_1sp + cp_may_1sp + cp_khac

    with col_result:
        st.subheader("📊 KẾT QUẢ TÍNH GIÁ")
        st.markdown("### **Giá Đại Lý**")
        hs_dl = st.number_input("Hệ số LN ĐL", min_value=0.01, max_value=1.0, value=0.6, step=0.01, key="hs_dl_don")
        gia_dai_ly = gvhb / hs_dl
        st.metric(label="Giá Đại Lý", value=f"{round(gia_dai_ly):,} VNĐ")
        st.markdown(f"<p style='color: #555; font-size: 0.9em;'>Công thức: {round(gvhb):,} / {hs_dl}</p>", unsafe_allow_html=True)
        
        st.write("---")
        st.markdown("### **Giá Tiêu Chuẩn**")
        hs_tc = st.number_input("Hệ số LN TC", min_value=0.01, max_value=1.0, value=0.6, step=0.01, key="hs_tc_don")
        gia_tieu_chuan = gia_dai_ly / hs_tc
        st.metric(label="Giá Tiêu Chuẩn", value=f"{round(gia_tieu_chuan):,} VNĐ")
        st.markdown(f"<p style='color: #555; font-size: 0.9em;'>Công thức: {round(gia_dai_ly):,} / {hs_tc}</p>", unsafe_allow_html=True)

        if st.button("💾 LƯU SẢN PHẨM", key="btn_don"):
            if ma_sp and ten_sp:
                st.session_state.danh_sach_sp.append({
                    "Mã SP": ma_sp, "Tên Sản Phẩm": ten_sp, "Giá Vốn": round(gvhb),
                    "Giá Đại Lý": round(gia_dai_ly), "Giá Tiêu Chuẩn": round(gia_tieu_chuan)
                })
                st.success("Đã lưu!")
            else: st.warning("Nhập tên và mã!")

# ==========================================
# TAB 3: GHÉP BỘ (CẬP NHẬT MỚI)
# ==========================================
with tab_ghep_bo:
    st.subheader("🧩 GHÉP BỘ SẢN PHẨM")
    
    # Kiểm tra xem có đủ sản phẩm để ghép không
    if len(st.session_state.danh_sach_sp) < 1:
        st.warning("⚠️ Bạn cần lưu ít nhất 1 sản phẩm ở Tab 1 để thực hiện ghép bộ!")
    else:
        ma_bo = st.text_input("1. Mã Bộ sản phẩm", placeholder="VD: BO001")
        ten_bo = st.text_input("2. Tên Bộ sản phẩm", placeholder="VD: Bộ hộp nắp gài")
        
        st.markdown("---")
        col_in_ghep, col_res_ghep = st.columns([1.2, 1])
        
        with col_in_ghep:
            # Nhánh 2: Bộ phận ghép
            with st.expander("⚙️ NHÁNH 2: BỘ PHẬN GHÉP", expanded=True):
                # Tạo danh sách tên để chọn
                list_ten_sp = [sp["Tên Sản Phẩm"] for sp in st.session_state.danh_sach_sp]
                
                chon_than = st.selectbox("Mục bộ phận thân:", list_ten_sp, key="sb_than")
                chon_nap = st.selectbox("Mục bộ phận nắp:", list_ten_sp, key="sb_nap")
                
                # Lấy giá vốn tương ứng
                von_than = next(item["Giá Vốn"] for item in st.session_state.danh_sach_sp if item["Tên Sản Phẩm"] == chon_than)
                von_nap = next(item["Giá Vốn"] for item in st.session_state.danh_sach_sp if item["Tên Sản Phẩm"] == chon_nap)
                
                st.info(f"💰 Vốn thân: {von_than:,} ₫ | Vốn nắp: {von_nap:,} ₫")

            # Nhánh 3: Chi phí khác
            with st.expander("📦 NHÁNH 3: CHI PHÍ KHÁC (BỘ)", expanded=True):
                bb_bo = st.number_input("Bao bì bộ (VNĐ/Bộ)", value=500)
                pk_bo = st.number_input("Phụ kiện bộ (VNĐ/Bộ)", value=200)
                cong_ghep = st.number_input("Công ghép bộ/đóng gói (VNĐ)", value=1000)
                cp_khac_bo = bb_bo + pk_bo + cong_ghep

            # Tổng vốn bộ ghép
            gvhb_bo = von_than + von_nap + cp_khac_bo

        with col_res_ghep:
            st.subheader("📊 KẾT QUẢ BỘ GHÉP")
            st.markdown("### **Giá Đại Lý (Bộ)**")
            hs_dl_bo = st.number_input("Hệ số LN ĐL", value=0.6, key="hs_dl_bo")
            gia_dl_bo = gvhb_bo / hs_dl_bo
            st.metric("Giá Đại Lý Bộ", f"{round(gia_dl_bo):,} VNĐ")
            st.markdown(f"<p style='color: #555; font-size: 0.85em;'>Cách tính: ({von_than:,} + {von_nap:,} + {cp_khac_bo:,}) / {hs_dl_bo}</p>", unsafe_allow_html=True)
            
            st.write("---")
            st.markdown("### **Giá Tiêu Chuẩn (Bộ)**")
            hs_tc_bo = st.number_input("Hệ số LN TC", value=0.6, key="hs_tc_bo")
            gia_tc_bo = gia_dl_bo / hs_tc_bo
            st.metric("Giá Tiêu Chuẩn Bộ", f"{round(gia_tc_bo):,} VNĐ")
            st.markdown(f"<p style='color: #555; font-size: 0.85em;'>Cách tính: {round(gia_dl_bo):,} / {hs_tc_bo}</p>", unsafe_allow_html=True)

            if st.button("💾 LƯU BỘ GHÉP NÀY"):
                if ma_bo and ten_bo:
                    st.session_state.danh_sach_sp.append({
                        "Mã SP": ma_bo, "Tên Sản Phẩm": f"[BỘ] {ten_bo}", "Giá Vốn": round(gvhb_bo),
                        "Giá Đại Lý": round(gia_dl_bo), "Giá Tiêu Chuẩn": round(gia_tc_bo)
                    })
                    st.success("Đã lưu bộ ghép!")

# ==========================================
# TAB 2: DANH SÁCH SẢN PHẨM
# ==========================================
with tab_danh_sach:
    st.subheader("📋 BẢNG TỔNG HỢP SẢN PHẨM & BỘ GHÉP")
    if st.session_state.danh_sach_sp:
        df = pd.DataFrame(st.session_state.danh_sach_sp)
        st.dataframe(df, use_container_width=True)
        if st.button("🗑️ Xóa danh sách"):
            st.session_state.danh_sach_sp = []; st.rerun()
