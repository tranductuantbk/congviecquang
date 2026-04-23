import streamlit as st
import pandas as pd
from sqlalchemy import inspect

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="Tính Giá Gia Công", layout="wide")

# --- KHÓA BẢO MẬT TỪ TRANG CHỦ ---
if not st.session_state.get("logged_in", False):
    st.warning("🔒 Bạn chưa đăng nhập! Vui lòng quay lại Trang Chủ (Home) để gõ mật khẩu.")
    st.stop()

# ==========================================
# KẾT NỐI NEON (POSTGRESQL) & XỬ LÝ DỮ LIỆU
# ==========================================
try:
    conn = st.connection("postgresql", type="sql")
except Exception as e:
    st.error("Chưa thể kết nối Database Neon. Vui lòng kiểm tra lại file cấu hình Secrets.")
    st.stop()

# Hàm tải dữ liệu gia công từ máy chủ xuống
def load_data_gc():
    try:
        inspector = inspect(conn.engine)
        if not inspector.has_table("wanchi_giacong"):
            return []
        df = pd.read_sql("SELECT * FROM wanchi_giacong", con=conn.engine)
        return df.to_dict('records') if not df.empty else []
    except Exception as e:
        return []

# Hàm đồng bộ dữ liệu gia công lên máy chủ
def save_data_gc(data_list):
    try:
        df = pd.DataFrame(data_list)
        if df.empty:
            df = pd.DataFrame(columns=["Mã SP", "Tên Sản Phẩm", "Giá Vốn", "Giá Đại Lý", "Giá Tiêu Chuẩn"])
        df.to_sql("wanchi_giacong", con=conn.engine, if_exists='replace', index=False)
    except Exception as e:
        st.error(f"⚠️ Lỗi khi đồng bộ lên đám mây: {e}")

# --- QUẢN LÝ TRẠNG THÁI (SESSION STATE) ---
if 'danh_sach_gc' not in st.session_state:
    st.session_state.danh_sach_gc = load_data_gc()

if 'active_tab_gc' not in st.session_state:
    st.session_state.active_tab_gc = "🧮 1. TÍNH TOÁN & NHẬP LIỆU"

if 'edit_mode_gc' not in st.session_state:
    st.session_state.edit_mode_gc = False
    st.session_state.edit_index_gc = None

# Hàm hỗ trợ điền dữ liệu cũ vào form khi đang sửa
def get_val_gc(key, default_val):
    return st.session_state[key] if st.session_state.edit_mode_gc and key in st.session_state else default_val

# ==========================================
# GIAO DIỆN CHÍNH (MENU ĐIỀU HƯỚNG)
# ==========================================
st.title("⚙️ MODULE: TÍNH GIÁ GIA CÔNG")

tabs = ["🧮 1. TÍNH TOÁN & NHẬP LIỆU", "📋 2. DANH SÁCH GIA CÔNG"]
st.session_state.active_tab_gc = st.selectbox("Chọn Tab làm việc:", tabs, index=tabs.index(st.session_state.active_tab_gc))
st.write("---")

