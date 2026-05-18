import streamlit as st
import pandas as pd
# --- KHÓA BẢO MẬT TỪ TRANG CHỦ ---
if not st.session_state.get("logged_in", False):
    st.warning("🔒 Bạn chưa đăng nhập! Vui lòng quay lại Trang Chủ (Home) để gõ mật khẩu.")
    st.stop()
from fpdf import FPDF
import unicodedata
from datetime import datetime
from sqlalchemy import text
import os

# ==========================================
# CẤU HÌNH TRANG & KẾT NỐI NEON (POSTGRESQL)
# ==========================================

try:
    conn = st.connection("postgresql", type="sql")
except Exception as e:
    st.error("Chưa thể kết nối đến cơ sở dữ liệu. Vui lòng kiểm tra lại file cấu hình Secrets.")
    st.stop()

def remove_accents(input_str):
    s = str(input_str).replace('Đ', 'D').replace('đ', 'd')
    nfkd_form = unicodedata.normalize('NFKD', s)
    return u"".join([c for c in nfkd_form if not unicodedata.combining(c)])

# ---> HÀM XUẤT PDF ĐÃ NÂNG CẤP (TỰ ĐỘNG XUỐNG DÒNG & CHIA TỶ LỆ) <---
def export_pdf(df, title):
    df_export = df.copy()
    if "Cụm khuôn hoàn chỉnh" in df_export.columns:
        df_export = df_export.drop(columns=["Cụm khuôn hoàn chỉnh"])
    
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    
    try:
        pdf.add_font('ArialVN', '', 'arial.ttf', uni=True)
        pdf.add_font('ArialVN', 'B', 'arialbd.ttf', uni=True)
        font_name = 'ArialVN'
    except:
        font_name = 'Arial'
        st.warning("⚠️ Không tìm thấy file 'arial.ttf'. PDF sẽ bị mất dấu tiếng Việt.")

    # --- Header (Logo & Thông tin) ---
    logo_path = "logo.png" 
    try:
        if os.path.exists(logo_path):
            pdf.image(logo_path, x=10, y=8, w=35)
            start_x = 50 
        else:
            start_x = 10
    except:
        start_x = 10

    pdf.set_xy(start_x, 10)
    pdf.set_font(font_name, 'B' if font_name == 'ArialVN' else '', 14)
    pdf.cell(0, 6, txt="WANCHI", ln=True, align='L')
    
    pdf.set_x(start_x)
    pdf.set_font(font_name, '', 10)
    pdf.cell(0, 5, txt="775 Võ Hữu Lợi, Xã Lê Minh Xuân, Huyện Bình Chánh, TP.HCM", ln=True, align='L')
    
    pdf.set_x(start_x)
    pdf.cell(0, 5, txt="SĐT: 0902.580.828 - 0937.572.577", ln=True, align='L')
    
    pdf.ln(10)
    pdf.set_font(font_name, 'B' if font_name == 'ArialVN' else '', 16)
    pdf.cell(0, 10, txt=title.upper(), ln=True, align='C')
    pdf.set_font(font_name, '', 10)
    pdf.cell(0, 8, txt=f"Ngày: {datetime.now().strftime('%d/%m/%Y')}", ln=True, align='C')
    pdf.ln(5)

    # --- Bảng Dữ Liệu ---
    if not df_export.empty:
        pdf.set_font(font_name, '', 8)
        num_cols = ["Số lượng", "Đơn giá", "Cắt dây", "Xung điện (EDM)", "Phay CNC", "Nhiệt Luyện", "Đánh bóng", "Tạo Nhám hoa văn", "Dọn phôi", "Tổng tiền", "Tổng Nguyên Vật Liệu (A)", "Tổng Gia Công (B)", "Tổng Vật Tư (C)", "TỔNG CỘNG", "Tổng giá trị khuôn", "Tổng giá gia công", "Cọc đợt 1", "Còn nợ"]
        
        # 1. Tính toán chiều rộng lý tưởng cho từng cột
        col_widths = []
        for col in df_export.columns:
            max_w = pdf.get_string_width(str(col)) + 4  # Dành chỗ cho Header
            for item in df_export[col]:
                val_str = str(item)
                if pd.notnull(item) and str(item).strip() != "":
                    if col in num_cols:
                        try:
                            val_str = f"{float(item):,.0f}".replace(",", ".")
                        except: pass
                # Giới hạn chiều rộng tối đa (ví dụ 45mm) để ép các ô nhiều chữ phải xuống dòng
                item_w = min(pdf.get_string_width(val_str) + 4, 45) 
                if item_w > max_w:
                    max_w = item_w
            col_widths.append(max_w)
        
        # Co giãn bề ngang cho vừa khổ giấy A4 (277mm khả dụng)
        total_w = sum(col_widths)
        if total_w > 0:
            scale = 277 / total_w
            col_widths = [w * scale for w in col_widths]

        # 2. In Header
        pdf.set_font(font_name, 'B' if font_name == 'ArialVN' else '', 8)
        pdf.set_fill_color(220, 220, 220)
        for i, col in enumerate(df_export.columns):
            pdf.cell(col_widths[i], 8, txt=str(col), border=1, fill=True, align='C')
        pdf.ln()
        
        # 3. In Dữ Liệu (Xử lý Text Wrapping)
        pdf.set_font(font_name, '', 8)
        
        # Khởi tạo bộ đếm tổng cho từng cột số
        col_sums = {c: 0.0 for c in df_export.columns}
        
        for _, row in df_export.iterrows():
            row_texts = []
            row_aligns = []
            
            # Chuẩn bị dữ liệu và tính tổng
            for i, (col_name, item) in enumerate(row.items()):
                val_str = str(item) if pd.notnull(item) else ""
                align_col = 'L'
                if col_name in num_cols and str(item).strip() != "":
                    try:
                        val = float(item)
                        val_str = f"{val:,.0f}".replace(",", ".")
                        align_col = 'R'
                        col_sums[col_name] += val
                    except: pass
                row_texts.append(val_str)
                row_aligns.append(align_col)
            
            # Tính toán chiều cao cần thiết cho hàng (dựa trên cột chứa nhiều dòng nhất)
            line_height = 5
            max_lines = 1
            for i, text_val in enumerate(row_texts):
                est_width = pdf.get_string_width(text_val) * 1.1 # Thêm 10% dung sai
                lines = int(est_width / (col_widths[i] - 1)) + 1
                lines += text_val.count('\n') # Cộng thêm số lần người dùng cố tình Enter
                if lines > max_lines:
                    max_lines = lines
            
            row_height = max_lines * line_height
            
            # Sang trang mới nếu hàng này vượt quá lề dưới
            if pdf.get_y() + row_height > 190: 
                pdf.add_page()
            
            # Vẽ từng ô bằng MultiCell để cho phép xuống dòng
            x_start = pdf.get_x()
            y_start = pdf.get_y()
            
            for i, text_val in enumerate(row_texts):
                pdf.set_xy(x_start, y_start)
                pdf.multi_cell(col_widths[i], line_height, txt=text_val, border=0, align=row_aligns[i])
                
                # Vẽ khung (Border) trùm lên vùng chữ
                pdf.set_xy(x_start, y_start)
                pdf.cell(col_widths[i], row_height, border=1)
                
                x_start += col_widths[i]
            
            # Đưa con trỏ xuống hàng tiếp theo
            pdf.set_y(y_start + row_height)
            
        # 4. In Dòng TỔNG CỘNG (Cộng độc lập từng cột)
        cols_to_sum = ["Tổng tiền", "TỔNG CỘNG", "Tổng giá trị khuôn", "Tổng giá gia công", "Cọc đợt 1", "Còn nợ"]
        if any(c in df_export.columns for c in cols_to_sum):
            pdf.set_font(font_name, 'B' if font_name == 'ArialVN' else '', 9)
            pdf.set_fill_color(240, 240, 240)
            
            for i, col in enumerate(df_export.columns):
                if col in cols_to_sum:
                    tong_str = f"{col_sums[col]:,.0f}".replace(",", ".")
                    pdf.cell(col_widths[i], 8, txt=tong_str, border=1, fill=True, align='R')
                elif i == 1: # Chữ TỔNG CỘNG để ở cột thứ 2 cho cân đối
                    pdf.cell(col_widths[i], 8, txt="TỔNG CỘNG:", border=1, fill=True, align='R')
                else:
                    pdf.cell(col_widths[i], 8, txt="", border=1, fill=True) 
            pdf.ln()
            
    # --- Lưu và trả về File ---
    temp_filename = f"temp_report_{datetime.now().strftime('%H%M%S')}.pdf"
    pdf.output(temp_filename)
    with open(temp_filename, "rb") as f:
        pdf_bytes = f.read()
    if os.path.exists(temp_filename):
        os.remove(temp_filename)
        
    return pdf_bytes


