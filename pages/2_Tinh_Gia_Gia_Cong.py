import streamlit as st
import pandas as pd
from sqlalchemy import inspect
import io
from fpdf import FPDF

st.set_page_config(page_title="Tính Giá Gia Công", layout="wide")

# --- KHÓA BẢO MẬT TỪ TRANG CHỦ ---
if not st.session_state.get("logged_in", False):
    st.warning("🔒 Bạn chưa đăng nhập! Vui lòng quay lại Trang Chủ (Home) để gõ mật khẩu.")
    st.stop()

# ==========================================
# KẾT NỐI NEON (POSTGRESQL)
# ==========================================
try:
    conn = st.connection("postgresql", type="sql")
except Exception as e:
    st.error("Chưa thể kết nối Database Neon.")
    st.stop()

def load_data_gc():
    try:
        inspector = inspect(conn.engine)
        if not inspector.has_table("wanchi_giacong"):
            return []
        df = pd.read_sql("SELECT * FROM wanchi_giacong", con=conn.engine)
        return df.to_dict('records') if not df.empty else []
    except Exception as e:
        # Xử lý lỗi Cold Start của Neon DB
        st.warning("⏳ Máy chủ dữ liệu đang khởi động. Vui lòng đợi 3 giây rồi tải lại.")
        return None

def save_data_gc(data_list):
    try:
        df = pd.DataFrame(data_list)
        if df.empty:
            df = pd.DataFrame(columns=["Mã SP", "Tên Sản Phẩm", "Trọng lượng", "Đơn giá nhựa", "Giá máy", "Chu kỳ", "SP Khuôn", "Bao bì", "Phụ kiện", "Đơn giá phụ gia", "Tỉ lệ phụ gia", "Hệ số ĐL", "Hệ số TC", "Giá Vốn", "Giá Đại Lý", "Giá Công ty"])
        df.to_sql("wanchi_giacong", con=conn.engine, if_exists='replace', index=False)
    except Exception: pass

# ==========================================
# KHỞI TẠO BỘ NHỚ LƯU TRỮ 
# ==========================================
if "danh_sach_gc" not in st.session_state or st.session_state["danh_sach_gc"] is None:
    st.session_state["danh_sach_gc"] = load_data_gc()

# Cứu cánh an toàn nếu DB chưa lên
if st.session_state["danh_sach_gc"] is None:
    st.session_state["danh_sach_gc"] = []

if "confirm_delete_idx_gc" not in st.session_state:
    st.session_state["confirm_delete_idx_gc"] = None

if "is_editing_gc" not in st.session_state:
    st.session_state["is_editing_gc"] = False
    st.session_state["edit_index_gc"] = None

danh_sach_tabs = ["🧮 1. TÍNH TOÁN & NHẬP LIỆU", "📋 2. DANH SÁCH GIA CÔNG", "⚖️ 3. ĐỊNH LƯỢNG SẢN PHẨM"]

if "current_tab_gc" not in st.session_state:
    st.session_state["current_tab_gc"] = danh_sach_tabs[0]

# Hàm đồng bộ khi người dùng click vào thanh Menu
def sync_tab():
    st.session_state["current_tab_gc"] = st.session_state["radio_menu_gc"]

st.title("⚙️ MODULE: TÍNH GIÁ GIA CÔNG")

# Thanh Menu an toàn
st.radio(
    "Menu chức năng:", 
    danh_sach_tabs, 
    index=danh_sach_tabs.index(st.session_state["current_tab_gc"]),
    horizontal=True, 
    key="radio_menu_gc",
    on_change=sync_tab,
    label_visibility="collapsed"
)
st.write("---")

