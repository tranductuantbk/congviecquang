import streamlit as st
import pandas as pd
from sqlalchemy import inspect

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="Tính Giá Sản Xuất", layout="wide")

# Kiểm tra đăng nhập từ trang Home
if not st.session_state.get("logged_in", False):
    st.warning("🔒 Bạn chưa đăng nhập! Vui lòng quay lại Trang Chủ (Home) để gõ mật khẩu.")
    st.stop()

# ==========================================
# KẾT NỐI NEON (POSTGRESQL)
# ==========================================
try:
    conn = st.connection("postgresql", type="sql")
except Exception as e:
    st.error("Chưa thể kết nối Database Neon. Vui lòng kiểm tra lại file cấu hình Secrets.")
    st.stop()

def load_data():
    try:
        inspector = inspect(conn.engine)
        if not inspector.has_table("wanchi_sanpham"):
            return []
        df = pd.read_sql("SELECT * FROM wanchi_sanpham", con=conn.engine)
        return df.to_dict('records') if not df.empty else []
    except Exception as e:
        return []

def save_data(data_list):
    try:
        df = pd.DataFrame(data_list)
        if df.empty:
            df = pd.DataFrame(columns=["Mã SP", "Tên Sản Phẩm", "Giá Vốn", "Giá Đại Lý", "Giá Tiêu Chuẩn"])
        df.to_sql("wanchi_sanpham", con=conn.engine, if_exists='replace', index=False)
    except Exception as e:
        st.error(f"⚠️ Lỗi khi đồng bộ: {e}")

# ==========================================
# QUẢN LÝ TRẠNG THÁI (SESSION STATE)
# ==========================================
if 'danh_sach_sp' not in st.session_state:
    st.session_state.danh_sach_sp = load_data()

if 'active_tab' not in st.session_state:
    st.session_state.active_tab = "🧮 1. TÍNH TOÁN & NHẬP LIỆU"

if 'edit_mode' not in st.session_state:
    st.session_state.edit_mode = False
    st.session_state.edit_index = None

# Trạng thái dùng để xác nhận xóa
if 'confirm_delete_idx' not in st.session_state:
    st.session_state.confirm_delete_idx = None

# Hàm hỗ trợ lấy dữ liệu điền vào form khi đang ở chế độ Sửa
def get_val(key, default_val):
    return st.session_state[key] if st.session_state.edit_mode and key in st.session_state else default_val

# ==========================================
# GIAO DIỆN ĐIỀU HƯỚNG
# ==========================================
st.title("💰 MODULE: TÍNH GIÁ SẢN XUẤT")

tabs = ["🧮 1. TÍNH TOÁN & NHẬP LIỆU", "📋 2. DANH SÁCH SẢN PHẨM", "🧩 3. GHÉP BỘ"]
st.session_state.active_tab = st.selectbox("Chọn Tab làm việc:", tabs, index=tabs.index(st.session_state.active_tab))
st.write("---")