# ==========================================
# KIẾN TRÚC BỘ NHỚ ĐỆM (CACHE) CỰC NHANH
# ==========================================

@st.cache_data(show_spinner=False, ttl=86400) 
def fetch_data_from_db(table_name):
    try:
        return conn.query(f"SELECT * FROM {table_name}", ttl=0)
    except Exception:
        return pd.DataFrame()

def force_reload_cache():
    fetch_data_from_db.clear()

def load_data(table_name, columns):
    df = fetch_data_from_db(table_name)
    if df.empty:
        return pd.DataFrame(columns=columns)
    for col in columns:
        if col not in df.columns:
            df[col] = None
    return df

def append_data(new_row_dict, table_name, df_current):
    try:
        df_new = pd.DataFrame([new_row_dict])
        df_new.to_sql(table_name, con=conn.engine, if_exists='append', index=False)
        force_reload_cache()
    except Exception:
        try:
            df_combined = pd.concat([df_current, pd.DataFrame([new_row_dict])], ignore_index=True)
            df_combined.to_sql(table_name, con=conn.engine, if_exists='replace', index=False, method='multi')
            force_reload_cache()
        except Exception as e2:
            st.error(f"⚠️ Lỗi cấu trúc: {str(e2)}")

def save_data(df, table_name):
    try:
        try:
            with conn.session as session:
                session.execute(text(f"TRUNCATE TABLE {table_name}"))
                session.commit()
            df.to_sql(table_name, con=conn.engine, if_exists='append', index=False, method='multi')
        except Exception:
            df.to_sql(table_name, con=conn.engine, if_exists='replace', index=False, method='multi')
        force_reload_cache()
    except Exception as e:
        st.error(f"⚠️ Lỗi khi lưu dữ liệu lên đám mây ({table_name}): {str(e)}")

