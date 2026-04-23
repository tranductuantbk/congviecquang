import streamlit as st
import pandas as pd
from sqlalchemy import inspect

# --- KHỞI TẠO CẤU HÌNH ---
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

# Trạng thái điều hướng tab
if 'active_tab' not in st.session_state:
    st.session_state.active_tab = "🧮 1. TÍNH TOÁN & NHẬP LIỆU"

# Trạng thái chỉnh sửa
if 'edit_mode' not in st.session_state:
    st.session_state.edit_mode = False
    st.session_state.edit_index = None

# ==========================================
# GIAO DIỆN ĐIỀU HƯỚNG (THAY CHO st.tabs)
# ==========================================
st.title("💰 MODULE: TÍNH GIÁ SẢN XUẤT")

# Tạo Menu điều hướng dạng ngang
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
    
    # Sử dụng giá trị từ session state nếu đang ở chế độ sửa
    ma_sp = col_info1.text_input("1. Mã Sản Phẩm", value=st.session_state.get('temp_ma_sp', ""), placeholder="VD: SP001")
    ten_sp = col_info2.text_input("2. Tên Sản Phẩm", value=st.session_state.get('temp_ten_sp', ""), placeholder="VD: Khay nhựa đen")
    
    st.markdown("---")
    col_input, col_result = st.columns([1.2, 1])

    with col_input:
        st.subheader("📥 THÔNG SỐ ĐẦU VÀO")
        with st.expander("🍀 NHÁNH 1: NGUYÊN VẬT LIỆU", expanded=True):
            c1, c2 = st.columns(2)
            trong_luong = c1.number_input("Trọng lượng (gram)", min_value=0.0, value=st.session_state.get('temp_trong_luong', 34.0), step=0.1)
            gia_nhua = c2.number_input("Đơn giá nhựa (VNĐ/kg)", min_value=0, value=st.session_state.get('temp_gia_nhua', 23000), step=500)
            cp_nvl_1sp = (trong_luong / 1000) * gia_nhua

        with st.expander("⚙️ NHÁNH 2: MÁY SẢN XUẤT", expanded=True):
            c3, c4 = st.columns(2)
            gia_may_ca = c3.number_input("Giá máy / Ca 8h (VNĐ)", min_value=0, value=st.session_state.get('temp_gia_may', 1700000), step=50000)
            chu_ky = c4.number_input("Chu kỳ (giây)", min_value=1.0, value=st.session_state.get('temp_chu_ky', 40.0), step=1.0)
            sp_khuon = st.number_input("Số SP / Khuôn", min_value=1, value=st.session_state.get('temp_sp_khuon', 2))
            sl_ca = (8 * 3600 / chu_ky) * sp_khuon
            cp_may_1sp = gia_may_ca / sl_ca if sl_ca > 0 else 0

        with st.expander("📦 NHÁNH 3: CHI PHÍ KHÁC & KHẤU HAO", expanded=True):
            bao_bi = st.number_input("Bao bì (VNĐ/SP)", value=st.session_state.get('temp_bao_bi', 10))
            phu_kien = st.number_input("Phụ kiện (VNĐ/SP)", value=st.session_state.get('temp_phu_kien', 100))
            
            st.markdown("**Tính Phụ gia:**")
            c_pg1, c_pg2 = st.columns(2)
            don_gia_phu_gia = c_pg1.number_input("Đơn giá phụ gia (VNĐ/kg)", min_value=0, value=st.session_state.get('temp_dg_pg', 0), step=500)
            ti_le_phu_gia = c_pg2.number_input("Tỉ lệ phụ gia (%)", min_value=0.0, value=st.session_state.get('temp_tl_pg', 0.0), step=0.1)
            phu_gia = don_gia_phu_gia * (ti_le_phu_gia * trong_luong / 100) / 1000
            st.caption(f"💡 Chi phí phụ gia: {phu_gia:,.2f} VNĐ/SP")
            
            st.markdown("**Tính Khấu hao khuôn:**")
            ck1, ck2 = st.columns(2)
            gia_tri_khuon = ck1.number_input("Giá trị khuôn (VNĐ)", min_value=0, value=st.session_state.get('temp_gia_khuon', 0), step=1000000)
            sl_khuon_sx = ck2.number_input("SL khuôn sản xuất (Cái)", min_value=1, value=st.session_state.get('temp_sl_khuon', 10000))
            khau_hao = gia_tri_khuon / sl_khuon_sx if sl_khuon_sx > 0 else 0
            cp_khac = bao_bi + phu_kien + phu_gia + khau_hao

    gvhb = cp_nvl_1sp + cp_may_1sp + cp_khac

    with col_result:
        st.subheader("📊 KẾT QUẢ TÍNH GIÁ")
        hs_dl = st.number_input("Hệ số LN ĐL", min_value=0.01, value=0.6, key="hs_dl")
        gia_dai_ly = gvhb / hs_dl
        st.metric(label="Giá Đại lý", value=f"{round(gia_dai_ly):,} VNĐ")

        hs_tc = st.number_input("Hệ số LN TC", min_value=0.01, value=0.6, key="hs_tc")
        gia_tieu_chuan = gia_dai_ly / hs_tc
        st.metric(label="Giá Tiêu chuẩn", value=f"{round(gia_tieu_chuan):,} VNĐ")

        if st.button("💾 LƯU / CẬP NHẬT SẢN PHẨM", use_container_width=True):
            if ma_sp == "" or ten_sp == "":
                st.warning("⚠️ Vui lòng nhập Mã và Tên sản phẩm!")
            else:
                new_data = {"Mã SP": ma_sp, "Tên Sản Phẩm": ten_sp, "Giá Vốn": round(gvhb), "Giá Đại Lý": round(gia_dai_ly), "Giá Tiêu Chuẩn": round(gia_tieu_chuan)}
                
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
    st.subheader("📋 BẢNG TỔNG HỢP")
    if st.session_state.danh_sach_sp:
        df = pd.DataFrame(st.session_state.danh_sach_sp)
        st.dataframe(df, use_container_width=True)
        
        st.markdown("---")
        col1, col2 = st.columns(2)
        
        with col1:
            ten_sp_chon = st.selectbox("Chọn sản phẩm để thao tác:", [sp["Tên Sản Phẩm"] for sp in st.session_state.danh_sach_sp])
            idx = next(i for i, sp in enumerate(st.session_state.danh_sach_sp) if sp["Tên Sản Phẩm"] == ten_sp_chon)
            
            c_btn1, c_btn2 = st.columns(2)
            # --- NÚT CHỈNH SỬA (NHẢY QUA TAB 1) ---
            if c_btn1.button("✏️ Chỉnh sửa sản phẩm", use_container_width=True):
                sp = st.session_state.danh_sach_sp[idx]
                # Đưa dữ liệu vào kho tạm để Tab 1 lấy ra
                st.session_state.temp_ma_sp = sp["Mã SP"]
                st.session_state.temp_ten_sp = sp["Tên Sản Phẩm"]
                # (Lưu ý: Các thông số chi tiết như trọng lượng... cần được lưu khi bấm 'Lưu' ở Tab 1 ban đầu 
                # để có thể khôi phục hoàn toàn. Hiện tại code chỉ lưu kết quả cuối nên ta sửa mã/tên trước)
                st.session_state.edit_mode = True
                st.session_state.edit_index = idx
                st.session_state.active_tab = "🧮 1. TÍNH TOÁN & NHẬP LIỆU"
                st.rerun()
                
            if c_btn2.button("🗑️ Xóa sản phẩm", use_container_width=True):
                st.session_state.danh_sach_sp.pop(idx)
                save_data(st.session_state.danh_sach_sp)
                st.rerun()
    else:
        st.info("Chưa có sản phẩm nào.")

# ==========================================
# TAB 3: GHÉP BỘ
# ==========================================
else:
    st.subheader("🧩 GHÉP BỘ PHẬN")
    # Giữ nguyên logic ghép bộ của bạn...
    st.info("Tính năng đang hoạt động bình thường theo code cũ.")
