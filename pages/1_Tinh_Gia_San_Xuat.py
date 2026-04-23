import streamlit as st
import pandas as pd
from sqlalchemy import inspect

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="Tính Giá Sản Xuất", layout="wide")

# ==========================================
# KẾT NỐI NEON (POSTGRESQL) & XỬ LÝ DỮ LIỆU
# ==========================================
try:
    conn = st.connection("postgresql", type="sql")
except Exception as e:
    st.error("Chưa thể kết nối Database Neon. Vui lòng kiểm tra lại file cấu hình Secrets.")
    st.stop()

# Hàm tải dữ liệu từ máy chủ xuống (ĐÃ SỬA LỖI MẤT DỮ LIỆU)
def load_data():
    try:
        inspector = inspect(conn.engine)
        if not inspector.has_table("wanchi_sanpham"):
            return []
            
        # DÙNG pd.read_sql ĐỂ TRUY VẤN TRỰC TIẾP, BỎ QUA BỘ ĐỆM CACHE
        df = pd.read_sql("SELECT * FROM wanchi_sanpham", con=conn.engine)
        
        if df.empty:
            return []
        return df.to_dict('records') # Chuyển đổi thành List
    except Exception as e:
        st.error(f"Lỗi tải dữ liệu từ máy chủ: {e}")
        return []

# Hàm đồng bộ dữ liệu lên máy chủ
def save_data(data_list):
    try:
        df = pd.DataFrame(data_list)
        if df.empty:
            # Tạo bảng khung nếu danh sách trống để tránh lỗi DB
            df = pd.DataFrame(columns=["Mã SP", "Tên Sản Phẩm", "Giá Vốn", "Giá Đại Lý", "Giá Tiêu Chuẩn"])
        df.to_sql("wanchi_sanpham", con=conn.engine, if_exists='replace', index=False)
    except Exception as e:
        st.error(f"⚠️ Lỗi khi đồng bộ lên đám mây: {e}")

# --- KHỞI TẠO BỘ NHỚ LƯU TRỮ (Lấy dữ liệu từ Neon) ---
if 'danh_sach_sp' not in st.session_state:
    st.session_state.danh_sach_sp = load_data()

# ==========================================
# GIAO DIỆN CHÍNH
# ==========================================
st.title("💰 MODULE: TÍNH GIÁ SẢN XUẤT")
st.write("---")