# ==========================================
# TAB 1: TÍNH TOÁN VÀ NHẬP LIỆU
# ==========================================
if st.session_state.active_tab == "🧮 1. TÍNH TOÁN & NHẬP LIỆU":
    if st.session_state.edit_mode:
        st.info(f"✨ Đang chỉnh sửa sản phẩm: **{st.session_state.get('temp_ten_sp', '')}**")
        if st.button("❌ Hủy chỉnh sửa"):
            st.session_state.edit_mode = False
            st.rerun()

    st.subheader("📝 THÔNG TIN SẢN PHẨM")
    col_info1, col_info2 = st.columns(2)
    ma_sp = col_info1.text_input("1. Mã Sản Phẩm", value=get_val('temp_ma_sp', ""), placeholder="VD: SP001")
    ten_sp = col_info2.text_input("2. Tên Sản Phẩm", value=get_val('temp_ten_sp', ""), placeholder="VD: Khay nhựa đen")
    
    st.markdown("---")
    col_input, col_result = st.columns([1.2, 1])

    with col_input:
        st.subheader("📥 THÔNG SỐ ĐẦU VÀO")
        
        with st.expander("🍀 NHÁNH 1: NGUYÊN VẬT LIỆU", expanded=True):
            c1, c2 = st.columns(2)
            trong_luong = c1.number_input("Trọng lượng (gram)", min_value=0.0, value=float(get_val('temp_trong_luong', 34.0)), step=0.1)
            gia_nhua = c2.number_input("Đơn giá nhựa (VNĐ/kg)", min_value=0, value=int(get_val('temp_gia_nhua', 23000)), step=500)
            cp_nvl_1sp = (trong_luong / 1000) * gia_nhua

        with st.expander("⚙️ NHÁNH 2: MÁY SẢN XUẤT", expanded=True):
            c3, c4 = st.columns(2)
            gia_may_ca = c3.number_input("Giá máy / Ca 8h (VNĐ)", min_value=0, value=int(get_val('temp_gia_may', 1700000)), step=50000)
            chu_ky = c4.number_input("Chu kỳ (giây)", min_value=1.0, value=float(get_val('temp_chu_ky', 40.0)), step=1.0)
            sp_khuon = st.number_input("Số SP / Khuôn", min_value=1, value=int(get_val('temp_sp_khuon', 2)))
            sl_ca = (8 * 3600 / chu_ky) * sp_khuon
            cp_may_1sp = gia_may_ca / sl_ca if sl_ca > 0 else 0

        with st.expander("📦 NHÁNH 3: CHI PHÍ KHÁC & KHẤU HAO", expanded=True):
            bao_bi = st.number_input("Bao bì (VNĐ/SP)", value=int(get_val('temp_bao_bi', 10)))
            phu_kien = st.number_input("Phụ kiện (VNĐ/SP)", value=int(get_val('temp_phu_kien', 100)))
            
            st.markdown("**Tính Phụ gia:**")
            c_pg1, c_pg2 = st.columns(2)
            don_gia_phu_gia = c_pg1.number_input("Đơn giá phụ gia (VNĐ/kg)", min_value=0, value=int(get_val('temp_dg_pg', 0)), step=500)
            ti_le_phu_gia = c_pg2.number_input("Tỉ lệ phụ gia (%)", min_value=0.0, value=float(get_val('temp_tl_pg', 0.0)), step=0.1)
            phu_gia = don_gia_phu_gia * (ti_le_phu_gia * trong_luong / 100) / 1000
            
            st.markdown("**Tính Khấu hao khuôn:**")
            ck1, ck2 = st.columns(2)
            gia_tri_khuon = ck1.number_input("Giá trị khuôn (VNĐ)", min_value=0, value=int(get_val('temp_gia_khuon', 0)), step=1000000)
            sl_khuon_sx = ck2.number_input("SL khuôn sản xuất (Cái)", min_value=1, value=int(get_val('temp_sl_khuon', 10000)))
            khau_hao = gia_tri_khuon / sl_khuon_sx if sl_khuon_sx > 0 else 0
            
            cp_khac_no_kh = bao_bi + phu_kien + phu_gia
            cp_khac = cp_khac_no_kh + khau_hao

    gvhb = cp_nvl_1sp + cp_may_1sp + cp_khac

    with col_result:
        st.subheader("📊 BẢNG PHÂN TÍCH GIÁ THÀNH")
        df_summary = pd.DataFrame({
            "Thành phần cấu tạo": [
                "1. Nguyên vật liệu", 
                "2. Máy sản xuất", 
                "3. Chi phí khác (Bao bì, PK, Phụ gia)", 
                "4. Khấu hao khuôn", 
                "TỔNG GIÁ VỐN (GVHB)"
            ],
            "Thành tiền (VNĐ/SP)": [
                f"{cp_nvl_1sp:,.0f}", 
                f"{cp_may_1sp:,.0f}", 
                f"{cp_khac_no_kh:,.0f}", 
                f"{khau_hao:,.0f}", 
                f"{gvhb:,.0f}"
            ]
        })
        st.table(df_summary)
        
        st.markdown("---")
        hs_dl = st.number_input("Hệ số LN ĐL", min_value=0.01, value=float(get_val('temp_hs_dl', 0.6)), key="hs_dl")
        gia_dai_ly = gvhb / hs_dl
        st.metric(label="Giá Đại lý", value=f"{round(gia_dai_ly):,} VNĐ")

        hs_tc = st.number_input("Hệ số LN TC", min_value=0.01, value=float(get_val('temp_hs_tc', 0.6)), key="hs_tc")
        gia_tieu_chuan = gia_dai_ly / hs_tc
        st.metric(label="Giá Tiêu chuẩn", value=f"{round(gia_tieu_chuan):,} VNĐ")

        if st.button("💾 LƯU / CẬP NHẬT SẢN PHẨM", use_container_width=True):
            if ma_sp == "" or ten_sp == "":
                st.warning("⚠️ Vui lòng nhập Mã và Tên sản phẩm!")
            else:
                # Đã nâng cấp: Lưu toàn bộ thông số đầu vào để sau này gọi lại
                new_data = {
                    "Mã SP": ma_sp,
                    "Tên Sản Phẩm": ten_sp,
                    "Trọng lượng": trong_luong,
                    "Đơn giá nhựa": gia_nhua,
                    "Giá máy": gia_may_ca,
                    "Chu kỳ": chu_ky,
                    "SP Khuôn": sp_khuon,
                    "Bao bì": bao_bi,
                    "Phụ kiện": phu_kien,
                    "Đơn giá phụ gia": don_gia_phu_gia,
                    "Tỉ lệ phụ gia": ti_le_phu_gia,
                    "Giá trị khuôn": gia_tri_khuon,
                    "SL khuôn": sl_khuon_sx,
                    "Hệ số ĐL": hs_dl,
                    "Hệ số TC": hs_tc,
                    "Giá Vốn": round(gvhb),
                    "Giá Đại Lý": round(gia_dai_ly),
                    "Giá Tiêu Chuẩn": round(gia_tieu_chuan)
                }
                
                if st.session_state.edit_mode:
                    st.session_state.danh_sach_sp[st.session_state.edit_index] = new_data
                    st.session_state.edit_mode = False
                else:
                    st.session_state.danh_sach_sp.append(new_data)
                
                save_data(st.session_state.danh_sach_sp)
                st.success("✅ Đã lưu dữ liệu thành công!")
                st.rerun()