# ==========================================
# TAB 1: TÍNH TOÁN VÀ NHẬP LIỆU
# ==========================================
if st.session_state["current_tab_gc"] == "🧮 1. TÍNH TOÁN & NHẬP LIỆU":
    if st.session_state.get("gc_success_msg"):
        st.success(st.session_state["gc_success_msg"])
        st.session_state["gc_success_msg"] = ""

    if st.session_state["is_editing_gc"]:
        st.info("✨ **ĐANG TRONG CHẾ ĐỘ CHỈNH SỬA SẢN PHẨM GIA CÔNG**")
        if st.button("❌ Hủy chỉnh sửa / Thêm mới"):
            st.session_state["is_editing_gc"] = False
            st.rerun()

    st.subheader("📝 THÔNG TIN SẢN PHẨM GIA CÔNG")
    col_info1, col_info2 = st.columns(2)
    ma_sp = col_info1.text_input("1. Mã Sản Phẩm", key="gc_ma_in")
    ten_sp = col_info2.text_input("2. Tên Sản Phẩm", key="gc_ten_in")
    
    st.markdown("---")
    col_input, col_result = st.columns([1.2, 1])

    with col_input:
        st.subheader("📥 THÔNG SỐ ĐẦU VÀO")
        
        with st.expander("🍀 NHÁNH 1: NGUYÊN VẬT LIỆU", expanded=True):
            c1, c2 = st.columns(2)
            trong_luong = c1.number_input("Trọng lượng (gram)", value=st.session_state.get("gc_tl_in", 34.0), step=0.1, key="gc_tl_in_ui")
            gia_nhua = c2.number_input("Đơn giá nhựa (VNĐ/kg)", value=st.session_state.get("gc_gia_nhua_in", 23000), step=500, key="gc_gia_nhua_in_ui")
            cp_nvl_1sp = (trong_luong / 1000) * gia_nhua

        with st.expander("⚙️ NHÁNH 2: MÁY SẢN XUẤT", expanded=True):
            c3, c4 = st.columns(2)
            gia_may_ca = c3.number_input("Giá máy / Ca 8h (VNĐ)", value=st.session_state.get("gc_gia_may_in", 1700000), step=50000, key="gc_gia_may_in_ui")
            chu_ky = c4.number_input("Chu kỳ (giây)", value=st.session_state.get("gc_chu_ky_in", 40.0), step=1.0, key="gc_chu_ky_in_ui")
            sp_khuon = st.number_input("Số SP / Khuôn", value=st.session_state.get("gc_sp_khuon_in", 2), min_value=1, key="gc_sp_khuon_in_ui")
            sl_ca = (8 * 3600 / chu_ky) * sp_khuon
            cp_may_1sp = gia_may_ca / sl_ca if sl_ca > 0 else 0

        with st.expander("📦 NHÁNH 3: CHI PHÍ KHÁC", expanded=True):
            bao_bi = st.number_input("Bao bì (VNĐ/SP)", value=st.session_state.get("gc_bao_bi_in", 10), key="gc_bao_bi_in_ui")
            phu_kien = st.number_input("Phụ kiện (VNĐ/SP)", value=st.session_state.get("gc_phu_kien_in", 100), key="gc_phu_kien_in_ui")
            
            st.markdown("**Tính Phụ gia:**")
            c_pg1, c_pg2 = st.columns(2)
            don_gia_phu_gia = c_pg1.number_input("Đơn giá phụ gia (VNĐ/kg)", value=st.session_state.get("gc_dg_pg_in", 0), step=500, key="gc_dg_pg_in_ui")
            ti_le_phu_gia = c_pg2.number_input("Tỉ lệ phụ gia (%)", value=st.session_state.get("gc_tl_pg_in", 0.0), step=0.1, key="gc_tl_pg_in_ui")
            phu_gia = don_gia_phu_gia * (ti_le_phu_gia * trong_luong / 100) / 1000
            st.caption(f"💡 Chi phí phụ gia: {phu_gia:,.2f} VNĐ/SP")
            
            cp_khac = bao_bi + phu_kien + phu_gia

    gvhb = cp_nvl_1sp + cp_may_1sp + cp_khac

    with col_result:
        st.subheader("📊 BẢNG PHÂN TÍCH GIÁ THÀNH")
        df_summary = pd.DataFrame({
            "Thành phần": ["1. Nguyên vật liệu", "2. Máy sản xuất", "3. Chi phí khác (Bao bì, PK, Phụ gia)", "TỔNG GIÁ VỐN"],
            "Thành tiền (VNĐ)": [f"{cp_nvl_1sp:,.0f}", f"{cp_may_1sp:,.0f}", f"{cp_khac:,.0f}", f"{gvhb:,.0f}"]
        })
        st.table(df_summary)
        
        st.markdown("---")
        hs_dl = st.number_input("Hệ số LN ĐL", value=st.session_state.get("gc_hs_dl_in", 0.6), min_value=0.01, step=0.01, key="gc_hs_dl_in_ui")
        gia_dai_ly = gvhb / hs_dl
        st.metric(label="Giá Đại lý", value=f"{round(gia_dai_ly):,} VNĐ")

        hs_tc = st.number_input("Hệ số LN TC", value=st.session_state.get("gc_hs_tc_in", 0.6), min_value=0.01, step=0.01, key="gc_hs_tc_in_ui")
        gia_cong_ty = gia_dai_ly / hs_tc
        st.metric(label="Giá Công ty", value=f"{round(gia_cong_ty):,} VNĐ")

        if st.button("💾 LƯU / CẬP NHẬT SẢN PHẨM", use_container_width=True):
            if ma_sp == "" or ten_sp == "":
                st.warning("⚠️ Vui lòng nhập Mã và Tên sản phẩm!")
            else:
                new_data = {
                    "Mã SP": ma_sp, "Tên Sản Phẩm": ten_sp, "Trọng lượng": trong_luong, "Đơn giá nhựa": gia_nhua,
                    "Giá máy": gia_may_ca, "Chu kỳ": chu_ky, "SP Khuôn": sp_khuon, "Bao bì": bao_bi, "Phụ kiện": phu_kien,
                    "Đơn giá phụ gia": don_gia_phu_gia, "Tỉ lệ phụ gia": ti_le_phu_gia, "Hệ số ĐL": hs_dl, "Hệ số TC": hs_tc,
                    "Giá Vốn": round(gvhb), "Giá Đại Lý": round(gia_dai_ly), "Giá Công ty": round(gia_cong_ty)
                }
                
                if st.session_state["is_editing_gc"]:
                    st.session_state["danh_sach_gc"][st.session_state["edit_index_gc"]] = new_data
                    st.session_state["is_editing_gc"] = False
                else:
                    st.session_state["danh_sach_gc"].append(new_data)
                
                save_data_gc(st.session_state["danh_sach_gc"])
                
                st.session_state["gc_success_msg"] = f"✅ Đã lưu sản phẩm gia công '{ten_sp}' thành công! Bạn có thể nhập tiếp sản phẩm mới."
                st.rerun()

