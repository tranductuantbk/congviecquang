import streamlit as st
import pandas as pd
from sqlalchemy import inspect
import io
from fpdf import FPDF

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
        # Xử lý lỗi Cold Start của Neon DB
        st.warning("⏳ Máy chủ dữ liệu đang khởi động. Vui lòng đợi 3 giây rồi tải lại.")
        return None

def save_data(data_list):
    try:
        df = pd.DataFrame(data_list)
        if df.empty:
            df = pd.DataFrame(columns=["Mã SP", "Tên Sản Phẩm", "Trọng lượng", "Đơn giá nhựa", "Giá máy", "Chu kỳ", "SP Khuôn", "Bao bì", "Phụ kiện", "Đơn giá phụ gia", "Tỉ lệ phụ gia", "Giá trị khuôn", "SL khuôn", "Hệ số ĐL", "Hệ số TC", "Giá Vốn", "Giá Đại Lý", "Giá Công ty"])
        df.to_sql("wanchi_sanpham", con=conn.engine, if_exists='replace', index=False)
    except Exception as e:
        pass

# ==========================================
# QUẢN LÝ TRẠNG THÁI (SESSION STATE)
# ==========================================
if "danh_sach_sp" not in st.session_state or st.session_state["danh_sach_sp"] is None:
    st.session_state["danh_sach_sp"] = load_data()

# Cứu cánh an toàn nếu DB chưa lên
if st.session_state["danh_sach_sp"] is None:
    st.session_state["danh_sach_sp"] = []

if "is_editing_sx" not in st.session_state:
    st.session_state["is_editing_sx"] = False
    st.session_state["edit_index_sx"] = None

if "confirm_delete_idx_sx" not in st.session_state:
    st.session_state["confirm_delete_idx_sx"] = None

danh_sach_tabs = ["🧮 1. TÍNH TOÁN & NHẬP LIỆU", "📋 2. DANH SÁCH SẢN PHẨM", "🧩 3. GHÉP BỘ", "⚖️ 4. ĐỊNH LƯỢNG SẢN PHẨM"]

if "current_tab_sx" not in st.session_state:
    st.session_state["current_tab_sx"] = danh_sach_tabs[0]

def sync_tab_sx():
    st.session_state["current_tab_sx"] = st.session_state["radio_menu_sx"]

# ==========================================
# GIAO DIỆN ĐIỀU HƯỚNG
# ==========================================
st.title("💰 MODULE: TÍNH GIÁ SẢN XUẤT")

st.radio(
    "Menu chức năng:", 
    danh_sach_tabs, 
    index=danh_sach_tabs.index(st.session_state["current_tab_sx"]),
    horizontal=True, 
    key="radio_menu_sx",
    on_change=sync_tab_sx,
    label_visibility="collapsed"
)
st.write("---")