# ==========================================
# TAB 2: DANH SÁCH SẢN PHẨM
# ==========================================
elif st.session_state.active_tab == "📋 2. DANH SÁCH SẢN PHẨM":
    st.subheader("📋 DANH SÁCH SẢN PHẨM ĐÃ LƯU")
    if st.session_state.danh_sach_sp:
        df = pd.DataFrame(st.session_state.danh_sach_sp)
        
        # Chỉ hiển thị 5 cột quan trọng nhất cho gọn gàng
        cols_to_show = ["Mã SP", "Tên Sản Phẩm", "Giá Vốn", "Giá Đại Lý", "Giá Tiêu Chuẩn"]
        df_display = df[[c for c in cols_to_show if c in df.columns]]
        st.dataframe(df_display, use_container_width=True)
        
        st.markdown("---")
        st.markdown("**Quản lý:**")
        col1, col2 = st.columns(2)
        
        with col1:
            ten_sp_chon = st.selectbox("Chọn sản phẩm:", [sp["Tên Sản Phẩm"] for sp in st.session_state.danh_sach_sp])
            idx = next(i for i, sp in enumerate(st.session_state.danh_sach_sp) if sp["Tên Sản Phẩm"] == ten_sp_chon)
            
            c_btn1, c_btn2 = st.columns(2)
            if c_btn1.button("✏️ Chỉnh sửa", use_container_width=True):
                sp = st.session_state.danh_sach_sp[idx]
                
                # Bốc toàn bộ 15 thông số lưu vào bộ nhớ tạm
                st.session_state.temp_ma_sp = sp.get("Mã SP", "")
                st.session_state.temp_ten_sp = sp.get("Tên Sản Phẩm", "")
                st.session_state.temp_trong_luong = float(sp.get("Trọng lượng", 34.0))
                st.session_state.temp_gia_nhua = int(sp.get("Đơn giá nhựa", 23000))
                st.session_state.temp_gia_may = int(sp.get("Giá máy", 1700000))
                st.session_state.temp_chu_ky = float(sp.get("Chu kỳ", 40.0))
                st.session_state.temp_sp_khuon = int(sp.get("SP Khuôn", 2))
                st.session_state.temp_bao_bi = int(sp.get("Bao bì", 10))
                st.session_state.temp_phu_kien = int(sp.get("Phụ kiện", 100))
                st.session_state.temp_dg_pg = int(sp.get("Đơn giá phụ gia", 0))
                st.session_state.temp_tl_pg = float(sp.get("Tỉ lệ phụ gia", 0.0))
                st.session_state.temp_gia_khuon = int(sp.get("Giá trị khuôn", 0))
                st.session_state.temp_sl_khuon = int(sp.get("SL khuôn", 10000))
                st.session_state.temp_hs_dl = float(sp.get("Hệ số ĐL", 0.6))
                st.session_state.temp_hs_tc = float(sp.get("Hệ số TC", 0.6))
                
                st.session_state.edit_mode = True
                st.session_state.edit_index = idx
                st.session_state.active_tab = "🧮 1. TÍNH TOÁN & NHẬP LIỆU"
                st.rerun()
                
            if c_btn2.button("🗑️ Xóa", use_container_width=True):
                st.session_state.confirm_delete_idx = idx
                
            # --- HIỆN HỘP THOẠI XÁC NHẬN ---
            if st.session_state.get("confirm_delete_idx") == idx:
                st.warning(f"⚠️ Bạn có chắc chắn muốn xóa sản phẩm **{st.session_state.danh_sach_sp[idx]['Tên Sản Phẩm']}** không?")
                col_yes, col_no = st.columns(2)
                if col_yes.button("✔️ Đồng ý xóa", use_container_width=True, key=f"yes_del"):
                    st.session_state.danh_sach_sp.pop(idx)
                    save_data(st.session_state.danh_sach_sp)
                    st.session_state.confirm_delete_idx = None
                    st.rerun()
                if col_no.button("❌ Hủy", use_container_width=True, key=f"no_del"):
                    st.session_state.confirm_delete_idx = None
                    st.rerun()
    else:
        st.info("Chưa có dữ liệu.")