# ==========================================
# TAB 1: TÍNH TOÁN VÀ NHẬP LIỆU 
# ==========================================
if st.session_state.active_tab_gc == "🧮 1. TÍNH TOÁN & NHẬP LIỆU":
    if st.session_state.edit_mode_gc:
        st.info(f"✨ Đang chỉnh sửa sản phẩm: **{st.session_state.get('temp_ten_sp_gc', '')}**")
        if st.button("❌ Hủy chỉnh sửa"):
            st.session_state.edit_mode_gc = False
            st.rerun()

    st.subheader("📝 THÔNG TIN SẢN PHẨM GIA CÔNG")
    col_info1, col_info2 = st.columns(2)
    ma_sp = col_info1.text_input("1. Mã Sản Phẩm", value=get_val_gc('temp_ma_sp_gc', ""), placeholder="VD: GC001")
    ten_sp = col_info2.text_input("2. Tên Sản Phẩm", value=get_val_gc('temp_ten_sp_gc', ""), placeholder="VD: Khay nhựa đen")
    
    st.markdown("---")

    col_input, col_result = st.columns([1.2, 1])

    with col_input:
        st.subheader("📥 THÔNG SỐ ĐẦU VÀO")
        
        # Nhánh 1: Nguyên Vật Liệu
        with st.expander("🍀 NHÁNH 1: NGUYÊN VẬT LIỆU", expanded=True):
            c1, c2 = st.columns(2)
            trong_luong = c1.number_input("Trọng lượng (gram)", min_value=0.0, value=float(get_val_gc('temp_trong_luong_gc', 34.0)), step=0.1)
            gia_nhua = c2.number_input("Đơn giá nhựa (VNĐ/kg)", min_value=0, value=int(get_val_gc('temp_gia_nhua_gc', 23000)), step=500)
            cp_nvl_1sp = (trong_luong / 1000) * gia_nhua

        # Nhánh 2: Chi phí Sản xuất (Máy)
        with st.expander("⚙️ NHÁNH 2: MÁY SẢN XUẤT", expanded=True):
            c3, c4 = st.columns(2)
            gia_may_ca = c3.number_input("Giá máy / Ca 8h (VNĐ)", min_value=0, value=int(get_val_gc('temp_gia_may_gc', 1700000)), step=50000)
            chu_ky = c4.number_input("Chu kỳ (giây)", min_value=1.0, value=float(get_val_gc('temp_chu_ky_gc', 40.0)), step=1.0)
            sp_khuon = st.number_input("Số SP / Khuôn", min_value=1, value=int(get_val_gc('temp_sp_khuon_gc', 2)))
            sl_ca = (8 * 3600 / chu_ky) * sp_khuon
            cp_may_1sp = gia_may_ca / sl_ca if sl_ca > 0 else 0

        # Nhánh 3: Chi phí khác
        with st.expander("📦 NHÁNH 3: CHI PHÍ KHÁC", expanded=True):
            bao_bi = st.number_input("Bao bì (VNĐ/SP)", value=int(get_val_gc('temp_bao_bi_gc', 10)))
            phu_kien = st.number_input("Phụ kiện (VNĐ/SP)", value=int(get_val_gc('temp_phu_kien_gc', 100)))
            
            st.markdown("**Tính Phụ gia:**")
            c_pg1, c_pg2 = st.columns(2)
            don_gia_phu_gia = c_pg1.number_input("Đơn giá phụ gia (VNĐ/kg)", min_value=0, value=int(get_val_gc('temp_dg_pg_gc', 0)), step=500)
            ti_le_phu_gia = c_pg2.number_input("Tỉ lệ phụ gia (%)", min_value=0.0, value=float(get_val_gc('temp_tl_pg_gc', 0.0)), step=0.1)
            phu_gia = don_gia_phu_gia * (ti_le_phu_gia * trong_luong / 100) / 1000
            
            cp_khac = bao_bi + phu_kien + phu_gia

    # --- TÍNH TOÁN CƠ BẢN ---
    gvhb = cp_nvl_1sp + cp_may_1sp + cp_khac

    with col_result:
        st.subheader("📊 BẢNG PHÂN TÍCH GIÁ THÀNH")
        
        df_summary = pd.DataFrame({
            "Thành phần cấu tạo": [
                "1. Nguyên vật liệu", 
                "2. Máy sản xuất", 
                "3. Chi phí khác (Bao bì, PK, Phụ gia)", 
                "TỔNG GIÁ VỐN (GVHB)"
            ],
            "Thành tiền (VNĐ/SP)": [
                f"{cp_nvl_1sp:,.0f}", 
                f"{cp_may_1sp:,.0f}", 
                f"{cp_khac:,.0f}", 
                f"{gvhb:,.0f}"
            ]
        })
        st.table(df_summary)
        
        st.markdown("---")
        hs_dl = st.number_input("Hệ số LN ĐL", min_value=0.01, value=float(get_val_gc('temp_hs_dl_gc', 0.6)), step=0.01, key="hs_dl_gc")
        gia_dai_ly = gvhb / hs_dl
        st.metric(label="Giá Đại lý", value=f"{round(gia_dai_ly):,} VNĐ")

        hs_tc = st.number_input("Hệ số LN TC", min_value=0.01, value=float(get_val_gc('temp_hs_tc_gc', 0.6)), step=0.01, key="hs_tc_gc")
        gia_tieu_chuan = gia_dai_ly / hs_tc
        st.metric(label="Giá Tiêu chuẩn", value=f"{round(gia_tieu_chuan):,} VNĐ")

        if st.button("💾 LƯU / CẬP NHẬT SẢN PHẨM", use_container_width=True):
            if ma_sp == "" or ten_sp == "":
                st.warning("⚠️ Vui lòng nhập Mã và Tên sản phẩm!")
            else:
                # Lưu toàn bộ chi tiết thông số để gọi lại khi chỉnh sửa
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
                    "Hệ số ĐL": hs_dl,
                    "Hệ số TC": hs_tc,
                    "Giá Vốn": round(gvhb),
                    "Giá Đại Lý": round(gia_dai_ly),
                    "Giá Tiêu Chuẩn": round(gia_tieu_chuan)
                }
                
                if st.session_state.edit_mode_gc:
                    st.session_state.danh_sach_gc[st.session_state.edit_index_gc] = new_data
                    st.session_state.edit_mode_gc = False
                else:
                    st.session_state.danh_sach_gc.append(new_data)
                    
                save_data_gc(st.session_state.danh_sach_gc)
                st.success("✅ Đã lưu dữ liệu thành công!")
                st.rerun()