# ==========================================
# TAB 1: TÍNH TOÁN VÀ NHẬP LIỆU
# ==========================================
if st.session_state["current_tab_sx"] == "🧮 1. TÍNH TOÁN & NHẬP LIỆU":
    if st.session_state.get("sx_success_msg"):
        st.success(st.session_state["sx_success_msg"])
        st.session_state["sx_success_msg"] = ""

    if st.session_state["is_editing_sx"]:
        st.info("✨ **ĐANG TRONG CHẾ ĐỘ CHỈNH SỬA SẢN PHẨM**")
        if st.button("❌ Hủy chỉnh sửa / Thêm mới"):
            st.session_state["is_editing_sx"] = False
            st.rerun()

    st.subheader("📝 THÔNG TIN SẢN PHẨM")
    col_info1, col_info2 = st.columns(2)
    ma_sp = col_info1.text_input("1. Mã Sản Phẩm", key="sx_ma_in")
    ten_sp = col_info2.text_input("2. Tên Sản Phẩm", key="sx_ten_in")
    
    st.markdown("---")
    col_input, col_result = st.columns([1.2, 1])

    with col_input:
        st.subheader("📥 THÔNG SỐ ĐẦU VÀO")
        
        with st.expander("🍀 NHÁNH 1: NGUYÊN VẬT LIỆU", expanded=True):
            c1, c2 = st.columns(2)
            trong_luong = c1.number_input("Trọng lượng (gram)", value=st.session_state.get("sx_tl_in", 34.0), step=0.1, key="sx_tl_in_ui")
            gia_nhua = c2.number_input("Đơn giá nhựa (VNĐ/kg)", value=st.session_state.get("sx_gia_nhua_in", 23000), step=500, key="sx_gia_nhua_in_ui")
            cp_nvl_1sp = (trong_luong / 1000) * gia_nhua

        with st.expander("⚙️ NHÁNH 2: MÁY SẢN XUẤT", expanded=True):
            c3, c4 = st.columns(2)
            gia_may_ca = c3.number_input("Giá máy / Ca 8h (VNĐ)", value=st.session_state.get("sx_gia_may_in", 1700000), step=50000, key="sx_gia_may_in_ui")
            chu_ky = c4.number_input("Chu kỳ (giây)", value=st.session_state.get("sx_chu_ky_in", 40.0), step=1.0, key="sx_chu_ky_in_ui")
            sp_khuon = st.number_input("Số SP / Khuôn", value=st.session_state.get("sx_sp_khuon_in", 2), min_value=1, key="sx_sp_khuon_in_ui")
            sl_ca = (8 * 3600 / chu_ky) * sp_khuon
            cp_may_1sp = gia_may_ca / sl_ca if sl_ca > 0 else 0

        with st.expander("📦 NHÁNH 3: CHI PHÍ KHÁC & KHẤU HAO", expanded=True):
            bao_bi = st.number_input("Bao bì (VNĐ/SP)", value=st.session_state.get("sx_bao_bi_in", 10), key="sx_bao_bi_in_ui")
            phu_kien = st.number_input("Phụ kiện (VNĐ/SP)", value=st.session_state.get("sx_phu_kien_in", 100), key="sx_phu_kien_in_ui")
            
            st.markdown("**Tính Phụ gia:**")
            c_pg1, c_pg2 = st.columns(2)
            don_gia_phu_gia = c_pg1.number_input("Đơn giá phụ gia (VNĐ/kg)", value=st.session_state.get("sx_dg_pg_in", 0), step=500, key="sx_dg_pg_in_ui")
            ti_le_phu_gia = c_pg2.number_input("Tỉ lệ phụ gia (%)", value=st.session_state.get("sx_tl_pg_in", 0.0), step=0.1, key="sx_tl_pg_in_ui")
            phu_gia = don_gia_phu_gia * (ti_le_phu_gia * trong_luong / 100) / 1000
            
            st.markdown("**Tính Khấu hao khuôn:**")
            ck1, ck2 = st.columns(2)
            gia_tri_khuon = ck1.number_input("Giá trị khuôn (VNĐ)", value=st.session_state.get("sx_gia_khuon_in", 0), step=1000000, key="sx_gia_khuon_in_ui")
            sl_khuon_sx = ck2.number_input("SL khuôn sản xuất (Cái)", value=st.session_state.get("sx_sl_khuon_in", 10000), min_value=1, key="sx_sl_khuon_in_ui")
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
        hs_dl = st.number_input("Hệ số LN ĐL", value=st.session_state.get("sx_hs_dl_in", 0.6), min_value=0.01, step=0.01, key="sx_hs_dl_in_ui")
        gia_dai_ly = gvhb / hs_dl
        st.metric(label="Giá Đại lý", value=f"{round(gia_dai_ly):,} VNĐ")

        hs_tc = st.number_input("Hệ số LN TC", value=st.session_state.get("sx_hs_tc_in", 0.55), min_value=0.01, step=0.01, key="sx_hs_tc_in_ui")
        gia_cong_ty = gia_dai_ly / hs_tc
        st.metric(label="Giá Công ty", value=f"{round(gia_cong_ty):,} VNĐ")

        if st.button("💾 LƯU / CẬP NHẬT SẢN PHẨM", use_container_width=True):
            if ma_sp == "" or ten_sp == "":
                st.warning("⚠️ Vui lòng nhập Mã và Tên sản phẩm!")
            else:
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
                    "Giá Công ty": round(gia_cong_ty)
                }
                
                if st.session_state["is_editing_sx"]:
                    st.session_state["danh_sach_sp"][st.session_state["edit_index_sx"]] = new_data
                    st.session_state["is_editing_sx"] = False
                else:
                    st.session_state["danh_sach_sp"].append(new_data)
                
                save_data(st.session_state["danh_sach_sp"])
                
                st.session_state["sx_success_msg"] = f"✅ Đã lưu sản phẩm '{ten_sp}' thành công! Bạn có thể nhập tiếp sản phẩm mới."
                st.rerun()