# TÍNH NĂNG XÓA TOÀN BỘ DỮ LIỆU CỦA 1 KHUÔN
def delete_mold_from_db(mold_code):
    try:
        with conn.session as session:
            session.execute(text('DELETE FROM wanchi_a WHERE "Mã khuôn" = :m'), {"m": mold_code})
            session.execute(text('DELETE FROM wanchi_b WHERE "Mã khuôn" = :m'), {"m": mold_code})
            session.execute(text('DELETE FROM wanchi_c WHERE "Mã khuôn" = :m'), {"m": mold_code})
            session.execute(text('DELETE FROM wanchi_d WHERE "Mã khuôn" = :m'), {"m": mold_code})
            session.execute(text('DELETE FROM wanchi_f WHERE "Mã khuôn" = :m'), {"m": mold_code})
            session.commit()
        force_reload_cache()
    except Exception as e:
        st.error(f"⚠️ Lỗi khi xóa khuôn trên database: {str(e)}")


# ==========================================
# KHỞI TẠO DỮ LIỆU TỪ DB & XỬ LÝ CỘT
# ==========================================
cols_A = ["Ngày", "Nhà cung cấp NVL", "Mã khuôn", "Tên NVL", "Quy cách", "Số lượng", "Đơn giá", "Tổng tiền"]
df_A = load_data("wanchi_a", cols_A)
df_A = df_A.loc[:, ~df_A.columns.duplicated()]

cols_B = ["Ngày", "Đơn vị gia công", "Mã khuôn", "Cắt dây", "Xung điện (EDM)", "Phay CNC", "Nhiệt Luyện", "Đánh bóng", "Tạo Nhám hoa văn", "Dọn phôi", "Cụm khuôn hoàn chỉnh", "Tổng tiền"]
df_B = load_data("wanchi_b", cols_B)

if "Đơn giá" in df_B.columns:
    df_B.rename(columns={"Đơn giá": "Cụm khuôn hoàn chỉnh"}, inplace=True)
if "Ráp khuôn hoàn thiện" in df_B.columns:
    df_B.rename(columns={"Ráp khuôn hoàn thiện": "Cụm khuôn hoàn chỉnh"}, inplace=True)

df_B = df_B.loc[:, ~df_B.columns.duplicated()]

if "Dọn phôi" not in df_B.columns:
    df_B["Dọn phôi"] = 0

df_B = df_B[[c for c in cols_B if c in df_B.columns]]

cols_C = ["Ngày", "Nhà cung cấp vật tư", "Mã khuôn", "Tên linh kiện", "Đơn giá", "Tổng tiền"]
df_C = load_data("wanchi_c", cols_C)
df_C = df_C.loc[:, ~df_C.columns.duplicated()]

cols_D = ["Ngày", "Mã khuôn", "Tổng Nguyên Vật Liệu (A)", "Tổng Gia Công (B)", "Tổng Vật Tư (C)", "TỔNG CỘNG"]
df_D = load_data("wanchi_d", cols_D)
df_D = df_D.loc[:, ~df_D.columns.duplicated()]

cols_F = ["Mã khuôn", "Đơn vị gia công", "Các mục gia công", "Thời gian nhận", "Thời gian bàn giao", "Tổng giá gia công", "Cọc đợt 1", "Còn nợ", "Ghi chú"]
df_F = load_data("wanchi_f", cols_F)
df_F = df_F.loc[:, ~df_F.columns.duplicated()]

all_molds_set = set()
if not df_A.empty: all_molds_set.update(df_A["Mã khuôn"].dropna().unique())
if not df_B.empty: all_molds_set.update(df_B["Mã khuôn"].dropna().unique())
if not df_C.empty: all_molds_set.update(df_C["Mã khuôn"].dropna().unique())
if not df_D.empty: all_molds_set.update(df_D["Mã khuôn"].dropna().unique())
if not df_F.empty: all_molds_set.update(df_F["Mã khuôn"].dropna().unique())
list_molds_master = sorted(list(all_molds_set))