# ==========================================
# TAB 2: DANH SÁCH SẢN PHẨM GIA CÔNG
# ==========================================
elif st.session_state.active_tab_gc == "📋 2. DANH SÁCH GIA CÔNG":
    st.subheader("📋 BẢNG TỔNG HỢP CÁC PHÂN KHÚC GIÁ GIA CÔNG")
    if len(st.session_state.danh_sach_gc) > 0:
        df_danh_sach = pd.DataFrame(st.session_state.danh_sach_gc)
        
        # Chỉ hiển thị các cột quan trọng nhất cho gọn gàng ở bảng
        cols_to_show = ["Mã SP", "Tên Sản Phẩm", "Giá Vốn", "Giá Đại Lý", "Giá Tiêu Chuẩn"]
        df_display = df_danh_sach[[c for c in cols_to_show if c in df_danh_sach.columns]]
        st.dataframe(df_display, use_container_width=True)
        
        st.markdown("---")
        st.markdown("**Quản lý:**")
        col1, col2 = st.columns([2, 1])
        
        with col1:
            ten_sp_chon = st.selectbox("Chọn sản phẩm để thao tác:", [sp["Tên Sản Phẩm"] for sp in st.session_state.danh_sach_gc])
            idx = next(i for i, sp in enumerate(st.session_state.danh_sach_gc) if sp["Tên Sản Phẩm"] == ten_sp_chon)
            
            c_btn1, c_btn2 = st.columns(2)
            
            # --- NÚT CHỈNH SỬA (NHẢY QUA TAB 1 VÀ ĐIỀN DỮ LIỆU) ---
            if c_btn1.button("✏️ Chỉnh sửa", use_container_width=True):
                sp = st.session_state.danh_sach_gc[idx]
                
                # Bốc toàn bộ thông số kỹ thuật lưu vào bộ nhớ tạm
                st.session_state.temp_ma_sp_gc = sp.get("Mã SP", "")
                st.session_state.temp_ten_sp_gc = sp.get("Tên Sản Phẩm", "")
                st.session_state.temp_trong_luong_gc = float(sp.get("Trọng lượng", 34.0))
                st.session_state.temp_gia_nhua_gc = int(sp.get("Đơn giá nhựa", 23000))
                st.session_state.temp_gia_may_gc = int(sp.get("Giá máy", 1700000))
                st.session_state.temp_chu_ky_gc = float(sp.get("Chu kỳ", 40.0))
                st.session_state.temp_sp_khuon_gc = int(sp.get("SP Khuôn", 2))
                st.session_state.temp_bao_bi_gc = int(sp.get("Bao bì", 10))
                st.session_state.temp_phu_kien_gc = int(sp.get("Phụ kiện", 100))
                st.session_state.temp_dg_pg_gc = int(sp.get("Đơn giá phụ gia", 0))
                st.session_state.temp_tl_pg_gc = float(sp.get("Tỉ lệ phụ gia", 0.0))
                st.session_state.temp_hs_dl_gc = float(sp.get("Hệ số ĐL", 0.6))
                st.session_state.temp_hs_tc_gc = float(sp.get("Hệ số TC", 0.6))
                
                st.session_state.edit_mode_gc = True
                st.session_state.edit_index_gc = idx
                st.session_state.active_tab_gc = "🧮 1. TÍNH TOÁN & NHẬP LIỆU"
                st.rerun()
                
            if c_btn2.button("🗑️ Xóa", use_container_width=True):
                st.session_state.danh_sach_gc.pop(idx)
                save_data_gc(st.session_state.danh_sach_gc)
                st.rerun()
                
        with col2:
            st.write("") 
            st.write("")
            if st.button("🚨 Xóa toàn bộ danh sách", use_container_width=True):
                st.session_state.danh_sach_gc = []
                save_data_gc(st.session_state.danh_sach_gc)
                st.rerun()
    else:
        st.info("ℹ️ Chưa có dữ liệu sản phẩm gia công.")