# ==========================================
# TAB 2: DANH SÁCH SẢN PHẨM
# ==========================================
elif st.session_state["current_tab_sx"] == "📋 2. DANH SÁCH SẢN PHẨM":
    st.subheader("📋 DANH SÁCH SẢN PHẨM ĐÃ LƯU")
    
    col_ref1, col_ref2 = st.columns([8, 2])
    if col_ref2.button("🔄 Tải lại dữ liệu (Refresh)"):
        st.session_state["danh_sach_sp"] = load_data()
        if st.session_state["danh_sach_sp"] is None:
            st.session_state["danh_sach_sp"] = []
        st.rerun()

    if st.session_state["danh_sach_sp"]:
        df = pd.DataFrame(st.session_state["danh_sach_sp"])
        
        cols_to_show = ["Mã SP", "Tên Sản Phẩm", "Giá Vốn", "Giá Đại Lý", "Giá Công ty"]
        # Hỗ trợ hiển thị đúng nếu dữ liệu cũ còn lưu cột "Giá Tiêu Chuẩn"
        if "Giá Tiêu Chuẩn" in df.columns and "Giá Công ty" not in df.columns:
            df.rename(columns={"Giá Tiêu Chuẩn": "Giá Công ty"}, inplace=True)
            
        df_display = df[[c for c in cols_to_show if c in df.columns]]
        st.dataframe(df_display, use_container_width=True)
        
        st.markdown("---")
        st.markdown("**Quản lý:**")
        col1, col2 = st.columns(2)
        
        with col1:
            ten_sp_chon = st.selectbox("Chọn sản phẩm:", [sp["Tên Sản Phẩm"] for sp in st.session_state["danh_sach_sp"]])
            idx = next(i for i, sp in enumerate(st.session_state["danh_sach_sp"]) if sp["Tên Sản Phẩm"] == ten_sp_chon)
            
            c_btn1, c_btn2 = st.columns(2)
            if c_btn1.button("✏️ Chỉnh sửa", use_container_width=True):
                sp = st.session_state["danh_sach_sp"][idx]
                
                st.session_state["sx_ma_in"] = sp.get("Mã SP", "")
                st.session_state["sx_ten_in"] = sp.get("Tên Sản Phẩm", "")
                st.session_state["sx_tl_in"] = float(sp.get("Trọng lượng", 34.0)) if isinstance(sp.get("Trọng lượng", 34.0), (int, float)) else 34.0
                st.session_state["sx_gia_nhua_in"] = int(sp.get("Đơn giá nhựa", 23000))
                st.session_state["sx_gia_may_in"] = int(sp.get("Giá máy", 1700000))
                st.session_state["sx_chu_ky_in"] = float(sp.get("Chu kỳ", 40.0))
                st.session_state["sx_sp_khuon_in"] = int(sp.get("SP Khuôn", 2))
                st.session_state["sx_bao_bi_in"] = int(sp.get("Bao bì", 10))
                st.session_state["sx_phu_kien_in"] = int(sp.get("Phụ kiện", 100))
                st.session_state["sx_dg_pg_in"] = int(sp.get("Đơn giá phụ gia", 0))
                st.session_state["sx_tl_pg_in"] = float(sp.get("Tỉ lệ phụ gia", 0.0))
                st.session_state["sx_gia_khuon_in"] = int(sp.get("Giá trị khuôn", 0))
                st.session_state["sx_sl_khuon_in"] = int(sp.get("SL khuôn", 10000))
                st.session_state["sx_hs_dl_in"] = float(sp.get("Hệ số ĐL", 0.6))
                st.session_state["sx_hs_tc_in"] = float(sp.get("Hệ số TC", 0.55))
                
                st.session_state["is_editing_sx"] = True
                st.session_state["edit_index_sx"] = idx
                st.session_state["current_tab_sx"] = danh_sach_tabs[0]
                st.rerun()
                
            if c_btn2.button("🗑️ Xóa", use_container_width=True):
                st.session_state["confirm_delete_idx_sx"] = idx
                
            if st.session_state.get("confirm_delete_idx_sx") == idx:
                st.warning(f"⚠️ Bạn có chắc chắn muốn xóa sản phẩm **{st.session_state['danh_sach_sp'][idx]['Tên Sản Phẩm']}** không?")
                col_yes, col_no = st.columns(2)
                if col_yes.button("✔️ Đồng ý xóa", use_container_width=True, key=f"yes_del_sx"):
                    st.session_state["danh_sach_sp"].pop(idx)
                    save_data(st.session_state["danh_sach_sp"])
                    st.session_state["confirm_delete_idx_sx"] = None
                    st.rerun()
                if col_no.button("❌ Hủy", use_container_width=True, key=f"no_del_sx"):
                    st.session_state["confirm_delete_idx_sx"] = None
                    st.rerun()
    else:
        st.info("Chưa có dữ liệu.")