# ==========================================
# GIAO DIỆN CHÍNH
# ==========================================
st.title("🏭 Công Cụ Quản Lý Khuôn Mẫu WANCHI")
st.markdown("---")

tab_A, tab_B, tab_C, tab_D, tab_F, tab_E = st.tabs([
    "A. Nguyên Vật Liệu", 
    "B. Gia Công", 
    "C. Vật Tư Khuôn", 
    "D. Tổng Giá Khuôn",
    "F. Đơn Hàng Gia Công",
    "E. Danh Sách & Quản Trị"
])

# ------------------------------------------
# MODULE A: NGUYÊN VẬT LIỆU
# ------------------------------------------
with tab_A:
    st.header("A. Nguyên Vật Liệu")
    with st.expander("➕ Nhập Nguyên Vật Liệu Mới"):
        with st.form("form_A"):
            c1, c2, c3, c4 = st.columns(4)
            ngay_a = c1.date_input("Ngày", datetime.today())
            ncc_a = c2.text_input("Nhà cung cấp NVL")
            ma_khuon_a = c3.text_input("Mã khuôn (Nhập mã mới tại đây)")
            ten_nvl = c4.text_input("Tên NVL")
            
            c5, c6, c7 = st.columns(3)
            quy_cach = c5.text_input("Quy cách")
            sl_a = c6.number_input("Số lượng", min_value=0.0, step=1.0) 
            don_gia_a = c7.number_input("Đơn giá", min_value=0, step=1)
            
            st.markdown("---")
            _, c8 = st.columns([3, 1])
            tong_tien_a = c8.number_input("💰 Tổng tiền (Tự nhập)", min_value=0, step=1)
            
            if st.form_submit_button("Lưu Dữ Liệu NVL"):
                with st.spinner("⏳ Đang chèn dữ liệu mới..."):
                    new_row = {"Ngày": ngay_a.strftime('%d/%m/%Y'), "Nhà cung cấp NVL": ncc_a, "Mã khuôn": ma_khuon_a.strip().upper(), 
                               "Tên NVL": ten_nvl, "Quy cách": quy_cach, "Số lượng": sl_a, "Đơn giá": don_gia_a, "Tổng tiền": tong_tien_a}
                    append_data(new_row, "wanchi_a", df_A)
                st.rerun()

    st.subheader("Bảng Dữ Liệu (Cho phép chỉnh sửa/xóa trực tiếp)")
    edited_A = st.data_editor(df_A, num_rows="dynamic", use_container_width=True, key="edit_A")
    if st.button("💾 Cập nhật dữ liệu A (Lên Neon)"):
        with st.spinner("⏳ Đang đồng bộ cập nhật lên Cloud, vui lòng đợi..."):
            save_data(edited_A, "wanchi_a")
        st.success("✅ Đã đồng bộ lên cơ sở dữ liệu!")
        st.rerun()
        
    st.markdown("---")
    st.subheader("📥 Xuất Báo Cáo PDF")
    col_pdf1, col_pdf2 = st.columns([1, 2])
    filter_pdf_a = col_pdf1.selectbox("Chọn Mã khuôn để xuất PDF:", ["Tất cả"] + list_molds_master, key="pdf_a")
    
    if st.button("Tạo file PDF (Module A)"):
        with st.spinner("Đang trích xuất file PDF..."):
            df_export_a = edited_A if filter_pdf_a == "Tất cả" else edited_A[edited_A["Mã khuôn"] == filter_pdf_a]
            pdf_a = export_pdf(df_export_a, f"BÁO CÁO NGUYÊN VẬT LIỆU KHUÔN {filter_pdf_a}")
        col_pdf2.download_button("⬇️ Nhấn để Tải PDF Xuống", pdf_a, f"WANCHI_NVL_{filter_pdf_a}.pdf", "application/pdf")


