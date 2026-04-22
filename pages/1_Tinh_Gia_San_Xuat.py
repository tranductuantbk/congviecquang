import streamlit as st
import pandas as pd

# --- KHỞI TẠO BỘ NHỚ LƯU TRỮ ---
# Nếu chưa có danh sách sản phẩm trong bộ nhớ, hệ thống sẽ tạo một danh sách trống
if 'danh_sach_sp' not in st.session_state:
    st.session_state.danh_sach_sp = []

st.title("💰 MODULE: TÍNH GIÁ SẢN XUẤT")
st.write("---")

# --- TẠO 2 TAB (THẺ) ---
tab_tinh_toan, tab_danh_sach = st.tabs(["🧮 1. TÍNH TOÁN & NHẬP LIỆU", "📋 2. DANH SÁCH SẢN PHẨM"])

# ==========================================
# TAB 1: TÍNH TOÁN VÀ NHẬP LIỆU
# ==========================================
with tab_tinh_toan:
    # Thêm phần Nhập Mã và Tên Sản phẩm
    st.subheader("📝 THÔNG TIN SẢN PHẨM")
    col_info1, col_info2 = st.columns(2)
    ma_sp = col_info1.text_input("1. Mã Sản Phẩm", placeholder="VD: SP001")
    ten_sp = col_info2.text_input("2. Tên Sản Phẩm", placeholder="VD: Khay nhựa đen")
    
    st.markdown("---")

    # --- GIAO DIỆN CHIA CỘT ---
    col_input, col_result = st.columns([1.2, 1])

    with col_input:
        st.subheader("📥 THÔNG SỐ ĐẦU VÀO")
        
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
        st.subheader("📊 KẾT QUẢ TÍNH TOÁN")
        ln_percent = st.slider("Lợi nhuận mong muốn (%)", 0, 200, 60)
        tien_ln = gvhb * (ln_percent / 100)
        gia_ban = gvhb + tien_ln

        st.metric(label="GIÁ BÁN DỰ KIẾN", value=f"{round(gia_ban):,} VNĐ")
        
        df_logic = pd.DataFrame({
            "Hạng mục": ["Nguyên Vật Liệu", "Máy sản xuất", "Chi phí khác", "GIÁ VỐN (GVHB)", "Lợi nhuận"],
            "Số tiền (VNĐ)": [f"{cp_nvl_1sp:,.0f}", f"{cp_may_1sp:,.0f}", f"{cp_khac:,.0f}", f"{gvhb:,.0f}", f"{tien_ln:,.0f}"]
        })
        st.table(df_logic)
        
        # --- NÚT LƯU SẢN PHẨM ---
        st.markdown("---")
        if st.button("💾 LƯU SẢN PHẨM NÀY", use_container_width=True):
            if ma_sp == "" or ten_sp == "":
                st.warning("⚠️ Vui lòng nhập đầy đủ Mã và Tên sản phẩm ở phía trên trước khi lưu!")
            else:
                # Tạo một cuốn sổ ghi chép tạm thời cho sản phẩm này
                san_pham_moi = {
                    "Mã SP": ma_sp,
                    "Tên Sản Phẩm": ten_sp,
                    "Trọng lượng (g)": trong_luong,
                    "Giá Nhựa": f"{gia_nhua:,.0f}",
                    "Giá Vốn (GVHB)": round(gvhb),
                    "% Lời": f"{ln_percent}%",
                    "Tiền Lời": round(tien_ln),
                    "GIÁ BÁN": round(gia_ban)
                }
                # Thêm vào danh sách trong bộ nhớ
                st.session_state.danh_sach_sp.append(san_pham_moi)
                st.success(f"✅ Đã lưu thành công: {ten_sp}")

# ==========================================
# TAB 2: DANH SÁCH SẢN PHẨM ĐÃ LƯU
# ==========================================
with tab_danh_sach:
    st.subheader("📋 BẢNG TỔNG HỢP SẢN PHẨM")
    
    # Kiểm tra xem danh sách có dữ liệu chưa
    if len(st.session_state.danh_sach_sp) > 0:
        # Chuyển dữ liệu thành bảng Pandas để hiển thị đẹp hơn
        df_danh_sach = pd.DataFrame(st.session_state.danh_sach_sp)
        
        # Định dạng lại cột tiền tệ cho dễ nhìn
        st.dataframe(
            df_danh_sach, 
            use_container_width=True,
            column_config={
                "Giá Vốn (GVHB)": st.column_config.NumberColumn("Giá Vốn (VNĐ)", format="%d ₫"),
                "Tiền Lời": st.column_config.NumberColumn("Tiền Lời (VNĐ)", format="%d ₫"),
                "GIÁ BÁN": st.column_config.NumberColumn("GIÁ BÁN (VNĐ)", format="%d ₫"),
            }
        )
        
        # Thêm nút tải file Excel hoặc xóa danh sách (Tính năng nâng cao)
        if st.button("🗑️ Xóa toàn bộ danh sách"):
            st.session_state.danh_sach_sp = []
            st.rerun() # Tải lại trang để cập nhật giao diện
            
    else:
        st.info("ℹ️ Hiện chưa có sản phẩm nào được lưu. Hãy quay lại Tab Tính Toán để thêm mới nhé!")