# ==========================================
# TAB 3: GHÉP BỘ
# ==========================================
elif st.session_state["current_tab_sx"] == "🧩 3. GHÉP BỘ":
    st.subheader("🧩 THÔNG TIN BỘ SẢN PHẨM")
    col_info1_bo, col_info2_bo = st.columns(2)
    ma_bo = col_info1_bo.text_input("1. Mã Bộ sản phẩm", placeholder="VD: BO001", key="ma_bo")
    ten_bo = col_info2_bo.text_input("2. Tên Bộ sản phẩm", placeholder="VD: Bộ hộp nắp gài", key="ten_bo")
    
    st.markdown("---")

    col_input_bo, col_result_bo = st.columns([1.2, 1])

    with col_input_bo:
        st.subheader("📥 THÔNG SỐ ĐẦU VÀO (BỘ)")
        
        with st.expander("⚙️ NHÁNH 2: GHÉP BỘ PHẬN", expanded=True):
            ds_ten_sp = [sp["Tên Sản Phẩm"] for sp in st.session_state["danh_sach_sp"] if not str(sp["Tên Sản Phẩm"]).startswith("[BỘ]")]
            
            chon_than = st.selectbox("Mục 1: Bộ phận thân", ds_ten_sp, key="sb_than_bo") if ds_ten_sp else None
            chon_nap = st.selectbox("Mục 2: Bộ phận nắp", ds_ten_sp, key="sb_nap_bo") if ds_ten_sp else None
            
            von_than = 0
            von_nap = 0
            if chon_than:
                von_than = next((s["Giá Vốn"] for s in st.session_state["danh_sach_sp"] if s["Tên Sản Phẩm"] == chon_than), 0)
            if chon_nap:
                von_nap = next((s["Giá Vốn"] for s in st.session_state["danh_sach_sp"] if s["Tên Sản Phẩm"] == chon_nap), 0)
                
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
        gia_cong_ty_bo = gia_dl_bo / hs_tc_bo
        st.metric(label="Giá Công ty Bộ", value=f"{round(gia_cong_ty_bo):,} VNĐ")
        
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
                tl_than = next((s.get("Trọng lượng", 0) for s in st.session_state["danh_sach_sp"] if s["Tên Sản Phẩm"] == chon_than), 0)
                tl_nap = next((s.get("Trọng lượng", 0) for s in st.session_state["danh_sach_sp"] if s["Tên Sản Phẩm"] == chon_nap), 0)
                
                san_pham_moi_bo = {
                    "Mã SP": ma_bo,
                    "Tên Sản Phẩm": f"[BỘ] {ten_bo}",
                    "Trọng lượng": f"Thân: {tl_than}g | Nắp: {tl_nap}g",
                    "Giá Vốn": round(gvhb_bo),
                    "Giá Đại Lý": round(gia_dl_bo),
                    "Giá Công ty": round(gia_cong_ty_bo)
                }
                st.session_state["danh_sach_sp"].append(san_pham_moi_bo)
                save_data(st.session_state["danh_sach_sp"])
                st.success(f"✅ Đã lưu bộ ghép lên đám mây: {ten_bo}")