# ------------------------------------------
# MODULE B: GIA CÔNG
# ------------------------------------------
with tab_B:
    st.header("B. Gia Công")
    with st.expander("➕ Nhập Chi Phí Gia Công Mới"):
        with st.form("form_B"):
            c1, c2, c3 = st.columns(3)
            ngay_b = c1.date_input("Ngày", datetime.today(), key="ngay_b")
            ncc_b = c2.text_input("Đơn vị gia công")
            ma_khuon_b = c3.selectbox("Chọn mã khuôn:", list_molds_master) if list_molds_master else c3.text_input("Mã khuôn")
            
            c4, c5, c6, c7 = st.columns(4)
            cat_day = c4.number_input("Cắt dây", min_value=0, step=1)
            xung_dien = c5.number_input("Xung điện (EDM)", min_value=0, step=1)
            phay_cnc = c6.number_input("Phay CNC", min_value=0, step=1)
            nhiet_luyen = c7.number_input("Nhiệt Luyện", min_value=0, step=1)
            
            c8, c9, c10, c11 = st.columns(4)
            danh_bong = c8.number_input("Đánh bóng", min_value=0, step=1)
            nham = c9.number_input("Tạo Nhám hoa văn", min_value=0, step=1)
            don_phoi = c10.number_input("Dọn phôi", min_value=0, step=1)
            rap_khuon = c11.number_input("Cụm khuôn hoàn chỉnh", min_value=0, step=1)
            
            st.markdown("---")
            _, c12 = st.columns([3, 1])
            tong_tien_b = c12.number_input("💰 Tổng tiền (Tự nhập)", min_value=0, step=1, key="tong_tien_b")
            
            if st.form_submit_button("Lưu Dữ Liệu Gia Công"):
                with st.spinner("⏳ Đang xử lý đồng bộ cơ sở dữ liệu..."):
                    new_row_b = {"Ngày": ngay_b.strftime('%d/%m/%Y'), "Đơn vị gia công": ncc_b, "Mã khuôn": ma_khuon_b.strip().upper(),
                                 "Cắt dây": cat_day, "Xung điện (EDM)": xung_dien, "Phay CNC": phay_cnc, "Nhiệt Luyện": nhiet_luyen,
                                 "Đánh bóng": danh_bong, "Tạo Nhám hoa văn": nham, "Dọn phôi": don_phoi, 
                                 "Cụm khuôn hoàn chỉnh": rap_khuon, "Tổng tiền": tong_tien_b}
                    append_data(new_row_b, "wanchi_b", df_B)
                st.rerun()

    st.subheader("Bảng Dữ Liệu Gia Công")
    edited_B = st.data_editor(df_B, num_rows="dynamic", use_container_width=True, key="edit_B")
    if st.button("💾 Cập nhật dữ liệu B (Lên Neon)"):
        with st.spinner("⏳ Đang đồng bộ cập nhật lên Cloud..."):
            save_data(edited_B, "wanchi_b")
        st.success("✅ Đã đồng bộ lên cơ sở dữ liệu!")
        st.rerun()

    st.markdown("---")
    st.subheader("📥 Xuất Báo Cáo PDF")
    col_pdf3, col_pdf4 = st.columns([1, 2])
    filter_pdf_b = col_pdf3.selectbox("Chọn Mã khuôn để xuất PDF:", ["Tất cả"] + list_molds_master, key="pdf_b")
    
    if st.button("Tạo file PDF (Module B)"):
        with st.spinner("Đang trích xuất file PDF..."):
            df_export_b = edited_B if filter_pdf_b == "Tất cả" else edited_B[edited_B["Mã khuôn"] == filter_pdf_b]
            pdf_b = export_pdf(df_export_b, f"BÁO CÁO CHI PHÍ GIA CÔNG KHUÔN {filter_pdf_b}")
        col_pdf4.download_button("⬇️ Nhấn để Tải PDF Xuống", pdf_b, f"WANCHI_GiaCong_{filter_pdf_b}.pdf", "application/pdf")


# ------------------------------------------
# MODULE C: VẬT TƯ
# ------------------------------------------
with tab_C:
    st.header("C. Vật Tư Khuôn Mẫu")
    with st.expander("➕ Nhập Vật Tư Mới"):
        with st.form("form_C"):
            c1, c2, c3 = st.columns(3)
            ngay_c = c1.date_input("Ngày", datetime.today(), key="ngay_c")
            ncc_c = c2.text_input("Nhà cung cấp vật tư")
            ma_khuon_c = c3.selectbox("Chọn mã khuôn:", list_molds_master, key="mk_c") if list_molds_master else c3.text_input("Mã khuôn", key="mk_c_text")
            
            c4, c5 = st.columns(2)
            ten_lk = c4.text_input("Tên linh kiện")
            don_gia_c = c5.number_input("Đơn giá", min_value=0, step=1, key="dg_c")
            
            st.markdown("---")
            _, c6 = st.columns([3, 1])
            tong_tien_c = c6.number_input("💰 Tổng tiền (Tự nhập)", min_value=0, step=1, key="tt_c")
            
            if st.form_submit_button("Lưu Dữ Liệu Vật Tư"):
                with st.spinner("⏳ Đang chèn dữ liệu mới..."):
                    new_row_c = {"Ngày": ngay_c.strftime('%d/%m/%Y'), "Nhà cung cấp vật tư": ncc_c, "Mã khuôn": ma_khuon_c.strip().upper(),
                                 "Tên linh kiện": ten_lk, "Đơn giá": don_gia_c, "Tổng tiền": tong_tien_c}
                    append_data(new_row_c, "wanchi_c", df_C)
                st.rerun()

    st.subheader("Bảng Dữ Tại Vật Tư")
    edited_C = st.data_editor(df_C, num_rows="dynamic", use_container_width=True, key="edit_C")
    if st.button("💾 Cập nhật dữ liệu C (Lên Neon)"):
        with st.spinner("⏳ Đang đồng bộ cập nhật lên Cloud..."):
            save_data(edited_C, "wanchi_c")
        st.success("✅ Đã đồng bộ lên cơ sở dữ liệu!")
        st.rerun()

    st.markdown("---")
    st.subheader("📥 Xuất Báo Cáo PDF")
    col_pdf5, col_pdf6 = st.columns([1, 2])
    filter_pdf_c = col_pdf5.selectbox("Chọn Mã khuôn để xuất PDF:", ["Tất cả"] + list_molds_master, key="pdf_c")
    
    if st.button("Tạo file PDF (Module C)"):
        with st.spinner("Đang trích xuất file PDF..."):
            df_export_c = edited_C if filter_pdf_c == "Tất cả" else edited_C[edited_C["Mã khuôn"] == filter_pdf_c]
            pdf_c = export_pdf(df_export_c, f"BÁO CÁO VẬT TƯ KHUÔN {filter_pdf_c}")
        col_pdf6.download_button("⬇️ Nhấn để Tải PDF Xuống", pdf_c, f"WANCHI_VatTu_{filter_pdf_c}.pdf", "application/pdf")


