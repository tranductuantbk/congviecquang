import streamlit as st
import pandas as pd
import time
# --- KHÓA BẢO MẬT TỪ TRANG CHỦ ---
if not st.session_state.get("logged_in", False):
    st.warning("🔒 Bạn chưa đăng nhập! Vui lòng quay lại Trang Chủ (Home) để gõ mật khẩu.")
    st.stop()
from fpdf import FPDF
import unicodedata
from datetime import datetime
from sqlalchemy import text
import os
import io

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

# ==========================================
# KHỞI TẠO THƯ VIỆN CHUYỂN PDF SANG ẢNH
# ==========================================
try:
    import fitz  # PyMuPDF
    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False

def convert_pdf_to_png(pdf_bytes):
    if not HAS_FITZ:
        st.error("⚠️ Hệ thống thiếu thư viện 'PyMuPDF' để xuất ảnh. Vui lòng chạy lệnh: pip install PyMuPDF")
        return None
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        page = doc.load_page(0) 
        pix = page.get_pixmap(dpi=200) 
        return pix.tobytes("png")
    except Exception as e:
        st.error(f"Lỗi khi chuyển đổi ảnh: {e}")
        return None

def export_pdf(df, title, ma_khuon_str=None, khach_hang_str=None, dvgc_str=None):
    df_export = df.copy()
    if "Ráp khuôn hoàn chỉnh" in df_export.columns:
        df_export = df_export.drop(columns=["Ráp khuôn hoàn chỉnh"])
        
    if "Mã khuôn" in df_export.columns:
        df_export = df_export.drop(columns=["Mã khuôn"])
        
    dvgc_text = ""
    if "Đơn vị gia công" in df_export.columns:
        unique_dv = [str(x) for x in df_export["Đơn vị gia công"].dropna().unique() if str(x).strip()]
        if unique_dv:
            dvgc_text = "Đơn vị gia công: " + ", ".join(unique_dv)
        df_export = df_export.drop(columns=["Đơn vị gia công"])

    ghi_chu_data = []
    if "Ghi chú" in df_export.columns:
        ghi_chu_data = df_export["Ghi chú"].tolist()
        df_export = df_export.drop(columns=["Ghi chú"])
    
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.add_page()
    
    try:
        pdf.add_font('ArialVN', '', 'arial.ttf', uni=True)
        pdf.add_font('ArialVN', 'B', 'arialbd.ttf', uni=True)
        font_name = 'ArialVN'
    except:
        font_name = 'Arial'

    def txt(s):
        return remove_accents(str(s)) if font_name == 'Arial' else str(s)

    logo_path = "logo.png" 
    try:
        if os.path.exists(logo_path):
            pdf.image(logo_path, x=10, y=8, w=35)
            start_x = 50 
        else:
            start_x = 10
    except:
        start_x = 10

    pdf.set_xy(start_x, 15)
    pdf.set_font(font_name, '', 10)
    pdf.cell(0, 5, txt=txt("775 Võ Hữu Lợi, Xã Lê Minh Xuân, Huyện Bình Chánh, TP.HCM"), ln=True, align='L')
    pdf.set_x(start_x)
    pdf.cell(0, 5, txt=txt("SĐT: 0937.572.577"), ln=True, align='L')
    pdf.ln(12)

    pdf.set_x(10)
    pdf.set_font(font_name, 'B' if font_name == 'ArialVN' else '', 16)
    
    clean_title_lines = [line for line in title.split('\n') if not line.startswith("ĐƠN VỊ GIA CÔNG") and not line.startswith("MÃ KHUÔN")]
    clean_title = "\n".join(clean_title_lines)
    pdf.multi_cell(0, 8, txt=txt(clean_title.upper()), align='C')
    
    pdf.set_font(font_name, '', 12)
    pdf.ln(2)
    
    if ma_khuon_str:
        pdf.set_x(10)
        pdf.multi_cell(0, 6, txt=txt(f"Mã khuôn: {ma_khuon_str}"), align='L')
    if khach_hang_str:
        pdf.set_x(10)
        pdf.multi_cell(0, 6, txt=txt(f"Khách hàng: {khach_hang_str}"), align='L')
    if dvgc_str:
        pdf.set_x(10)
        pdf.multi_cell(0, 6, txt=txt(f"Đơn vị gia công: {dvgc_str}"), align='L')
    if dvgc_text and not dvgc_str:
        pdf.set_x(10)
        pdf.multi_cell(0, 6, txt=txt(dvgc_text), align='L')
        
    pdf.set_x(10)
    pdf.set_font(font_name, '', 10)
    pdf.cell(0, 8, txt=txt(f"Ngày lập: {datetime.now().strftime('%d/%m/%Y')}"), ln=True, align='C')
    pdf.ln(5)

    if not df_export.empty:
        pdf.set_font(font_name, '', 8)
        num_cols = ["Số lượng", "Đơn giá", "Cắt dây", "Xung điện (EDM)", "Phay CNC", "Nhiệt Luyện", "Đánh bóng", "Tạo Nhám hoa văn", "Dọn phôi", "Tổng tiền", "Tổng Nguyên Vật Liệu (A)", "Tổng Gia Công (B)", "Tổng Vật Tư (C)", "TỔNG CỘNG", "Tổng giá trị khuôn", "Tổng giá gia công", "Cọc đợt 1", "Còn nợ"]
        
        col_widths = []
        for col in df_export.columns:
            max_w = pdf.get_string_width(txt(col)) + 4 
            for item in df_export[col]:
                val_str = str(item) if pd.notnull(item) else ""
                if col in num_cols and val_str.strip() != "":
                    try: val_str = f"{float(item):,.0f}".replace(",", ".")
                    except: pass
                for para in val_str.split('\n'):
                    item_w = pdf.get_string_width(txt(para)) + 4
                    if item_w > max_w:
                        max_w = item_w
            if col in ["Các mục gia công", "Tên NVL", "Tên linh kiện", "Quy cách", "Nhà cung cấp NVL", "Khách hàng"]:
                if max_w > 45: max_w = 45
            elif max_w > 50: max_w = 50
            col_widths.append(max_w)
        
        total_w = sum(col_widths)
        if total_w > 0:
            scale = 190 / total_w
            col_widths = [w * scale for w in col_widths]

        sum_tong_tien = 0 
        
        def draw_row(row_data, is_header=False, is_footer=False):
            line_h = 6 if is_header or is_footer else 5
            max_lines = 1
            for i, val in enumerate(row_data):
                cw = col_widths[i]
                lines = 1
                curr_w = 0
                for para in val.split('\n'):
                    words = para.split(' ')
                    for w in words:
                        ww = pdf.get_string_width(w + ' ')
                        if curr_w + ww > cw - 2:
                            lines += 1
                            curr_w = ww
                        else:
                            curr_w += ww
                if lines > max_lines: max_lines = lines
                
            row_height = max_lines * line_h
            if pdf.get_y() + row_height > 270: 
                pdf.add_page()
            start_y = pdf.get_y()
            pdf.set_x(10)
            for i, val in enumerate(row_data):
                start_x = pdf.get_x()
                align_col = 'C' if is_header else ('R' if df_export.columns[i] in num_cols else 'L')
                if is_footer and i == len(df_export.columns) - 2: align_col = 'R'
                if is_header:
                    pdf.set_fill_color(220, 220, 220)
                    pdf.rect(start_x, start_y, col_widths[i], row_height, style='DF')
                elif is_footer:
                    pdf.set_fill_color(240, 240, 240)
                    pdf.rect(start_x, start_y, col_widths[i], row_height, style='DF')
                else:
                    pdf.rect(start_x, start_y, col_widths[i], row_height)
                pdf.multi_cell(col_widths[i], line_h, val, border=0, align=align_col)
                pdf.set_xy(start_x + col_widths[i], start_y)
            pdf.set_y(start_y + row_height)

        pdf.set_font(font_name, 'B' if font_name == 'ArialVN' else '', 8)
        headers = [txt(col) for col in df_export.columns]
        draw_row(headers, is_header=True)
        
        pdf.set_font(font_name, '', 8)
        for _, row in df_export.iterrows():
            row_data = []
            for col_name, item in row.items():
                val_str = str(item) if pd.notnull(item) else ""
                if col_name in num_cols and val_str.strip() != "":
                    try: 
                        val = float(item)
                        val_str = f"{val:,.0f}".replace(",", ".")
                        if col_name in ["Tổng tiền", "TỔNG CỘNG", "Tổng giá trị khuôn", "Tổng giá gia công", "Cọc đợt 1", "Còn nợ"]:
                            sum_tong_tien += val
                    except: pass
                row_data.append(txt(val_str))
            draw_row(row_data)
            
        if any(c in df_export.columns for c in ["Tổng tiền", "TỔNG CỘNG", "Tổng giá trị khuôn"]):
            pdf.set_font(font_name, 'B' if font_name == 'ArialVN' else '', 9)
            footer_data = []
            for i, col in enumerate(df_export.columns):
                if col in ["Tổng tiền", "TỔNG CỘNG", "Tổng giá trị khuôn"]:
                    footer_data.append(txt(f"{sum_tong_tien:,.0f}".replace(",", ".")))
                elif i == len(df_export.columns) - 2:
                    footer_data.append(txt("TỔNG CỘNG:"))
                else:
                    footer_data.append("")
            draw_row(footer_data, is_footer=True)
            
        if ghi_chu_data:
            valid_gc = [str(g).strip() for g in ghi_chu_data if pd.notnull(g) and str(g).strip() != "" and str(g).strip() != "None"]
            if valid_gc:
                pdf.ln(5)
                pdf.set_x(10)
                pdf.set_font(font_name, 'B' if font_name == 'ArialVN' else '', 9)
                pdf.set_fill_color(220, 220, 220)
                pdf.cell(190, 8, txt=txt("GHI CHÚ"), border=1, ln=True, align='C', fill=True)
                pdf.set_x(10)
                pdf.set_font(font_name, '', 9)
                combined_gc = "\n".join([f"- {g}" for g in valid_gc]) if len(valid_gc) > 1 else valid_gc[0]
                pdf.multi_cell(190, 6, txt=txt(combined_gc), border=1, align='L')
            
    temp_filename = f"temp_report_{datetime.now().strftime('%H%M%S')}.pdf"
    pdf.output(temp_filename)
    with open(temp_filename, "rb") as f:
        pdf_bytes = f.read()
    if os.path.exists(temp_filename):
        os.remove(temp_filename)
    return pdf_bytes

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

