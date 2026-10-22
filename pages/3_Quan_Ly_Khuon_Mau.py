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
    """Hàm chuyển byte PDF thành byte Ảnh PNG độ nét cao"""
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

# ---> HÀM XUẤT PDF (BẢN VẼ LÕI ĐỂ CHUYỂN ẢNH) <---
def export_pdf(df, title, ma_khuon_str=None, khach_hang_str=None, dvgc_str=None):
    df_export = df.copy()
    if "Cụm khuôn hoàn chỉnh" in df_export.columns:
        df_export = df_export.drop(columns=["Cụm khuôn hoàn chỉnh"])
        
    # Xóa cột Mã khuôn khỏi bảng
    if "Mã khuôn" in df_export.columns:
        df_export = df_export.drop(columns=["Mã khuôn"])
        
    # Tách Đơn vị gia công ra khỏi bảng
    dvgc_text = ""
    if "Đơn vị gia công" in df_export.columns:
        unique_dv = [str(x) for x in df_export["Đơn vị gia công"].dropna().unique() if str(x).strip()]
        if unique_dv:
            dvgc_text = "Đơn vị gia công: " + ", ".join(unique_dv)
        df_export = df_export.drop(columns=["Đơn vị gia công"])
    
    # Định dạng khổ A4 Dọc (Portrait)
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.add_page()
    
    try:
        pdf.add_font('ArialVN', '', 'arial.ttf', uni=True)
        pdf.add_font('ArialVN', 'B', 'arialbd.ttf', uni=True)
        font_name = 'ArialVN'
    except:
        font_name = 'Arial'
        st.warning("⚠️ Không tìm thấy file 'arial.ttf'. Hệ thống sẽ xuất PDF không dấu để tránh lỗi.")

    def txt(s):
        return remove_accents(str(s)) if font_name == 'Arial' else str(s)

    # --- XỬ LÝ LOGO VÀ ĐỊA CHỈ ---
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

    # --- IN TIÊU ĐỀ CHÍNH ---
    pdf.set_x(10)
    pdf.set_font(font_name, 'B' if font_name == 'ArialVN' else '', 16)
    
    clean_title_lines = [line for line in title.split('\n') if not line.startswith("ĐƠN VỊ GIA CÔNG") and not line.startswith("MÃ KHUÔN")]
    clean_title = "\n".join(clean_title_lines)
    pdf.multi_cell(0, 8, txt=txt(clean_title.upper()), align='C')
    
    # --- IN THÔNG TIN PHỤ (Mã khuôn, Khách hàng, ĐVGC) (Không in hoa, Lề trái) ---
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

    # --- THUẬT TOÁN CO GIÃN CỘT VÀ XUỐNG DÒNG VĂN BẢN (LUÔN ÉP FULL 190MM) ---
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
            
            # Cấp diện tích tối đa cho các cột chứa text để ép xuống dòng
            if col in ["Ghi chú", "Các mục gia công", "Tên NVL", "Tên linh kiện", "Quy cách", "Nhà cung cấp NVL", "Khách hàng"]:
                if max_w > 45: max_w = 45
            elif max_w > 50: max_w = 50
                
            col_widths.append(max_w)
        
        # Bắt buộc kéo giãn bảng lấp đầy khổ A4 dọc (190mm)
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
            if pdf.get_y() + row_height > 270: # Vượt biên dưới của A4 Dọc
                pdf.add_page()
                
            start_y = pdf.get_y()
            pdf.set_x(10) # Reset X về 10 để đảm bảo mỗi dòng bảng đều bám sát lề trái
            
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
    "E. Danh Sách & Quản Trị",
    "F. Tạo Đơn Hàng Gia Công",
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
    st.info("Khi tạo khuôn mới tại đây, mã khuôn sẽ tự động xuất hiện ở tất cả các tab khác để anh/chị tiện chọn.")
    
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
                    ghi_chu_kh = f"KH: {khach_hang}" if khach_hang else ""
                    
                    row_a = {"Ngày": ngay_str, "Nhà cung cấp NVL": ghi_chu_kh, "Mã khuôn": ma_khuon_moi, "Tên NVL": "Khởi tạo khuôn", "Tổng tiền": 0}
                    append_data(row_a, "wanchi_a", df_A)
                    
                    row_b = {"Ngày": ngay_str, "Đơn vị gia công": ghi_chu_kh, "Mã khuôn": ma_khuon_moi, "Tổng tiền": 0}
                    append_data(row_b, "wanchi_b", df_B)
                    
                    row_c = {"Ngày": ngay_str, "Nhà cung cấp vật tư": ghi_chu_kh, "Mã khuôn": ma_khuon_moi, "Tên linh kiện": "Khởi tạo", "Tổng tiền": 0}
                    append_data(row_c, "wanchi_c", df_C)
                    
                    row_d = {"Ngày": ngay_str, "Mã khuôn": ma_khuon_moi, "Tổng Nguyên Vật Liệu (A)": 0, "Tổng Gia Công (B)": 0, "Tổng Vật Tư (C)": 0, "TỔNG CỘNG": 0}
                    append_data(row_d, "wanchi_d", df_D)
                    
                    row_f = {"Mã khuôn": ma_khuon_moi, "Đơn vị gia công": "Chưa có", "Các mục gia công": "Khởi tạo", "Thời gian nhận": ngay_str, "Thời gian bàn giao": ngay_str, "Tổng giá gia công": 0, "Cọc đợt 1": 0, "Còn nợ": 0, "Ghi chú": ghi_chu_kh}
                    append_data(row_f, "wanchi_f", df_F)
                    
                st.success(f"🎉 Khởi tạo khuôn **{ma_khuon_moi}** thành công! Bây giờ anh/chị có thể sang các Tab A, B, C để nhập chi tiết.")
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
    edited_A = st.data_editor(df_A, num_rows="dynamic", use_container_width=True, hide_index=True, key="edit_A")
    if st.button("💾 Cập nhật dữ liệu A"):
        with st.spinner("⏳ Đang cập nhật dữ liệu, vui lòng đợi..."):
            save_data(edited_A, "wanchi_a")
        st.success("✅ Đã cập nhật thành công!")
        st.rerun()
        
    st.markdown("---")
    st.subheader("📥 Xuất Báo Cáo ẢNH NÉT CAO")
    col_pdf1, col_pdf2 = st.columns([1, 2])
    filter_pdf_a = col_pdf1.selectbox("Chọn Mã khuôn để xuất Ảnh:", ["Tất cả"] + list_molds_master, key="pdf_a")
    
    if st.button("Tạo file ẢNH (Module A)"):
        with st.spinner("Đang trích xuất file ẢNH..."):
            df_export_a = edited_A if filter_pdf_a == "Tất cả" else edited_A[edited_A["Mã khuôn"] == filter_pdf_a]
            
            kh_str = None
            if filter_pdf_a != "Tất cả":
                try:
                    row_kh = df_A[(df_A["Mã khuôn"] == filter_pdf_a) & (df_A["Tên NVL"] == "Khởi tạo khuôn")]
                    if not row_kh.empty:
                        kh_raw = str(row_kh.iloc[0]["Nhà cung cấp NVL"])
                        if kh_raw.startswith("KH: "):
                            kh_str = kh_raw[4:]
                        elif kh_raw and kh_raw.strip():
                            kh_str = kh_raw
                except: pass
                
            pdf_a = export_pdf(df_export_a, title="BÁO CÁO NGUYÊN VẬT LIỆU", ma_khuon_str=filter_pdf_a if filter_pdf_a != "Tất cả" else None, khach_hang_str=kh_str)
            st.session_state['img_a'] = convert_pdf_to_png(pdf_a)
            
    if st.session_state.get('img_a'):
        col_pdf2.download_button("⬇️ Nhấn để Tải ẢNH Xuống", st.session_state['img_a'], f"WANCHI_NVL_{filter_pdf_a}.png", "image/png", type="primary")


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
            rap_khuon = c11.number_input("Cụm khuôn hoàn chỉnh", min_value=0, step=1)
            
            st.markdown("---")
            _, c12 = st.columns([3, 1])
            tong_tien_b = c12.number_input("💰 Tổng tiền (Tự nhập)", min_value=0, step=1, key="tong_tien_b")
            
            if st.form_submit_button("Lưu Dữ Liệu Gia Công"):
                with st.spinner("⏳ Đang lưu dữ liệu..."):
                    new_row_b = {"Ngày": ngay_b.strftime('%d/%m/%Y'), "Đơn vị gia công": ncc_b, "Mã khuôn": ma_khuon_b.strip().upper(),
                                 "Cắt dây": cat_day, "Xung điện (EDM)": xung_dien, "Phay CNC": phay_cnc, "Nhiệt Luyện": nhiet_luyen,
                                 "Đánh bóng": danh_bong, "Tạo Nhám hoa văn": nham, "Dọn phôi": don_phoi, 
                                 "Cụm khuôn hoàn chỉnh": rap_khuon, "Tổng tiền": tong_tien_b}
                    append_data(new_row_b, "wanchi_b", df_B)
                st.rerun()

    st.subheader("Bảng Dữ Liệu Gia Công")
    edited_B = st.data_editor(df_B, num_rows="dynamic", use_container_width=True, hide_index=True, key="edit_B")
    if st.button("💾 Cập nhật dữ liệu B"):
        with st.spinner("⏳ Đang cập nhật dữ liệu..."):
            save_data(edited_B, "wanchi_b")
        st.success("✅ Đã cập nhật thành công!")
        st.rerun()

    st.markdown("---")
    st.subheader("📥 Xuất Báo Cáo ẢNH NÉT CAO")
    col_pdf3, col_pdf4 = st.columns([1, 2])
    filter_pdf_b = col_pdf3.selectbox("Chọn Mã khuôn để xuất Ảnh:", ["Tất cả"] + list_molds_master, key="pdf_b")
    
    if st.button("Tạo file ẢNH (Module B)"):
        with st.spinner("Đang trích xuất file ẢNH..."):
            df_export_b = edited_B if filter_pdf_b == "Tất cả" else edited_B[edited_B["Mã khuôn"] == filter_pdf_b]
            
            kh_str = None
            if filter_pdf_b != "Tất cả":
                try:
                    row_kh = df_A[(df_A["Mã khuôn"] == filter_pdf_b) & (df_A["Tên NVL"] == "Khởi tạo khuôn")]
                    if not row_kh.empty:
                        kh_raw = str(row_kh.iloc[0]["Nhà cung cấp NVL"])
                        if kh_raw.startswith("KH: "):
                            kh_str = kh_raw[4:]
                        elif kh_raw and kh_raw.strip():
                            kh_str = kh_raw
                except: pass
                
            pdf_b = export_pdf(df_export_b, title="BÁO CÁO CHI PHÍ GIA CÔNG", ma_khuon_str=filter_pdf_b if filter_pdf_b != "Tất cả" else None, khach_hang_str=kh_str)
            st.session_state['img_b'] = convert_pdf_to_png(pdf_b)
            
    if st.session_state.get('img_b'):
        col_pdf4.download_button("⬇️ Nhấn để Tải ẢNH Xuống", st.session_state['img_b'], f"WANCHI_GiaCong_{filter_pdf_b}.png", "image/png", type="primary")


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
    edited_C = st.data_editor(df_C, num_rows="dynamic", use_container_width=True, hide_index=True, key="edit_C")
    if st.button("💾 Cập nhật dữ liệu C"):
        with st.spinner("⏳ Đang cập nhật dữ liệu..."):
            save_data(edited_C, "wanchi_c")
        st.success("✅ Đã cập nhật thành công!")
        st.rerun()

    st.markdown("---")
    st.subheader("📥 Xuất Báo Cáo ẢNH NÉT CAO")
    col_pdf5, col_pdf6 = st.columns([1, 2])
    filter_pdf_c = col_pdf5.selectbox("Chọn Mã khuôn để xuất Ảnh:", ["Tất cả"] + list_molds_master, key="pdf_c")
    
    if st.button("Tạo file ẢNH (Module C)"):
        with st.spinner("Đang trích xuất file ẢNH..."):
            df_export_c = edited_C if filter_pdf_c == "Tất cả" else edited_C[edited_C["Mã khuôn"] == filter_pdf_c]
            
            kh_str = None
            if filter_pdf_c != "Tất cả":
                try:
                    row_kh = df_A[(df_A["Mã khuôn"] == filter_pdf_c) & (df_A["Tên NVL"] == "Khởi tạo khuôn")]
                    if not row_kh.empty:
                        kh_raw = str(row_kh.iloc[0]["Nhà cung cấp NVL"])
                        if kh_raw.startswith("KH: "):
                            kh_str = kh_raw[4:]
                        elif kh_raw and kh_raw.strip():
                            kh_str = kh_raw
                except: pass
                
            pdf_c = export_pdf(df_export_c, title="BÁO CÁO VẬT TƯ", ma_khuon_str=filter_pdf_c if filter_pdf_c != "Tất cả" else None, khach_hang_str=kh_str)
            st.session_state['img_c'] = convert_pdf_to_png(pdf_c)
            
    if st.session_state.get('img_c'):
        col_pdf6.download_button("⬇️ Nhấn để Tải ẢNH Xuống", st.session_state['img_c'], f"WANCHI_VatTu_{filter_pdf_c}.png", "image/png", type="primary")


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
            st.rerun()

    st.markdown("---")
    st.subheader("Bảng Tổng Hợp Chi Phí")
    edited_D = st.data_editor(df_D, num_rows="dynamic", use_container_width=True, hide_index=True, key="edit_D")
    if st.button("💾 Cập nhật bảng Tổng"):
        with st.spinner("⏳ Đang lưu dữ liệu..."):
            save_data(edited_D, "wanchi_d")
        st.success("✅ Đã lưu các thay đổi!")
        st.rerun()
        
    st.markdown("---")
    st.subheader("📥 Xuất Báo Cáo ẢNH NÉT CAO")
    col_pdf1_d, col_pdf2_d = st.columns([1, 2])
    filter_pdf_d = col_pdf1_d.selectbox("Chọn Mã khuôn để xuất Ảnh:", ["Tất cả"] + list_molds_master, key="pdf_d")
    
    if st.button("Tạo file ẢNH (Module D)"):
        with st.spinner("Đang trích xuất file ẢNH..."):
            df_export_d = edited_D if filter_pdf_d == "Tất cả" else edited_D[edited_D["Mã khuôn"] == filter_pdf_d]
            
            kh_str = None
            if filter_pdf_d != "Tất cả":
                try:
                    row_kh = df_A[(df_A["Mã khuôn"] == filter_pdf_d) & (df_A["Tên NVL"] == "Khởi tạo khuôn")]
                    if not row_kh.empty:
                        kh_raw = str(row_kh.iloc[0]["Nhà cung cấp NVL"])
                        if kh_raw.startswith("KH: "):
                            kh_str = kh_raw[4:]
                        elif kh_raw and kh_raw.strip():
                            kh_str = kh_raw
                except: pass
                
            pdf_d = export_pdf(df_export_d, title="BẢNG TỔNG HỢP CHI PHÍ", ma_khuon_str=filter_pdf_d if filter_pdf_d != "Tất cả" else None, khach_hang_str=kh_str)
            st.session_state['img_d'] = convert_pdf_to_png(pdf_d)
            
    if st.session_state.get('img_d'):
        col_pdf2_d.download_button("⬇️ Nhấn để Tải ẢNH Xuống", st.session_state['img_d'], f"WANCHI_TongHop_{filter_pdf_d}.png", "image/png", type="primary")