# ==========================================
# TAB 4: ĐỊNH LƯỢNG SẢN PHẨM
# ==========================================
elif st.session_state["current_tab_sx"] == "⚖️ 4. ĐỊNH LƯỢNG SẢN PHẨM":
    st.subheader("⚖️ BẢNG ĐỊNH LƯỢNG SẢN PHẨM")
    
    col_ref3, col_ref4 = st.columns([8, 2])
    if col_ref4.button("🔄 Tải lại dữ liệu"):
        st.session_state["danh_sach_sp"] = load_data()
        st.rerun()
    
    if st.session_state["danh_sach_sp"]:
        du_lieu_hien_thi = []
        
        for sp in st.session_state["danh_sach_sp"]:
            ma_sp = sp.get("Mã SP", "")
            ten_sp = sp.get("Tên Sản Phẩm", "")
            trong_luong = sp.get("Trọng lượng", "")
            
            if isinstance(trong_luong, (int, float)):
                tl_hien_thi = f"{trong_luong} g"
            elif isinstance(trong_luong, str):
                tl_hien_thi = trong_luong
            else:
                tl_hien_thi = "N/A"
                
            du_lieu_hien_thi.append({
                "Mã SP": ma_sp,
                "Tên Sản Phẩm": ten_sp,
                "Định Lượng (Trọng lượng)": tl_hien_thi
            })
            
        df_dinh_luong = pd.DataFrame(du_lieu_hien_thi)
        st.dataframe(df_dinh_luong, use_container_width=True)
        
        # --- XUẤT DỮ LIỆU ---
        st.write("---")
        st.markdown("### 📥 XUẤT DỮ LIỆU BÁO CÁO")
        col_export1, col_export2 = st.columns(2)
        
        with col_export1:
            # Xuất Excel (CSV)
            csv_data = df_dinh_luong.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="📊 Tải xuống file Excel (CSV)",
                data=csv_data,
                file_name='Bang_Dinh_Luong_San_Pham.csv',
                mime='text/csv',
                use_container_width=True
            )
            
        with col_export2:
            # Hàm xử lý xuất PDF bằng thư viện fpdf2
            def tao_file_pdf(dataframe):
                pdf = FPDF()
                pdf.add_page()
                
                # NẠP FONT ĐÃ CÀI ĐẶT
                try:
                    # Chú ý: File arial.ttf phải nằm cùng thư mục với file code này
                    pdf.add_font("CustomFont", "", "arial.ttf", uni=True)
                    pdf.set_font("CustomFont", size=16)
                except Exception as e:
                    st.error(f"Lỗi nạp font: Đảm bảo bạn đã chép file 'arial.ttf' vào cùng thư mục. Chi tiết lỗi: {e}")
                    pdf.set_font("Arial", size=16)
                
                # Tiêu đề
                pdf.cell(0, 10, txt="BẢNG ĐỊNH LƯỢNG SẢN PHẨM (WANCHI)", ln=True, align='C')
                pdf.ln(5)
                
                # Thiết lập cỡ chữ cho bảng
                try:
                    pdf.set_font("CustomFont", size=10)
                except:
                    pdf.set_font("Arial", size=10)
                    
                # Tiêu đề cột
                pdf.cell(30, 10, "Mã SP", border=1, align='C')
                pdf.cell(90, 10, "Tên Sản Phẩm", border=1, align='C')
                pdf.cell(70, 10, "Trọng Lượng", border=1, align='C')
                pdf.ln()
                
                # Nội dung dữ liệu
                for i, row in dataframe.iterrows():
                    ma = str(row['Mã SP'])
                    ten = str(row['Tên Sản Phẩm'])
                    tl = str(row['Định Lượng (Trọng lượng)'])
                    
                    pdf.cell(30, 10, ma, border=1, align='C')
                    pdf.cell(90, 10, ten, border=1, align='L')
                    pdf.cell(70, 10, tl, border=1, align='C')
                    pdf.ln()
                
                return bytes(pdf.output())

            # Nút tải PDF
            pdf_bytes = tao_file_pdf(df_dinh_luong)
            st.download_button(
                label="📄 Tải xuống file PDF",
                data=pdf_bytes,
                file_name='Bang_Dinh_Luong_San_Pham.pdf',
                mime='application/pdf',
                use_container_width=True
            )

    else:
        st.info("Chưa có dữ liệu sản phẩm.")