# ==========================================
# KHỞI TẠO DỮ LIỆU TỪ DB
# ==========================================
cols_A = ["Ngày", "Nhà cung cấp NVL", "Mã khuôn", "Tên NVL", "Quy cách", "Số lượng", "Đơn giá", "Tổng tiền"]
df_A = load_data("wanchi_a", cols_A)
df_A = df_A.loc[:, ~df_A.columns.duplicated()]

# --- CẬP NHẬT: Đổi tên cột Cụm khuôn thành Ráp khuôn ---
cols_B = ["Ngày", "Đơn vị gia công", "Mã khuôn", "Cắt dây", "Xung điện (EDM)", "Phay CNC", "Nhiệt Luyện", "Đánh bóng", "Tạo Nhám hoa văn", "Dọn phôi", "Ráp khuôn hoàn chỉnh", "Tổng tiền"]
df_B = load_data("wanchi_b", cols_B)
if "Đơn giá" in df_B.columns: df_B.rename(columns={"Đơn giá": "Ráp khuôn hoàn chỉnh"}, inplace=True)
if "Cụm khuôn hoàn chỉnh" in df_B.columns: df_B.rename(columns={"Cụm khuôn hoàn chỉnh": "Ráp khuôn hoàn chỉnh"}, inplace=True)
if "Ráp khuôn hoàn thiện" in df_B.columns: df_B.rename(columns={"Ráp khuôn hoàn thiện": "Ráp khuôn hoàn chỉnh"}, inplace=True)
df_B = df_B.loc[:, ~df_B.columns.duplicated()]
if "Dọn phôi" not in df_B.columns: df_B["Dọn phôi"] = 0
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