# --- TẠO 3 TAB ---
tab_tinh_toan, tab_danh_sach, tab_ghep_bo = st.tabs([
    "🧮 1. TÍNH TOÁN & NHẬP LIỆU", 
    "📋 2. DANH SÁCH SẢN PHẨM",
    "🧩 3. GHÉP BỘ"
])

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
            
            # ---> ĐÃ THÊM MỤC TÍNH PHỤ GIA Ở ĐÂY <---
            st.markdown("**Tính Phụ gia:**")
            c_pg1, c_pg2 = st.columns(2)
            don_gia_phu_gia = c_pg1.number_input("Đơn giá phụ gia (VNĐ/kg)", min_value=0, value=0, step=500)
            ti_le_phu_gia = c_pg2.number_input("Tỉ lệ phụ gia (%)", min_value=0.0, value=0.0, step=0.1)
            phu_gia = don_gia_phu_gia * (ti_le_phu_gia * trong_luong / 100) / 1000
            st.caption(f"💡 Chi phí phụ gia: {phu_gia:,.2f} VNĐ/SP")
            # ----------------------------------------
            
            st.markdown("**Tính Khấu hao khuôn:**")
            ck1, ck2 = st.columns(2)
            gia_tri_khuon = ck1.number_input("Giá trị khuôn (VNĐ)", min_value=0, value=0, step=1000000)
            sl_khuon_sx = ck2.number_input("SL khuôn sản xuất (Cái)", min_value=1, value=10000)
            
            khau_hao = gia_tri_khuon / sl_khuon_sx if sl_khuon_sx > 0 else 0
            st.caption(f"💡 Khấu hao dự kiến: {khau_hao:,.2f} VNĐ/SP")
            
            # Cập nhật tổng chi phí khác cộng thêm phụ gia
            cp_khac = bao_bi + phu_kien + phu_gia + khau_hao

    # --- TÍNH TOÁN CƠ BẢN ---
    gvhb = cp_nvl_1sp + cp_may_1sp + cp_khac

    with col_result:
        st.subheader("📊 KẾT QUẢ TÍNH GIÁ")
        
        # PHẦN 2: GIÁ ĐẠI LÝ
        st.markdown("### **Giá Đại Lý**")
        hs_dl = st.number_input("Hệ số LN ĐL", min_value=0.01, max_value=1.0, value=0.6, step=0.01, key="hs_dl")
        gia_dai_ly = gvhb / hs_dl
        st.metric(label="Giá Đại lý", value=f"{round(gia_dai_ly):,} VNĐ")

        # PHẦN 3: GIÁ TIÊU CHUẨN
        st.markdown("### **Giá tiêu chuẩn**")
        hs_tc = st.number_input("Hệ số LN TC", min_value=0.01, max_value=1.0, value=0.6, step=0.01, key="hs_tc")
        gia_tieu_chuan = gia_dai_ly / hs_tc
        st.metric(label="Giá Tiêu chuẩn", value=f"{round(gia_tieu_chuan):,} VNĐ")
        
        st.write("---")
        st.markdown("**Phân tích giá thành:**")
        df_logic = pd.DataFrame({
            "Hạng mục": ["Nguyên Vật Liệu", "Máy sản xuất", "Bao bì & Phụ kiện", "Phụ gia", "Khấu hao khuôn", "GIÁ VỐN (GVHB)"],
            "Số tiền (VNĐ)": [
                f"{cp_nvl_1sp:,.0f}", 
                f"{cp_may_1sp:,.0f}", 
                f"{bao_bi + phu_kien:,.0f}", 
                f"{phu_gia:,.0f}",
                f"{khau_hao:,.0f}", 
                f"{gvhb:,.0f}"
            ]
        })
        st.table(df_logic)

        if st.button("💾 LƯU SẢN PHẨM NÀY", use_container_width=True):
            if ma_sp == "" or ten_sp == "":
                st.warning("⚠️ Vui lòng nhập Mã và Tên sản phẩm!")
            else:
                san_pham_moi = {
                    "Mã SP": ma_sp,
                    "Tên Sản Phẩm": ten_sp,
                    "Giá Vốn": round(gvhb),
                    "Giá Đại Lý": round(gia_dai_ly),
                    "Giá Tiêu Chuẩn": round(gia_tieu_chuan)
                }
                # Tích hợp thêm lệnh Lưu vào DB
                st.session_state.danh_sach_sp.append(san_pham_moi)
                save_data(st.session_state.danh_sach_sp)
                st.success(f"✅ Đã lưu lên đám mây: {ten_sp}")

# ==========================================
# TAB 2: DANH SÁCH SẢN PHẨM 
# ==========================================
with tab_danh_sach:
    st.subheader("📋 BẢNG TỔNG HỢP CÁC PHÂN KHÚC GIÁ")
    if len(st.session_state.danh_sach_sp) > 0:
        df_danh_sach = pd.DataFrame(st.session_state.danh_sach_sp)
        st.dataframe(
            df_danh_sach, 
            use_container_width=True,
            column_config={
                "Giá Vốn": st.column_config.NumberColumn("Giá Vốn", format="%d ₫"),
                "Giá Đại Lý": st.column_config.NumberColumn("Giá Đại Lý", format="%d ₫"),
                "Giá Tiêu Chuẩn": st.column_config.NumberColumn("Giá Tiêu Chuẩn", format="%d ₫"),
            }
        )
        if st.button("🗑️ Xóa toàn bộ danh sách"):
            st.session_state.danh_sach_sp = []
            # Tích hợp xóa trên DB
            save_data(st.session_state.danh_sach_sp)
            st.rerun()
    else:
        st.info("ℹ️ Chưa có dữ liệu sản phẩm.")