# ==========================================
# TAB 2: DANH SÁCH SẢN PHẨM GIA CÔNG
# ==========================================
elif st.session_state["current_tab_gc"] == "📋 2. DANH SÁCH GIA CÔNG":
    st.subheader("📋 DANH SÁCH SẢN PHẨM ĐÃ LƯU")
    
    col_ref1, col_ref2 = st.columns([8, 2])
    if col_ref2.button("🔄 Tải lại dữ liệu (Refresh)"):
        st.session_state["danh_sach_gc"] = load_data_gc()
        if st.session_state["danh_sach_gc"] is None:
            st.session_state["danh_sach_gc"] = []
        st.rerun()

    if st.session_state["danh_sach_gc"]:
        df = pd.DataFrame(st.session_state["danh_sach_gc"])
        
        # Hỗ trợ hiển thị đúng nếu dữ liệu cũ còn lưu cột "Giá Tiêu Chuẩn"
        if "Giá Tiêu Chuẩn" in df.columns and "Giá Công ty" not in df.columns:
            df.rename(columns={"Giá Tiêu Chuẩn": "Giá Công ty"}, inplace=True)
            
        cols_to_show = ["Mã SP", "Tên Sản Phẩm", "Giá Vốn", "Giá Đại Lý", "Giá Công ty"]
        st.dataframe(df[[c for c in cols_to_show if c in df.columns]], use_container_width=True)
        
        st.markdown("---")
        st.markdown("**Quản lý:**")
        col1, col2 = st.columns([2, 1])
        
        with col1:
            ten_sp_chon = st.selectbox("Chọn sản phẩm:", [sp["Tên Sản Phẩm"] for sp in st.session_state["danh_sach_gc"]])
            idx = next(i for i, sp in enumerate(st.session_state["danh_sach_gc"]) if sp["Tên Sản Phẩm"] == ten_sp_chon)
            
            c_btn1, c_btn2 = st.columns(2)
            if c_btn1.button("✏️ Chỉnh sửa", use_container_width=True):
                sp = st.session_state["danh_sach_gc"][idx]
                
                # Bơm dữ liệu vào bộ nhớ
                st.session_state["gc_ma_in"] = sp.get("Mã SP", "")
                st.session_state["gc_ten_in"] = sp.get("Tên Sản Phẩm", "")
                st.session_state["gc_tl_in"] = float(sp.get("Trọng lượng", 34.0)) if isinstance(sp.get("Trọng lượng", 34.0), (int, float)) else 34.0
                st.session_state["gc_gia_nhua_in"] = int(sp.get("Đơn giá nhựa", 23000))
                st.session_state["gc_gia_may_in"] = int(sp.get("Giá máy", 1700000))
                st.session_state["gc_chu_ky_in"] = float(sp.get("Chu kỳ", 40.0))
                st.session_state["gc_sp_khuon_in"] = int(sp.get("SP Khuôn", 2))
                st.session_state["gc_bao_bi_in"] = int(sp.get("Bao bì", 10))
                st.session_state["gc_phu_kien_in"] = int(sp.get("Phụ kiện", 100))
                st.session_state["gc_dg_pg_in"] = int(sp.get("Đơn giá phụ gia", 0))
                st.session_state["gc_tl_pg_in"] = float(sp.get("Tỉ lệ phụ gia", 0.0))
                st.session_state["gc_hs_dl_in"] = float(sp.get("Hệ số ĐL", 0.6))
                st.session_state["gc_hs_tc_in"] = float(sp.get("Hệ số TC", 0.6))
                
                st.session_state["is_editing_gc"] = True
                st.session_state["edit_index_gc"] = idx
                
                # Kích hoạt lệnh nhảy Tab
                st.session_state["current_tab_gc"] = danh_sach_tabs[0]
                st.rerun()
                
            if c_btn2.button("🗑️ Xóa", use_container_width=True):
                st.session_state["confirm_delete_idx_gc"] = idx
                
            # --- HIỆN HỘP THOẠI XÁC NHẬN ---
            if st.session_state.get("confirm_delete_idx_gc") == idx:
                st.warning(f"⚠️ Bạn có chắc chắn muốn xóa sản phẩm **{st.session_state['danh_sach_gc'][idx]['Tên Sản Phẩm']}** không?")
                col_yes, col_no = st.columns(2)
                if col_yes.button("✔️ Đồng ý xóa", use_container_width=True, key=f"yes_del_gc"):
                    st.session_state["danh_sach_gc"].pop(idx)
                    save_data_gc(st.session_state["danh_sach_gc"])
                    st.session_state["confirm_delete_idx_gc"] = None
                    st.rerun()
                if col_no.button("❌ Hủy", use_container_width=True, key=f"no_del_gc"):
                    st.session_state["confirm_delete_idx_gc"] = None
                    st.rerun()
                    
        with col2:
            st.write("") 
    else:
        st.info("Chưa có dữ liệu.")

