import streamlit as st
import pandas as pd

# --- KHỞI TẠO BỘ NHỚ LƯU TRỮ ---
if 'danh_sach_sp' not in st.session_state:
    st.session_state.danh_sach_sp = []

st.title("💰 MODULE: TÍNH GIÁ SẢN XUẤT")
st.write("---")

# --- TẠO 3 TAB RIÊNG BIỆT ---
tab_tinh_toan, tab_danh_sach, tab_ghep_bo = st.tabs([
    "🧮 1. TÍNH TOÁN & NHẬP LIỆU", 
    "📋 2. DANH SÁCH SẢN PHẨM", 
    "🧩 3. GHÉP BỘ"
])

# ==========================================
# TAB 1: GIỮ NGUYÊN BẢN (Sản phẩm đơn lẻ)
# ==========================================
with tab_tinh_toan:
    st.subheader("📝 THÔNG TIN SẢN PHẨM")
    col_info1, col_info2 = st.columns(2)
    ma_sp = col_info1.text_input("1. Mã Sản Phẩm", placeholder="VD: SP001", key="ma_don")
    ten_sp = col_info2.text_input("2. Tên Sản Phẩm", placeholder="VD: Khay nhựa đen", key="ten_don")
    
    st.markdown("---")
    col_input, col_result = st.columns([1.2, 1])

    with col_input:
        st.subheader("📥 THÔNG SỐ ĐẦU VÀO")
        # Nhánh 1: Nguyên vật liệu
        with st.expander("🍀 NHÁNH 1: NGUYÊN VẬT LIỆU", expanded=True):
            c1, c2 = st.columns(2)
            trong_luong = c1.number_input("Trọng lượng (gram)", min_value=0.0, value=34.0, step=0.1, key="tl_don")
            gia_nhua = c2.number_input("Đơn giá nhựa (VNĐ/kg)", min_value=0, value=23000, step=500, key="gn_don")
            cp_nvl_1sp = (trong_luong / 1000) * gia_nhua

        # Nhánh 2: Máy sản xuất
        with st.expander("⚙️ NHÁNH 2: MÁY SẢN XUẤT", expanded=True):
            c3, c4 = st.columns(2)
            gia_may_ca = c3.number_input("Giá máy / Ca 8h (VNĐ)", min_value=0, value=1700000, step=50000, key="gm_don")
            chu_ky = c4.number_input("Chu kỳ (giây)", min_value=1.0, value=40.0, step=1.0, key="ck_don")
            sp_khuon = st.number_input("Số SP / Khuôn", min_value=1, value=2, key="sk_don")
            sl_ca = (8 * 3600 / chu_ky) * sp_khuon
            cp_may_1sp = gia_may_ca / sl_ca if sl_ca > 0 else 0

        # Nhánh 3: Chi phí khác
        with st.expander("📦 NHÁNH 3: CHI PHÍ KHÁC & KHẤU HAO", expanded=True):
            bao_bi = st.number_input("Bao bì (VNĐ/SP)", value=10, key="bb_don")
            phu_kien = st.number_input("Phụ kiện (VNĐ/SP)", value=100, key="pk_don")
            gia_tri_khuon = st.number_input("Giá trị khuôn (VNĐ)", min_value=0, value=0, key="gt_khuon_don")
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
        st.markdown(f"<p style='color: #555; font-size: 0.9em;'>Cách tính: {round(gvhb):,} / {hs_dl}</p>", unsafe_allow_html=True)
        
        st.write("---")
        st.markdown("### **Giá Tiêu Chuẩn**")
        hs_tc = st.number_input("Hệ số LN TC", min_value=0.01, max_value=1.0, value=0.6, step=0.01, key="hs_tc_don")
        gia_tieu_chuan = gia_dai_ly / hs_tc
        st.metric(label="Giá Tiêu Chuẩn", value=f"{round(gia_tieu_chuan):,} VNĐ")
        st.markdown(f"<p style='color: #555; font-size: 0.9em;'>Cách tính: {round(gia_dai_ly):,} / {hs_tc}</p>", unsafe_allow_html=True)

        if st.button("💾 LƯU SẢN PHẨM", key="btn_don"):
            if ma_sp and ten_sp:
                st.session_state.danh_sach_sp.append({
                    "Mã SP": ma_sp, "Tên Sản Phẩm": ten_sp, "Giá Vốn": round(gvhb),
                    "Giá Đại Lý": round(gia_dai_ly), "Giá Tiêu Chuẩn": round(gia_tieu_chuan)
                })
                st.success(f"Đã lưu {ten_sp}!")