# ==========================================
# TAB 3: GHÉP BỘ
# ==========================================
with tab_ghep_bo:
    st.subheader("🧩 THÔNG TIN BỘ SẢN PHẨM")
    col_info1_bo, col_info2_bo = st.columns(2)
    ma_bo = col_info1_bo.text_input("1. Mã Bộ sản phẩm", placeholder="VD: BO001", key="ma_bo")
    ten_bo = col_info2_bo.text_input("2. Tên Bộ sản phẩm", placeholder="VD: Bộ hộp nắp gài", key="ten_bo")
    
    st.markdown("---")

    col_input_bo, col_result_bo = st.columns([1.2, 1])

    with col_input_bo:
        st.subheader("📥 THÔNG SỐ ĐẦU VÀO (BỘ)")
        
        with st.expander("⚙️ NHÁNH 2: GHÉP BỘ PHẬN", expanded=True):
            ds_ten_sp = [sp["Tên Sản Phẩm"] for sp in st.session_state.danh_sach_sp]
            
            chon_than = st.selectbox("Mục 1: Bộ phận thân", ds_ten_sp, key="sb_than_bo") if ds_ten_sp else None
            chon_nap = st.selectbox("Mục 2: Bộ phận nắp", ds_ten_sp, key="sb_nap_bo") if ds_ten_sp else None
            
            von_than = 0
            von_nap = 0
            if chon_than:
                von_than = next((s["Giá Vốn"] for s in st.session_state.danh_sach_sp if s["Tên Sản Phẩm"] == chon_than), 0)
            if chon_nap:
                von_nap = next((s["Giá Vốn"] for s in st.session_state.danh_sach_sp if s["Tên Sản Phẩm"] == chon_nap), 0)
                
            st.info(f"💰 Vốn thân: {von_than:,} ₫ | Vốn nắp: {von_nap:,} ₫")

        with st.expander("📦 NHÁNH 3: CHI PHÍ KHÁC & KHẤU HAO BỘ", expanded=True):
            bb_bo = st.number_input("Bao bì bộ (VNĐ/Bộ)", value=10, key="bb_bo")
            pk_bo = st.number_input("Phụ kiện bộ (VNĐ/Bộ)", value=100, key="pk_bo")
            
            st.markdown("**Tính Khấu hao khuôn bộ:**")
            ck1_bo, ck2_bo = st.columns(2)
            gt_khuon_bo = ck1_bo.number_input("Giá trị khuôn bộ (VNĐ)", min_value=0, value=0, step=1000000, key="gt_bo")
            sl_sx_bo = ck2_bo.number_input("SL sản xuất bộ (Cái)", min_value=1, value=10000, key="sl_bo")
            
            kh_bo = gt_khuon_bo / sl_sx_bo if sl_sx_bo > 0 else 0
            st.caption(f"💡 Khấu hao dự kiến bộ: {kh_bo:,.2f} VNĐ/Bộ")
            cp_khac_bo = bb_bo + pk_bo + kh_bo

    gvhb_bo = von_than + von_nap + cp_khac_bo

    with col_result_bo:
        st.subheader("📊 KẾT QUẢ TÍNH GIÁ BỘ")
        
        st.markdown("### **Giá Đại Lý (Bộ)**")
        hs_dl_bo = st.number_input("Hệ số LN ĐL (Bộ)", min_value=0.01, max_value=1.0, value=0.6, step=0.01, key="hs_dl_bo")
        gia_dl_bo = gvhb_bo / hs_dl_bo
        st.metric(label="Giá Đại lý Bộ", value=f"{round(gia_dl_bo):,} VNĐ")

        st.markdown("### **Giá tiêu chuẩn (Bộ)**")
        hs_tc_bo = st.number_input("Hệ số LN TC (Bộ)", min_value=0.01, max_value=1.0, value=0.6, step=0.01, key="hs_tc_bo")
        gia_tc_bo = gia_dl_bo / hs_tc_bo
        st.metric(label="Giá Tiêu chuẩn Bộ", value=f"{round(gia_tc_bo):,} VNĐ")
        
        st.write("---")
        st.markdown("**Phân tích giá thành bộ:**")
        df_bo = pd.DataFrame({
            "Hạng mục": ["Bộ phận thân", "Bộ phận nắp", "Bao bì & Phụ kiện", "Khấu hao khuôn", "GIÁ VỐN (BỘ)"],
            "Số tiền (VNĐ)": [
                f"{von_than:,.0f}", 
                f"{von_nap:,.0f}", 
                f"{bb_bo + pk_bo:,.0f}", 
                f"{kh_bo:,.0f}", 
                f"{gvhb_bo:,.0f}"
            ]
        })
        st.table(df_bo)

        if st.button("💾 LƯU BỘ SẢN PHẨM NÀY", use_container_width=True, key="btn_bo"):
            if ma_bo == "" or ten_bo == "":
                st.warning("⚠️ Vui lòng nhập Mã và Tên bộ sản phẩm!")
            else:
                san_pham_moi_bo = {
                    "Mã SP": ma_bo,
                    "Tên Sản Phẩm": f"[BỘ] {ten_bo}",
                    "Giá Vốn": round(gvhb_bo),
                    "Giá Đại Lý": round(gia_dl_bo),
                    "Giá Tiêu Chuẩn": round(gia_tc_bo)
                }
                # Tích hợp thêm lệnh Lưu vào DB
                st.session_state.danh_sach_sp.append(san_pham_moi_bo)
                save_data(st.session_state.danh_sach_sp)
                st.success(f"✅ Đã lưu bộ ghép lên đám mây: {ten_bo}")