# ==========================================
# TAB 3: ĐỊNH LƯỢNG SẢN PHẨM (GIA CÔNG)
# ==========================================
elif st.session_state["current_tab_gc"] == "⚖️ 3. ĐỊNH LƯỢNG SẢN PHẨM":
    st.subheader("⚖️ BẢNG ĐỊNH LƯỢNG SẢN PHẨM GIA CÔNG")
    
    col_ref3, col_ref4 = st.columns([8, 2])
    if col_ref4.button("🔄 Tải lại dữ liệu", key="refresh_dl_gc"):
        st.session_state["danh_sach_gc"] = load_data_gc()
        st.rerun()
    
    if st.session_state["danh_sach_gc"]:
        du_lieu_hien_thi = []
        
        for sp in st.session_state["danh_sach_gc"]:
            ma_sp = sp.get("Mã SP", "")
            ten_sp = sp.get("Tên Sản Phẩm", "")
            trong_luong = sp.get("Trọng lượng", 0)
            
            tl_hien_thi = f"{trong_luong} g" if isinstance(trong_luong, (int, float)) else f"{trong_luong}"
                
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
                file_name='Bang_Dinh_Luong_Gia_Cong.csv',
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
                    pdf.add_font("CustomFont", "", "arial.ttf", uni=True)
                    pdf.set_font("CustomFont", size=16)
                except Exception as e:
                    st.error(f"Lỗi nạp font: Đảm bảo bạn đã chép file 'arial.ttf' vào cùng thư mục.")
                    pdf.set_font("Arial", size=16)
                
                # Tiêu đề
                pdf.cell(0, 10, txt="BẢNG ĐỊNH LƯỢNG SẢN PHẨM GIA CÔNG (WANCHI)", ln=True, align='C')
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
                file_name='Bang_Dinh_Luong_Gia_Cong.pdf',
                mime='application/pdf',
                use_container_width=True
            )

    else:
        st.info("Chưa có dữ liệu sản phẩm gia công.")