cols_Doitac = ["Phân loại", "Tên đối tác"]
df_Doitac = load_data("wanchi_doitac", cols_Doitac)
df_Doitac = df_Doitac.loc[:, ~df_Doitac.columns.duplicated()]

all_molds_set = set()
if not df_A.empty: all_molds_set.update(df_A["Mã khuôn"].dropna().unique())
if not df_B.empty: all_molds_set.update(df_B["Mã khuôn"].dropna().unique())
if not df_C.empty: all_molds_set.update(df_C["Mã khuôn"].dropna().unique())
if not df_D.empty: all_molds_set.update(df_D["Mã khuôn"].dropna().unique())
if not df_F.empty: all_molds_set.update(df_F["Mã khuôn"].dropna().unique())
list_molds_master = sorted(list(all_molds_set))

# ==========================================
# GIAO DIỆN CHÍNH & LƯỚI ĐIỀU HƯỚNG
# ==========================================
st.title("🏭 Công Cụ Quản Lý Khuôn Mẫu WANCHI")
st.markdown("---")

if "current_tab" not in st.session_state:
    st.session_state.current_tab = "➕ Tạo Khuôn Mới"

menu_items = [
    "➕ Tạo Khuôn Mới",
    "A. Nguyên Vật Liệu", 
    "B. Gia Công", 
    "C. Vật Tư Khuôn Mẫu", 
    "D. Tổng Giá Khuôn",
    "E. Danh Mục",
    "F. Tạo đơn Gia công",
    "G. Theo Dõi Đơn Hàng"
]

for i in range(0, len(menu_items), 4):
    cols = st.columns(4)
    for j, col in enumerate(cols):
        if i + j < len(menu_items):
            item = menu_items[i + j]
            btn_style = "primary" if st.session_state.current_tab == item else "secondary"
            if col.button(item, use_container_width=True, type=btn_style):
                st.session_state.current_tab = item
                st.rerun()

st.markdown("---")