# ==========================================
# TAB 3: GHÉP BỘ (Sửa theo đúng yêu cầu)
# ==========================================
with tab_ghep_bo:
    st.subheader("🧩 GHÉP BỘ SẢN PHẨM")
    
    # Chỉ cho phép ghép nếu đã có sản phẩm trong danh sách
    if not st.session_state.danh_sach_sp:
        st.warning("⚠️ Hãy tạo và lưu sản phẩm ở Tab 1 trước khi thực hiện Ghép bộ.")
    else:
        ma_bo = st.text_input("Mã bộ sản phẩm", key="ma_bo")
        ten_bo = st.text_input("Tên bộ sản phẩm", key="ten_bo")
        
        st.markdown("---")
        col_in_ghep, col_res_ghep = st.columns([1.2, 1])
        
        with col_in_ghep:
            st.subheader("📥 THÔNG SỐ GHÉP")
            # NHÁNH 2: BỘ PHẬN GHÉP (Đổi tên và mục bên trong)
            with st.expander("⚙️ NHÁNH 2: BỘ PHẬN GHÉP", expanded=True):
                list_ten = [sp["Tên Sản Phẩm"] for sp in st.session_state.danh_sach_sp]
                chon_than = st.selectbox("Mục bộ phận thân:", list_ten, key="sb_than")
                chon_nap = st.selectbox("Mục bộ phận nắp:", list_ten, key="sb_nap")
                
                # Lấy giá vốn tương ứng từ danh sách
                von_than = next(s["Giá Vốn"] for s in st.session_state.danh_sach_sp if s["Tên Sản Phẩm"] == chon_than)
                von_nap = next(s["Giá Vốn"] for s in st.session_state.danh_sach_sp if s["Tên Sản Phẩm"] == chon_nap)
                
                st.info(f"💰 Vốn thân: {von_than:,} ₫ | Vốn nắp: {von_nap:,} ₫")

            # NHÁNH 3: CHI PHÍ KHÁC
            with st.expander("📦 NHÁNH 3: CHI PHÍ KHÁC", expanded=True):
                bb_bo = st.number_input("Bao bì bộ (VNĐ)", value=500)
                pk_bo = st.number_input("Phụ kiện bộ (VNĐ)", value=200)
                cong_ghep = st.number_input("Công lắp ghép/đóng gói (VNĐ)", value=1000)
                cp_khac_bo = bb_bo + pk_bo + cong_ghep

            # Tổng vốn bộ = Vốn thân + Vốn nắp + Chi phí khác
            gvhb_bo = von_than + von_nap + cp_khac_bo

        with col_res_ghep:
            st.subheader("📊 KẾT QUẢ BỘ")
            hs_dl_bo = st.number_input("Hệ số LN ĐL (Bộ)", value=0.6, key="hs_dl_bo")
            gia_dl_bo = gvhb_bo / hs_dl_bo
            st.metric("Giá Đại Lý Bộ", f"{round(gia_dl_bo):,} VNĐ")
            st.markdown(f"<p style='color: #555; font-size: 0.85em;'>Cách tính: {round(gvhb_bo):,} / {hs_dl_bo}</p>", unsafe_allow_html=True)
            
            st.write("---")
            hs_tc_bo = st.number_input("Hệ số LN TC (Bộ)", value=0.6, key="hs_tc_bo")
            gia_tc_bo = gia_dl_bo / hs_tc_bo
            st.metric("Giá Tiêu Chuẩn Bộ", f"{round(gia_tc_bo):,} VNĐ")
            st.markdown(f"<p style='color: #555; font-size: 0.85em;'>Cách tính: {round(gia_dl_bo):,} / {hs_tc_bo}</p>", unsafe_allow_html=True)

            if st.button("💾 LƯU BỘ GHÉP"):
                st.session_state.danh_sach_sp.append({
                    "Mã SP": ma_bo, "Tên Sản Phẩm": f"[BỘ] {ten_bo}", "Giá Vốn": round(gvhb_bo),
                    "Giá Đại Lý": round(gia_dl_bo), "Giá Tiêu Chuẩn": round(gia_tc_bo)
                })
                st.success("Đã lưu bộ ghép thành công!")

# ==========================================
# TAB 2: DANH SÁCH SẢN PHẨM (Giữ nguyên)
# ==========================================
with tab_danh_sach:
    st.subheader("📋 BẢNG TỔNG HỢP SẢN PHẨM")
    if st.session_state.danh_sach_sp:
        df = pd.DataFrame(st.session_state.danh_sach_sp)
        st.dataframe(df, use_container_width=True)
        if st.button("🗑️ Xóa danh sách"):
            st.session_state.danh_sach_sp = []; st.rerun()
    else:
        st.info("Chưa có sản phẩm nào được lưu.")