# ------------------------------------------
# MODULE D: TỔNG KẾT
# ------------------------------------------
with tab_D:
    st.header("D. Tổng Hợp Giá Trị Khuôn")
    
    with st.expander("🔄 Cập Nhật Tổng Giá Tự Động"):
        st.write("Chọn mã khuôn để tự động quét toàn bộ chi phí từ 3 Module trên:")
        selected_mold = st.selectbox("Mã Khuôn Cần Tổng Kết:", list_molds_master, key="mold_total")
        
        if st.button("🧮 Tính Toán Bảng Tổng"):
            with st.spinner("⏳ Đang xử lý tính toán..."):
                if selected_mold:
                    sum_A = pd.to_numeric(df_A[df_A["Mã khuôn"] == selected_mold]["Tổng tiền"], errors='coerce').sum() if not df_A.empty else 0
                    sum_B = pd.to_numeric(df_B[df_B["Mã khuôn"] == selected_mold]["Tổng tiền"], errors='coerce').sum() if not df_B.empty else 0
                    sum_C = pd.to_numeric(df_C[df_C["Mã khuôn"] == selected_mold]["Tổng tiền"], errors='coerce').sum() if not df_C.empty else 0
                    
                    total = sum_A + sum_B + sum_C
                    
                    new_row_D = {
                        "Ngày": datetime.today().strftime('%d/%m/%Y'),
                        "Mã khuôn": selected_mold,
                        "Tổng Nguyên Vật Liệu (A)": sum_A,
                        "Tổng Gia Công (B)": sum_B,
                        "Tổng Vật Tư (C)": sum_C,
                        "TỔNG CỘNG": total
                    }
                    
                    if selected_mold in df_D["Mã khuôn"].values:
                        idx = df_D.index[df_D['Mã khuôn'] == selected_mold].tolist()[0]
                        for k, v in new_row_D.items():
                            df_D.at[idx, k] = v
                        save_data(df_D, "wanchi_d")
                    else:
                        append_data(new_row_D, "wanchi_d", df_D)
            st.success("✅ Đã tính toán xong và đồng bộ lên DB!")
            st.rerun()

    st.markdown("---")
    st.subheader("Bảng Tổng Hợp Chi Phí")
    edited_D = st.data_editor(df_D, num_rows="dynamic", use_container_width=True, key="edit_D")
    if st.button("💾 Cập nhật bảng Tổng (Lên Neon)"):
        with st.spinner("⏳ Đang lưu dữ liệu Tổng Hợp..."):
            save_data(edited_D, "wanchi_d")
        st.success("✅ Đã lưu các thay đổi!")
        st.rerun()
        
    st.markdown("---")
    st.subheader("📥 Xuất Báo Cáo PDF")
    col_pdf1_d, col_pdf2_d = st.columns([1, 2])
    filter_pdf_d = col_pdf1_d.selectbox("Chọn Mã khuôn để xuất PDF:", ["Tất cả"] + list_molds_master, key="pdf_d")
    
    if st.button("Tạo file PDF (Module D)"):
        with st.spinner("Đang trích xuất file PDF..."):
            df_export_d = edited_D if filter_pdf_d == "Tất cả" else edited_D[edited_D["Mã khuôn"] == filter_pdf_d]
            pdf_d = export_pdf(df_export_d, f"BẢNG TỔNG HỢP CHI PHÍ KHUÔN {filter_pdf_d}")
        col_pdf2_d.download_button("⬇️ Nhấn để Tải PDF Xuống", pdf_d, f"WANCHI_TongHop_{filter_pdf_d}.pdf", "application/pdf")


