import streamlit as st
import pandas as pd
from sqlalchemy import inspect

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="Tính Giá Gia Công", layout="wide")

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
        df = conn.query("SELECT * FROM wanchi_giacong", ttl=0)
        if df.empty:
            return []
        return df.to_dict('records')
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

# --- KHỞI TẠO BỘ NHỚ LƯU TRỮ TỪ NEON ---
if 'danh_sach_gc' not in st.session_state:
    st.session_state.danh_sach_gc = load_data_gc()

st.title("⚙️ MODULE: TÍNH GIÁ GIA CÔNG")
st.write("---")

# --- TẠO 2 TAB (Đã xóa Tab 3) ---
tab_tinh_toan, tab_danh_sach = st.tabs([
    "🧮 1. TÍNH TOÁN & NHẬP LIỆU", 
    "📋 2. DANH SÁCH GIA CÔNG"
])

# ==========================================
# TAB 1: TÍNH TOÁN VÀ NHẬP LIỆU 
# ==========================================
with tab_tinh_toan:
    st.subheader("📝 THÔNG TIN SẢN PHẨM GIA CÔNG")
    col_info1, col_info2 = st.columns(2)
    ma_sp = col_info1.text_input("1. Mã Sản Phẩm", placeholder="VD: GC001")
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

        # Nhánh 3: Chi phí khác
        with st.expander("📦 NHÁNH 3: CHI PHÍ KHÁC", expanded=True):
            bao_bi = st.number_input("Bao bì (VNĐ/SP)", value=10)
            phu_kien = st.number_input("Phụ kiện (VNĐ/SP)", value=100)
            
            st.markdown("**Tính Phụ gia:**")
            c_pg1, c_pg2 = st.columns(2)
            don_gia_phu_gia = c_pg1.number_input("Đơn giá phụ gia (VNĐ/kg)", min_value=0, value=0, step=500)
            ti_le_phu_gia = c_pg2.number_input("Tỉ lệ phụ gia (%)", min_value=0.0, value=0.0, step=0.1)
            phu_gia = don_gia_phu_gia * (ti_le_phu_gia * trong_luong / 100) / 1000
            st.caption(f"💡 Chi phí phụ gia: {phu_gia:,.2f} VNĐ/SP")
            
            cp_khac = bao_bi + phu_kien + phu_gia

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
            "Hạng mục": ["Nguyên Vật Liệu", "Máy sản xuất", "Bao bì & Phụ kiện", "Phụ gia", "GIÁ VỐN (GVHB)"],
            "Số tiền (VNĐ)": [
                f"{cp_nvl_1sp:,.0f}", 
                f"{cp_may_1sp:,.0f}", 
                f"{bao_bi + phu_kien:,.0f}", 
                f"{phu_gia:,.0f}",
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
                # Thêm vào danh sách và lưu lên DB
                st.session_state.danh_sach_gc.append(san_pham_moi)
                save_data_gc(st.session_state.danh_sach_gc)
                st.success(f"✅ Đã lưu lên đám mây: {ten_sp}")

# ==========================================
# TAB 2: DANH SÁCH SẢN PHẨM GIA CÔNG
# ==========================================
with tab_danh_sach:
    st.subheader("📋 BẢNG TỔNG HỢP CÁC PHÂN KHÚC GIÁ GIA CÔNG")
    if len(st.session_state.danh_sach_gc) > 0:
        df_danh_sach = pd.DataFrame(st.session_state.danh_sach_gc)
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
            st.session_state.danh_sach_gc = []
            # Đồng bộ xóa với DB
            save_data_gc(st.session_state.danh_sach_gc)
            st.rerun()
    else:
        st.info("ℹ️ Chưa có dữ liệu sản phẩm gia công.")