# ------------------------------------------
# MODULE E: DANH SÁCH KHUÔN TỔNG HỢP & QUẢN TRỊ
# ------------------------------------------
elif st.session_state.current_tab == "E. Danh Sách & Quản Trị":
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
        st.subheader("📥 Xuất Báo Cáo ẢNH Danh Sách Khuôn")
        if st.button("Tạo file ẢNH (Module E)"):
            with st.spinner("Đang trích xuất file ẢNH..."):
                pdf_e = export_pdf(df_E, "DANH SÁCH TỔNG HỢP CÁC KHUÔN ĐÃ LÀM")
                st.session_state['img_e'] = convert_pdf_to_png(pdf_e)
                
        if st.session_state.get('img_e'):
            st.download_button("⬇️ Nhấn để Tải ẢNH Xuống", st.session_state['img_e'], "WANCHI_DanhSachKhuon.png", "image/png", type="primary")
            
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


# ------------------------------------------
# MODULE F: TẠO ĐƠN HÀNG GIA CÔNG
# ------------------------------------------
elif st.session_state.current_tab == "F. Tạo Đơn Hàng Gia Công":
    st.header("F. Tạo Đơn Hàng Gia Công")
    st.markdown("Khởi tạo đơn hàng mới, đặt cọc và các hạng mục thuê gia công.")
    
    with st.form("form_f"):
        c1, c2 = st.columns(2)
        ma_khuon_f = c1.selectbox("Mã khuôn", list_molds_master) if list_molds_master else c1.text_input("Mã khuôn")
        
        list_vendors = df_F["Đơn vị gia công"].dropna().unique().tolist() if not df_F.empty else []
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
        ghi_chu_f = c7.text_area("Ghi chú (Tự động kéo giãn khi xuất bảng)")
        
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
                st.success("✅ Đã tạo đơn hàng gia công mới thành công!")
                st.rerun()