# ------------------------------------------
# MODULE F: ĐƠN HÀNG GIA CÔNG MỚI
# ------------------------------------------
with tab_F:
    st.header("F. Đơn Hàng Gia Công Ngoại")
    st.markdown("Quản lý dòng tiền đặt cọc và theo dõi tiến độ các hạng mục thuê gia công.")
    
    with st.expander("➕ Tạo Đơn Hàng Mới", expanded=True):
        with st.form("form_f"):
            c1, c2 = st.columns(2)
            ma_khuon_f = c1.selectbox("Mã khuôn", list_molds_master) if list_molds_master else c1.text_input("Mã khuôn")
            
            list_vendors = df_B["Đơn vị gia công"].dropna().unique().tolist() if not df_B.empty else []
            dv_options = ["(Nhập mới)"] + list_vendors
            dv_select = c2.selectbox("Đơn vị gia công (Chọn đối tác cũ hoặc nhập mới bên dưới)", dv_options)
            dv_new = c2.text_input("Nhập tên Đơn vị gia công mới (Chỉ nhập nếu chọn '(Nhập mới)')")
            
            st.markdown("---")
            danh_sach_hang_muc = ["Cắt dây", "Xung điện (EDM)", "Phay CNC", "Nhiệt Luyện", "Đánh bóng", "Tạo Nhám hoa văn", "Dọn phôi", "Ráp khuôn hoàn thiện"]
            hang_muc = st.multiselect("Các hạng mục cần gia công:", danh_sach_hang_muc)
            
            c3, c4 = st.columns(2)
            ngay_nhan = c3.date_input("Thời gian nhận phôi/khuôn")
            ngay_giao = c4.date_input("Thời gian bàn giao (Dự kiến)")
            
            st.markdown("---")
            c5, c6, c7 = st.columns(3)
            tong_gia_f = c5.number_input("Tổng giá gia công", min_value=0, step=1)
            coc_f = c6.number_input("Cọc đợt 1", min_value=0, step=1)
            ghi_chu_f = c7.text_input("Ghi chú")
            
            if st.form_submit_button("Lưu Đơn Hàng Mới"):
                final_dv = dv_new if dv_select == "(Nhập mới)" else dv_select
                if not final_dv:
                    st.error("⚠️ Vui lòng nhập tên Đơn vị gia công!")
                elif not hang_muc:
                    st.error("⚠️ Vui lòng chọn ít nhất 1 hạng mục gia công!")
                else:
                    with st.spinner("⏳ Đang lưu đơn hàng..."):
                        con_no = tong_gia_f - coc_f
                        new_row_f = {
                            "Mã khuôn": ma_khuon_f.strip().upper(),
                            "Đơn vị gia công": final_dv,
                            "Các mục gia công": ", ".join(hang_muc),
                            "Thời gian nhận": ngay_nhan.strftime('%d/%m/%Y'),
                            "Thời gian bàn giao": ngay_giao.strftime('%d/%m/%Y'),
                            "Tổng giá gia công": tong_gia_f,
                            "Cọc đợt 1": coc_f,
                            "Còn nợ": con_no,
                            "Ghi chú": ghi_chu_f
                        }
                        append_data(new_row_f, "wanchi_f", df_F)
                    st.rerun()

    st.subheader("Bảng Theo Dõi Đơn Hàng")
    edited_F = st.data_editor(df_F, num_rows="dynamic", use_container_width=True, key="edit_F")
    if st.button("💾 Cập nhật dữ liệu F (Lên Neon)"):
        with st.spinner("⏳ Đang đồng bộ..."):
            save_data(edited_F, "wanchi_f")
        st.success("✅ Đã đồng bộ lên cơ sở dữ liệu!")
        st.rerun()
        
    st.markdown("---")
    st.subheader("📥 Xuất Báo Cáo Đơn Hàng")
    col_pdf1_f, col_pdf2_f = st.columns([1, 2])
    filter_pdf_f = col_pdf1_f.selectbox("Chọn Mã khuôn để xuất PDF:", ["Tất cả"] + list_molds_master, key="pdf_f")
    
    if st.button("Tạo file PDF (Module F)"):
        with st.spinner("Đang trích xuất file PDF..."):
            df_export_f = edited_F if filter_pdf_f == "Tất cả" else edited_F[edited_F["Mã khuôn"] == filter_pdf_f]
            pdf_f = export_pdf(df_export_f, f"ĐƠN HÀNG GIA CÔNG KHUÔN {filter_pdf_f}")
        col_pdf2_f.download_button("⬇️ Nhấn để Tải PDF Xuống", pdf_f, f"WANCHI_DonHang_{filter_pdf_f}.pdf", "application/pdf")