# ------------------------------------------
# MODULE 0: TẠO KHUÔN MỚI
# ------------------------------------------
if st.session_state.current_tab == "➕ Tạo Khuôn Mới":
    st.header("➕ Khởi Tạo Dự Án Khuôn Mới")
    st.info("Khuôn mới sẽ được ghi danh vào hệ thống (Danh Mục) để bạn có thể chọn khi nhập liệu, không làm rác các bảng chi tiết.")
    
    with st.form("form_tao_khuon_moi", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        ngay_tao = c1.date_input("Ngày Khởi Tạo", datetime.today())
        khach_hang = c2.text_input("Tên Khách Hàng (Tùy chọn)")
        ma_khuon_moi = c3.text_input("Nhập Mã Khuôn Mới (*)", help="Bắt buộc nhập. VD: KHUON_ABC")
        
        st.write("")
        btn_tao_khuon = st.form_submit_button("🚀 XÁC NHẬN TẠO KHUÔN MỚI", type="primary", use_container_width=True)
        
        if btn_tao_khuon:
            ma_khuon_moi = ma_khuon_moi.strip().upper()
            if not ma_khuon_moi:
                st.error("⚠️ Vui lòng nhập Mã Khuôn!")
            elif ma_khuon_moi in list_molds_master:
                st.error(f"⚠️ Mã khuôn **{ma_khuon_moi}** đã tồn tại trong hệ thống. Vui lòng nhập mã khác!")
            else:
                with st.spinner("⏳ Đang khởi tạo kết nối toàn hệ thống..."):
                    ngay_str = ngay_tao.strftime('%d/%m/%Y')
                    row_d = {"Ngày": ngay_str, "Mã khuôn": ma_khuon_moi, "Tổng Nguyên Vật Liệu (A)": 0, "Tổng Gia Công (B)": 0, "Tổng Vật Tư (C)": 0, "TỔNG CỘNG": 0}
                    append_data(row_d, "wanchi_d", df_D)
                st.success(f"🎉 Khởi tạo khuôn **{ma_khuon_moi}** thành công! Mã khuôn này hiện đã có mặt trong Danh Mục để bạn chọn.")
                time.sleep(2)
                st.rerun()

# ------------------------------------------
# MODULE A: NGUYÊN VẬT LIỆU
# ------------------------------------------
elif st.session_state.current_tab == "A. Nguyên Vật Liệu":
    st.header("A. Nguyên Vật Liệu")
    with st.expander("➕ Nhập Nguyên Vật Liệu Mới"):
        with st.form("form_A"):
            c1, c2, c3, c4 = st.columns(4)
            ngay_a = c1.date_input("Ngày", datetime.today())
            ncc_a = c2.text_input("Nhà cung cấp NVL")
            ma_khuon_a = c3.selectbox("Chọn mã khuôn:", list_molds_master) if list_molds_master else c3.text_input("Mã khuôn")
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
    df_A_disp = df_A.copy()
    df_A_disp.insert(0, "Chọn", False)
    
    edited_A = st.data_editor(df_A_disp, num_rows="dynamic", use_container_width=True, hide_index=True, key="edit_A")
    edited_A["Chọn"] = edited_A["Chọn"].fillna(False).astype(bool)
    
    if st.button("💾 CẬP NHẬT DỮ LIỆU NGUYÊN VẬT LIỆU", type="primary", use_container_width=True):
        with st.spinner("⏳ Đang cập nhật dữ liệu, vui lòng đợi..."):
            save_data(edited_A.drop(columns=["Chọn"]), "wanchi_a")
        st.success("✅ Đã cập nhật thành công!")
        time.sleep(1)
        st.rerun()
            
    st.markdown("---")
    col_a2, col_a3 = st.columns(2)
    with col_a2:
        if st.button("🖼️ Tạo file ẢNH", use_container_width=True, key="btn_img_a"):
            selected_A = edited_A[edited_A["Chọn"] == True]
            if selected_A.empty:
                st.warning("⚠️ Vui lòng tick chọn ít nhất 1 dòng để xuất ảnh!")
            else:
                with st.spinner("Đang trích xuất file ẢNH..."):
                    unique_molds = selected_A["Mã khuôn"].dropna().unique().tolist()
                    filter_pdf_a = unique_molds[0] if len(unique_molds) == 1 else "NHIỀU MÃ KHUÔN"
                    
                    kh_str = None
                    if filter_pdf_a != "NHIỀU MÃ KHUÔN":
                        try:
                            row_kh = df_A[(df_A["Mã khuôn"] == filter_pdf_a) & (df_A["Tên NVL"] == "Khởi tạo khuôn")]
                            if not row_kh.empty:
                                kh_raw = str(row_kh.iloc[0]["Nhà cung cấp NVL"])
                                if kh_raw.startswith("KH: "):
                                    kh_str = kh_raw[4:]
                                elif kh_raw and kh_raw.strip():
                                    kh_str = kh_raw
                        except: pass
                        
                    pdf_a = export_pdf(selected_A.drop(columns=["Chọn"]), title="BÁO CÁO NGUYÊN VẬT LIỆU", ma_khuon_str=filter_pdf_a if filter_pdf_a != "NHIỀU MÃ KHUÔN" else None, khach_hang_str=kh_str)
                    st.session_state['img_a'] = convert_pdf_to_png(pdf_a)
                    st.session_state['file_name_a'] = f"WANCHI_NVL_{filter_pdf_a}.png"
                    
    with col_a3:
        if st.session_state.get('img_a'):
            st.download_button("⬇️ Tải ẢNH Xuống", st.session_state['img_a'], st.session_state.get('file_name_a', "WANCHI_NVL.png"), "image/png", type="primary", use_container_width=True)

# ------------------------------------------
# MODULE B: GIA CÔNG
# ------------------------------------------
elif st.session_state.current_tab == "B. Gia Công":
    st.header("B. Gia Công")
    with st.expander("➕ Nhập Chi Phí Gia Công Mới"):
        with st.form("form_B"):
            c1, c2, c3 = st.columns(3)
            ngay_b = c1.date_input("Ngày", datetime.today(), key="ngay_b")
            ncc_b = c2.text_input("Đơn vị gia công")
            ma_khuon_b = c3.selectbox("Chọn mã khuôn:", list_molds_master) if list_molds_master else c3.text_input("Mã khuôn")
            
            c4, c5, c6 = st.columns(3)
            cat_day = c4.number_input("Cắt dây", min_value=0, step=1)
            xung_dien = c5.number_input("Xung điện (EDM)", min_value=0, step=1)
            phay_cnc = c6.number_input("Phay CNC", min_value=0, step=1)
            
            c7, c8, c9 = st.columns(3)
            nhiet_luyen = c7.number_input("Nhiệt Luyện", min_value=0, step=1)
            danh_bong = c8.number_input("Đánh bóng", min_value=0, step=1)
            nham = c9.number_input("Tạo Nhám hoa văn", min_value=0, step=1)
            
            c10, c11, _ = st.columns(3)
            don_phoi = c10.number_input("Dọn phôi", min_value=0, step=1)
            # --- CẬP NHẬT: Đổi tên thành Ráp khuôn hoàn chỉnh ---
            rap_khuon = c11.number_input("Ráp khuôn hoàn chỉnh", min_value=0, step=1)
            
            st.markdown("---")
            _, c12 = st.columns([3, 1])
            tong_tien_b = c12.number_input("💰 Tổng tiền (Tự nhập)", min_value=0, step=1, key="tong_tien_b")
            
            if st.form_submit_button("Lưu Dữ Liệu Gia Công"):
                with st.spinner("⏳ Đang lưu dữ liệu..."):
                    new_row_b = {"Ngày": ngay_b.strftime('%d/%m/%Y'), "Đơn vị gia công": ncc_b, "Mã khuôn": ma_khuon_b.strip().upper(),
                                 "Cắt dây": cat_day, "Xung điện (EDM)": xung_dien, "Phay CNC": phay_cnc, "Nhiệt Luyện": nhiet_luyen,
                                 "Đánh bóng": danh_bong, "Tạo Nhám hoa văn": nham, "Dọn phôi": don_phoi, 
                                 "Ráp khuôn hoàn chỉnh": rap_khuon, "Tổng tiền": tong_tien_b}
                    append_data(new_row_b, "wanchi_b", df_B)
                st.rerun()

    st.subheader("Bảng Dữ Liệu Gia Công")
    df_B_disp = df_B.copy()
    df_B_disp.insert(0, "Chọn", False)
    
    edited_B = st.data_editor(df_B_disp, num_rows="dynamic", use_container_width=True, hide_index=True, key="edit_B")
    edited_B["Chọn"] = edited_B["Chọn"].fillna(False).astype(bool)
    
    if st.button("💾 CẬP NHẬT DỮ LIỆU GIA CÔNG", type="primary", use_container_width=True):
        with st.spinner("⏳ Đang cập nhật dữ liệu..."):
            save_data(edited_B.drop(columns=["Chọn"]), "wanchi_b")
        st.success("✅ Đã cập nhật thành công!")
        time.sleep(1)
        st.rerun()
            
    st.markdown("---")
    col_b2, col_b3 = st.columns(2)
    with col_b2:
        if st.button("🖼️ Tạo file ẢNH", use_container_width=True, key="btn_img_b"):
            selected_B = edited_B[edited_B["Chọn"] == True]
            if selected_B.empty:
                st.warning("⚠️ Vui lòng tick chọn ít nhất 1 dòng để xuất ảnh!")
            else:
                with st.spinner("Đang trích xuất file ẢNH..."):
                    unique_molds = selected_B["Mã khuôn"].dropna().unique().tolist()
                    filter_pdf_b = unique_molds[0] if len(unique_molds) == 1 else "NHIỀU MÃ KHUÔN"
                    
                    kh_str = None
                    if filter_pdf_b != "NHIỀU MÃ KHUÔN":
                        try:
                            row_kh = df_A[(df_A["Mã khuôn"] == filter_pdf_b) & (df_A["Tên NVL"] == "Khởi tạo khuôn")]
                            if not row_kh.empty:
                                kh_raw = str(row_kh.iloc[0]["Nhà cung cấp NVL"])
                                if kh_raw.startswith("KH: "):
                                    kh_str = kh_raw[4:]
                                elif kh_raw and kh_raw.strip():
                                    kh_str = kh_raw
                        except: pass
                    
                    pdf_b = export_pdf(selected_B.drop(columns=["Chọn"]), title="BÁO CÁO CHI PHÍ GIA CÔNG", ma_khuon_str=filter_pdf_b if filter_pdf_b != "NHIỀU MÃ KHUÔN" else None, khach_hang_str=kh_str)
                    st.session_state['img_b'] = convert_pdf_to_png(pdf_b)
                    st.session_state['file_name_b'] = f"WANCHI_GiaCong_{filter_pdf_b}.png"
                    
    with col_b3:
        if st.session_state.get('img_b'):
            st.download_button("⬇️ Tải ẢNH Xuống", st.session_state['img_b'], st.session_state.get('file_name_b', "WANCHI_GiaCong.png"), "image/png", type="primary", use_container_width=True)

# ------------------------------------------
# MODULE C: VẬT TƯ
# ------------------------------------------
elif st.session_state.current_tab == "C. Vật Tư Khuôn Mẫu":
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
    df_C_disp = df_C.copy()
    df_C_disp.insert(0, "Chọn", False)
    
    edited_C = st.data_editor(df_C_disp, num_rows="dynamic", use_container_width=True, hide_index=True, key="edit_C")
    edited_C["Chọn"] = edited_C["Chọn"].fillna(False).astype(bool)
    
    if st.button("💾 CẬP NHẬT DỮ LIỆU VẬT TƯ", type="primary", use_container_width=True):
        with st.spinner("⏳ Đang cập nhật dữ liệu..."):
            save_data(edited_C.drop(columns=["Chọn"]), "wanchi_c")
        st.success("✅ Đã cập nhật thành công!")
        time.sleep(1)
        st.rerun()
            
    st.markdown("---")
    col_c2, col_c3 = st.columns(2)
    with col_c2:
        if st.button("🖼️ Tạo file ẢNH", use_container_width=True, key="btn_img_c"):
            selected_C = edited_C[edited_C["Chọn"] == True]
            if selected_C.empty:
                st.warning("⚠️ Vui lòng tick chọn ít nhất 1 dòng để xuất ảnh!")
            else:
                with st.spinner("Đang trích xuất file ẢNH..."):
                    unique_molds = selected_C["Mã khuôn"].dropna().unique().tolist()
                    filter_pdf_c = unique_molds[0] if len(unique_molds) == 1 else "NHIỀU MÃ KHUÔN"
                    
                    kh_str = None
                    if filter_pdf_c != "NHIỀU MÃ KHUÔN":
                        try:
                            row_kh = df_A[(df_A["Mã khuôn"] == filter_pdf_c) & (df_A["Tên NVL"] == "Khởi tạo khuôn")]
                            if not row_kh.empty:
                                kh_raw = str(row_kh.iloc[0]["Nhà cung cấp NVL"])
                                if kh_raw.startswith("KH: "):
                                    kh_str = kh_raw[4:]
                                elif kh_raw and kh_raw.strip():
                                    kh_str = kh_raw
                        except: pass
                    
                    pdf_c = export_pdf(selected_C.drop(columns=["Chọn"]), title="BÁO CÁO VẬT TƯ", ma_khuon_str=filter_pdf_c if filter_pdf_c != "NHIỀU MÃ KHUÔN" else None, khach_hang_str=kh_str)
                    st.session_state['img_c'] = convert_pdf_to_png(pdf_c)
                    st.session_state['file_name_c'] = f"WANCHI_VatTu_{filter_pdf_c}.png"
                    
    with col_c3:
        if st.session_state.get('img_c'):
            st.download_button("⬇️ Tải ẢNH Xuống", st.session_state['img_c'], st.session_state.get('file_name_c', "WANCHI_VatTu.png"), "image/png", type="primary", use_container_width=True)

# ------------------------------------------
# MODULE D: TỔNG KẾT
# ------------------------------------------
elif st.session_state.current_tab == "D. Tổng Giá Khuôn":
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
            st.success("✅ Đã tính toán xong và lưu thành công!")
            time.sleep(1)
            st.rerun()

    st.markdown("---")
    st.subheader("Bảng Tổng Hợp Chi Phí")
    df_D_disp = df_D.copy()
    df_D_disp.insert(0, "Chọn", False)
    
    edited_D = st.data_editor(df_D_disp, num_rows="dynamic", use_container_width=True, hide_index=True, key="edit_D")
    edited_D["Chọn"] = edited_D["Chọn"].fillna(False).astype(bool)
    
    if st.button("💾 CẬP NHẬT BẢNG TỔNG", type="primary", use_container_width=True):
        with st.spinner("⏳ Đang lưu dữ liệu..."):
            save_data(edited_D.drop(columns=["Chọn"]), "wanchi_d")
        st.success("✅ Đã lưu các thay đổi!")
        time.sleep(1)
        st.rerun()
            
    st.markdown("---")
    col_d2, col_d3 = st.columns(2)
    with col_d2:
        if st.button("🖼️ Tạo file ẢNH", use_container_width=True, key="btn_img_d"):
            selected_D = edited_D[edited_D["Chọn"] == True]
            if selected_D.empty:
                st.warning("⚠️ Vui lòng tick chọn ít nhất 1 dòng để xuất ảnh!")
            else:
                with st.spinner("Đang trích xuất file ẢNH..."):
                    unique_molds = selected_D["Mã khuôn"].dropna().unique().tolist()
                    filter_pdf_d = unique_molds[0] if len(unique_molds) == 1 else "NHIỀU MÃ KHUÔN"
                    
                    kh_str = None
                    if filter_pdf_d != "NHIỀU MÃ KHUÔN":
                        try:
                            row_kh = df_A[(df_A["Mã khuôn"] == filter_pdf_d) & (df_A["Tên NVL"] == "Khởi tạo khuôn")]
                            if not row_kh.empty:
                                kh_raw = str(row_kh.iloc[0]["Nhà cung cấp NVL"])
                                if kh_raw.startswith("KH: "):
                                    kh_str = kh_raw[4:]
                                elif kh_raw and kh_raw.strip():
                                    kh_str = kh_raw
                        except: pass
                        
                    pdf_d = export_pdf(selected_D.drop(columns=["Chọn"]), title="BẢNG TỔNG HỢP CHI PHÍ", ma_khuon_str=filter_pdf_d if filter_pdf_d != "NHIỀU MÃ KHUÔN" else None, khach_hang_str=kh_str)
                    st.session_state['img_d'] = convert_pdf_to_png(pdf_d)
                    st.session_state['file_name_d'] = f"WANCHI_TongHop_{filter_pdf_d}.png"
                    
    with col_d3:
        if st.session_state.get('img_d'):
            st.download_button("⬇️ Tải ẢNH Xuống", st.session_state['img_d'], st.session_state.get('file_name_d', "WANCHI_TongHop.png"), "image/png", type="primary", use_container_width=True)

# ------------------------------------------
# MODULE E: DANH MỤC QUẢN LÝ (KHUÔN, NCC, NGC)
# ------------------------------------------
elif st.session_state.current_tab == "E. Danh Mục":
    st.header("E. Danh Mục Hệ Thống")
    st.markdown("Bảng điều khiển 2 cột: Quản lý danh sách Khuôn mẫu hiện hành và Hệ thống đối tác (Nhà cung cấp, Nhà gia công).")
    
    col_k, col_dt = st.columns(2)
    
    # ------------------ CỘT 1: DANH SÁCH KHUÔN ------------------
    with col_k:
        st.subheader("📋 Danh Sách Khuôn")
        
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
                "Ngày bắt đầu": ngay_lam,
                "Mã khuôn": mk,
                "Tổng giá trị (VNĐ)": f"{tong_gia:,.0f}" if tong_gia > 0 else "0"
            })
            
        df_E = pd.DataFrame(danh_sach_khuon_data)
        
        if not df_E.empty:
            st.dataframe(df_E, use_container_width=True, hide_index=True)
        else:
            st.info("Chưa có khuôn nào trong hệ thống.")

    # ------------------ CỘT 2: DANH SÁCH ĐỐI TÁC ------------------
    with col_dt:
        st.subheader("🤝 Danh Sách NCC, NGC")
        
        with st.form("form_them_doitac", clear_on_submit=True):
            c_loai, c_ten = st.columns([1, 2])
            loai_doitac = c_loai.selectbox("Phân loại", ["Nhà cung cấp (NCC)", "Nhà gia công (NGC)"])
            ten_doitac = c_ten.text_input("Nhập tên Đối tác (NCC / NGC)")
            
            if st.form_submit_button("➕ Thêm Đối Tác Mới", type="primary", use_container_width=True):
                if ten_doitac.strip():
                    with st.spinner("Đang lưu đối tác..."):
                        new_row_dt = {"Phân loại": loai_doitac, "Tên đối tác": ten_doitac.strip()}
                        append_data(new_row_dt, "wanchi_doitac", df_Doitac)
                    st.success("✅ Đã thêm vào danh sách đối tác!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.warning("⚠️ Vui lòng nhập tên Đối tác!")
                    
        if not df_Doitac.empty:
            st.dataframe(df_Doitac, use_container_width=True, hide_index=True)
        else:
            st.info("Danh sách đối tác đang trống.")

# ------------------------------------------
# MODULE F: TẠO ĐƠN HÀNG GIA CÔNG
# ------------------------------------------
elif st.session_state.current_tab == "F. Tạo đơn Gia công":
    st.header("F. Tạo đơn Gia công")
    st.markdown("Khởi tạo đơn hàng mới, đặt cọc và các hạng mục thuê gia công.")
    
    with st.form("form_f"):
        c1, c2 = st.columns(2)
        ma_khuon_f = c1.selectbox("Mã khuôn", list_molds_master) if list_molds_master else c1.text_input("Mã khuôn")
        
        list_ngc = []
        if not df_Doitac.empty:
            list_ngc = df_Doitac[df_Doitac["Phân loại"] == "Nhà gia công (NGC)"]["Tên đối tác"].dropna().unique().tolist()
            
        old_vendors = df_F["Đơn vị gia công"].dropna().unique().tolist() if not df_F.empty else []
        for v in old_vendors:
            if v not in list_ngc:
                list_ngc.append(v)
                
        if list_ngc:
            dv_select = c2.selectbox("Chọn đơn vị gia công", list_ngc)
        else:
            dv_select = c2.selectbox("Chọn đơn vị gia công", ["-- Chưa có nhà gia công --"])
        
        st.markdown("---")
        danh_sach_hang_muc = ["Cắt dây", "Xung điện (EDM)", "Phay CNC", "Nhiệt Luyện", "Đánh bóng", "Tạo Nhám hoa văn", "Dọn phôi", "Ráp khuôn hoàn chỉnh"]
        hang_muc = st.multiselect("Các hạng mục cần gia công:", danh_sach_hang_muc)
        
        c3, c4 = st.columns(2)
        ngay_nhan = c3.date_input("Thời gian nhận phôi/khuôn")
        ngay_giao = c4.date_input("Thời gian bàn giao (Dự kiến)")
        
        st.markdown("---")
        c5, c6, c7 = st.columns(3)
        tong_gia_f = c5.number_input("Tổng giá gia công", min_value=0, step=1)
        coc_f = c6.number_input("Cọc đợt 1", min_value=0, step=1)
        ghi_chu_f = c7.text_area("Ghi chú (Tự động kéo giãn khi xuất bảng)")
        
        if st.form_submit_button("Tạo đơn hàng mới"):
            final_dv = dv_select
            if not final_dv or final_dv == "-- Chưa có nhà gia công --":
                st.error("⚠️ Vui lòng chọn Đơn vị gia công (Nếu chưa có, hãy sang Tab E. Danh Mục để thêm)!")
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
                st.success("✅ Đã tạo đơn hàng gia công mới thành công!")
                time.sleep(1)
                st.rerun()

# ------------------------------------------
# MODULE G: THEO DÕI ĐƠN HÀNG GIA CÔNG
# ------------------------------------------
elif st.session_state.current_tab == "G. Theo Dõi Đơn Hàng":
    st.header("G. Theo Dõi Đơn Hàng")
    st.markdown("Kiểm tra, cập nhật công nợ và quản lý danh sách đơn hàng đã tạo.")
    
    st.subheader("Bảng Theo Dõi Đơn Hàng")
    df_F_disp = df_F.copy()
    df_F_disp.insert(0, "Chọn", False)
    
    edited_F = st.data_editor(df_F_disp, num_rows="dynamic", use_container_width=True, hide_index=True, key="edit_F")
    edited_F["Chọn"] = edited_F["Chọn"].fillna(False).astype(bool)
    
    if st.button("💾 CẬP NHẬT DỮ LIỆU ĐƠN HÀNG", type="primary", use_container_width=True):
        with st.spinner("⏳ Đang cập nhật..."):
            save_data(edited_F.drop(columns=["Chọn"]), "wanchi_f")
        st.success("✅ Đã cập nhật thành công!")
        time.sleep(1)
        st.rerun()
            
    st.markdown("---")
    col_f2, col_f3 = st.columns(2)
    with col_f2:
        if st.button("🖼️ Tạo file ẢNH", use_container_width=True, key="btn_img_f"):
            selected_F = edited_F[edited_F["Chọn"] == True]
            if selected_F.empty:
                st.warning("⚠️ Vui lòng tick chọn ít nhất 1 dòng để xuất ảnh!")
            else:
                with st.spinner("Đang trích xuất file ẢNH..."):
                    unique_molds = selected_F["Mã khuôn"].dropna().unique().tolist()
                    filter_pdf_mold_f = unique_molds[0] if len(unique_molds) == 1 else "NHIỀU MÃ KHUÔN"
                    
                    unique_vendors = selected_F["Đơn vị gia công"].dropna().unique().tolist()
                    filter_pdf_vendor_f = unique_vendors[0] if len(unique_vendors) == 1 else None
                    
                    kh_str = None
                    if filter_pdf_mold_f != "NHIỀU MÃ KHUÔN":
                        try:
                            row_kh = df_A[(df_A["Mã khuôn"] == filter_pdf_mold_f) & (df_A["Tên NVL"] == "Khởi tạo khuôn")]
                            if not row_kh.empty:
                                kh_raw = str(row_kh.iloc[0]["Nhà cung cấp NVL"])
                                if kh_raw.startswith("KH: "):
                                    kh_str = kh_raw[4:]
                                elif kh_raw and kh_raw.strip():
                                    kh_str = kh_raw
                        except: pass
                    
                    pdf_f = export_pdf(selected_F.drop(columns=["Chọn"]), title="ĐƠN HÀNG GIA CÔNG", ma_khuon_str=filter_pdf_mold_f if filter_pdf_mold_f != "NHIỀU MÃ KHUÔN" else None, khach_hang_str=kh_str, dvgc_str=filter_pdf_vendor_f)
                    st.session_state['img_f'] = convert_pdf_to_png(pdf_f)
                    
                    safe_name = f"{filter_pdf_mold_f}_{filter_pdf_vendor_f}" if filter_pdf_vendor_f else filter_pdf_mold_f
                    st.session_state['file_name_f'] = f"WANCHI_DonHang_{safe_name}.png"

    with col_f3:
        if st.session_state.get('img_f'):
            st.download_button("⬇️ Tải ẢNH Xuống", st.session_state['img_f'], st.session_state.get('file_name_f', "WANCHI_DonHang.png"), "image/png", type="primary", use_container_width=True)