# ------------------------------------------
# MODULE G: THEO DÕI ĐƠN HÀNG GIA CÔNG
# ------------------------------------------
elif st.session_state.current_tab == "G. Theo Dõi Đơn Hàng":
    st.header("G. Theo Dõi Đơn Hàng")
    st.markdown("Kiểm tra, cập nhật công nợ và quản lý danh sách đơn hàng đã tạo.")
    
    st.subheader("Bảng Theo Dõi Đơn Hàng")
    edited_F = st.data_editor(df_F, num_rows="dynamic", use_container_width=True, hide_index=True, key="edit_F")
    if st.button("💾 Cập nhật dữ liệu đơn hàng"):
        with st.spinner("⏳ Đang cập nhật..."):
            save_data(edited_F, "wanchi_f")
        st.success("✅ Đã cập nhật thành công!")
        st.rerun()
        
    st.markdown("---")
    st.subheader("📥 Xuất Báo Cáo ẢNH Đơn Hàng")
    
    col_pdf1_f, col_pdf2_f = st.columns([2, 1])
    
    # Gom Nhóm Tùy Chọn: Mã Khuôn + Đơn vị gia công
    options_f = ["Tất cả"]
    combo_list = []
    if not edited_F.empty:
        for _, r in edited_F.iterrows():
            mk = str(r.get('Mã khuôn', ''))
            dv = str(r.get('Đơn vị gia công', ''))
            if mk and dv:
                combo = f"{mk} | {dv}"
                if combo not in combo_list:
                    combo_list.append(combo)
    options_f.extend(combo_list)
    
    filter_pdf_f = col_pdf1_f.selectbox("Chọn đơn hàng (Mã khuôn | Đơn vị gia công) để xuất Ảnh:", options_f, key="pdf_combo_f")
    
    if st.button("Tạo file ẢNH (Module Theo Dõi Đơn Hàng)"):
        with st.spinner("Đang trích xuất file ẢNH..."):
            df_export_f = edited_F.copy()
            
            ma_khuon_chon = None
            dvgc_chon = None
            kh_str = None
            
            if filter_pdf_f != "Tất cả":
                ma_khuon_chon = filter_pdf_f.split(" | ")[0].strip()
                dvgc_chon = filter_pdf_f.split(" | ")[1].strip()
                
                df_export_f = df_export_f[(df_export_f["Mã khuôn"] == ma_khuon_chon) & (df_export_f["Đơn vị gia công"] == dvgc_chon)]
                
                # Quét Tên Khách hàng từ Module A
                try:
                    row_kh = df_A[(df_A["Mã khuôn"] == ma_khuon_chon) & (df_A["Tên NVL"] == "Khởi tạo khuôn")]
                    if not row_kh.empty:
                        kh_raw = str(row_kh.iloc[0]["Nhà cung cấp NVL"])
                        if kh_raw.startswith("KH: "):
                            kh_str = kh_raw[4:]
                        elif kh_raw and kh_raw.strip():
                            kh_str = kh_raw
                except: pass
                
            pdf_f = export_pdf(df_export_f, title="ĐƠN HÀNG GIA CÔNG", ma_khuon_str=ma_khuon_chon, khach_hang_str=kh_str, dvgc_str=dvgc_chon)
            st.session_state['img_f'] = convert_pdf_to_png(pdf_f)
            st.session_state['filter_f'] = filter_pdf_f
    
    if st.session_state.get('img_f'):
        safe_name = st.session_state['filter_f'].replace(" | ", "_").replace("/", "-")
        file_name_img = f"WANCHI_DonHang_{safe_name}.png" if safe_name != "Tất cả" else "WANCHI_DonHang_TatCa.png"
        
        col_pdf2_f.markdown("<br>", unsafe_allow_html=True)
        col_pdf2_f.download_button("⬇️ Nhấn để Tải ẢNH Xuống", st.session_state['img_f'], file_name_img, "image/png", type="primary")