# ------------------------------------------
# MODULE E: DANH SÁCH KHUÔN TỔNG HỢP & QUẢN TRỊ
# ------------------------------------------
with tab_E:
    st.header("E. Danh Sách Các Khuôn Đã Làm")
    st.markdown("Bảng tóm tắt tự động thu thập ngày bắt đầu làm khuôn (ngày sớm nhất nhập vật liệu/gia công) và tổng giá trị cho từng mã khuôn.")
    
    danh_sach_khuon_data = []
    for mk in list_molds_master:
        dates = []
        for df_temp in [df_A, df_B, df_C]:
            if not df_temp.empty and 'Mã khuôn' in df_temp.columns and 'Ngày' in df_temp.columns:
                mold_dates = df_temp[df_temp['Mã khuôn'] == mk]['Ngày'].dropna().tolist()
                dates.extend(mold_dates)
        
        ngay_lam = ""
        if dates:
            parsed_dates = []
            for d in dates:
                try:
                    parsed_dates.append(datetime.strptime(str(d), '%d/%m/%Y'))
                except:
                    pass
            if parsed_dates:
                ngay_lam = min(parsed_dates).strftime('%d/%m/%Y')
        
        tong_gia = 0
        if not df_D.empty and 'Mã khuôn' in df_D.columns:
            row_d = df_D[df_D['Mã khuôn'] == mk]
            if not row_d.empty:
                tong_gia = row_d['TỔNG CỘNG'].values[0]
        
        if tong_gia == 0:
            sum_A = pd.to_numeric(df_A[df_A["Mã khuôn"] == mk]["Tổng tiền"], errors='coerce').sum() if not df_A.empty else 0
            sum_B = pd.to_numeric(df_B[df_B["Mã khuôn"] == mk]["Tổng tiền"], errors='coerce').sum() if not df_B.empty else 0
            sum_C = pd.to_numeric(df_C[df_C["Mã khuôn"] == mk]["Tổng tiền"], errors='coerce').sum() if not df_C.empty else 0
            tong_gia = sum_A + sum_B + sum_C
            
        danh_sach_khuon_data.append({
            "Ngày làm khuôn": ngay_lam,
            "Mã khuôn": mk,
            "Tổng giá trị khuôn": tong_gia
        })
        
    df_E = pd.DataFrame(danh_sach_khuon_data)
    
    if not df_E.empty:
        st.dataframe(
            df_E,
            column_config={
                "Tổng giá trị khuôn": st.column_config.NumberColumn(
                    "Tổng giá trị khuôn (VNĐ)",
                    format="%d",
                    help="Được tổng hợp tự động từ Tab D"
                )
            },
            use_container_width=True,
            hide_index=True
        )
        
        st.markdown("---")
        st.subheader("📥 Xuất Báo Cáo PDF Danh Sách Khuôn")
        if st.button("Tạo file PDF (Module E)"):
            with st.spinner("Đang trích xuất file PDF..."):
                pdf_e = export_pdf(df_E, "DANH SÁCH TỔNG HỢP CÁC KHUÔN ĐÃ LÀM")
            st.download_button("⬇️ Nhấn để Tải PDF Xuống", pdf_e, "WANCHI_DanhSachKhuon.pdf", "application/pdf")
            
        st.markdown("---")
        st.subheader("🗑️ Khu Vực Quản Trị: Xóa Khuôn")
        st.warning("⚠️ Công cụ này dùng để xóa toàn bộ dữ liệu của một dự án khuôn lỗi hoặc nhập sai. Thao tác này sẽ dọn sạch dữ liệu ở cả 5 bảng và không thể khôi phục.")
        
        col_del1, col_del2 = st.columns([1, 1])
        selected_mold_to_delete = col_del1.selectbox("Chọn mã khuôn cần xóa hoàn toàn:", list_molds_master, key="del_mold_select")
        
        if "confirm_delete" not in st.session_state:
            st.session_state.confirm_delete = False
            st.session_state.mold_to_delete = None

        if col_del1.button("🗑️ Xóa khuôn này"):
            if selected_mold_to_delete:
                st.session_state.confirm_delete = True
                st.session_state.mold_to_delete = selected_mold_to_delete
                st.rerun()

        if st.session_state.get("confirm_delete") and st.session_state.get("mold_to_delete"):
            mold = st.session_state.mold_to_delete
            with st.container(border=True):
                st.error(f"🛑 BẠN ĐANG THAO TÁC XÓA KHUÔN: **{mold}**")
                st.write(f"Bạn có chắc chắn muốn xóa vĩnh viễn toàn bộ lịch sử chi phí của **{mold}** không? Hãy xác nhận bên dưới.")
                
                c_yes, c_no = st.columns(2)
                if c_yes.button("✅ Vâng, Xóa Toàn Bộ"):
                    with st.spinner(f"Đang dọn dẹp dữ liệu của khuôn {mold}..."):
                        delete_mold_from_db(mold)
                        st.session_state.confirm_delete = False
                        st.session_state.mold_to_delete = None
                    st.success(f"🎉 Đã xóa thành công toàn bộ dữ liệu của khuôn {mold}!")
                    st.rerun()
                    
                if c_no.button("❌ Hủy bỏ, Không xóa"):
                    st.session_state.confirm_delete = False
                    st.session_state.mold_to_delete = None
                    st.rerun()
    else:
        st.info("Chưa có dữ liệu khuôn nào trong hệ thống.")