# ==========================================
# TAB 3: GHÉP BỘ
# ==========================================
else:
    st.subheader("🧩 THÔNG TIN BỘ SẢN PHẨM")
    col_info1_bo, col_info2_bo = st.columns(2)
    ma_bo = col_info1_bo.text_input("1. Mã Bộ sản phẩm", placeholder="VD: BO001", key="ma_bo")
    ten_bo = col_info2_bo.text_input("2. Tên Bộ sản phẩm", placeholder="VD: Bộ hộp nắp gài", key="ten_bo")
    
    st.markdown("---")

    col_input_bo, col_result_bo = st.columns([1.2, 1])

    with col_input_bo:
        st.subheader("📥 THÔNG SỐ ĐẦU VÀO (BỘ)")
        
        with st.expander("⚙️ NHÁNH 2: GHÉP BỘ PHẬN", expanded=True):
            ds_ten_sp = [sp["Tên Sản Phẩm"] for sp in st.session_state.danh_sach_sp if not str(sp["Tên Sản Phẩm"]).startswith("[BỘ]")]
            
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
            cp_khac_bo = bb_bo + pk_bo + kh_bo

    gvhb_bo = von_than + von_nap + cp_khac_bo

    with col_result_bo:
        st.subheader("📊 KẾT QUẢ TÍNH GIÁ BỘ")
        
        hs_dl_bo = st.number_input("Hệ số LN ĐL (Bộ)", min_value=0.01, max_value=1.0, value=0.6, step=0.01, key="hs_dl_bo")
        gia_dl_bo = gvhb_bo / hs_dl_bo
        st.metric(label="Giá Đại lý Bộ", value=f"{round(gia_dl_bo):,} VNĐ")

        hs_tc_bo = st.number_input("Hệ số LN TC (Bộ)", min_value=0.01, max_value=1.0, value=0.6, step=0.01, key="hs_tc_bo")
        gia_tc_bo = gia_dl_bo / hs_tc_bo
        st.metric(label="Giá Tiêu chuẩn Bộ", value=f"{round(gia_tc_bo):,} VNĐ")
        
        st.write("---")
        st.markdown("**Phân tích giá thành bộ:**")
        df_bo = pd.DataFrame({
            "Hạng mục": ["Bộ phận thân", "Bộ phận nắp", "Bao bì & Phụ kiện", "Khấu hao khuôn", "GIÁ VỐN (BỘ)"],
            "Số tiền (VNĐ)": [f"{von_than:,.0f}", f"{von_nap:,.0f}", f"{bb_bo + pk_bo:,.0f}", f"{kh_bo:,.0f}", f"{gvhb_bo:,.0f}"]
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
                st.session_state.danh_sach_sp.append(san_pham_moi_bo)
                save_data(st.session_state.danh_sach_sp)
                st.success(f"✅ Đã lưu bộ ghép lên đám mây: {ten_bo}")
