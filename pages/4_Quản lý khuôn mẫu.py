import streamlit as st
import pandas as pd
import time
import os
import unicodedata
from datetime import datetime
from sqlalchemy import text
from fpdf import FPDF

# --- KHÓA BẢO MẬT TỪ TRANG CHỦ ---
if not st.session_state.get("logged_in", False):
    st.warning("🔒 Bạn chưa đăng nhập! Vui lòng quay lại Trang Chủ (Home) để gõ mật khẩu.")
    st.stop()

# ==========================================
# CẤU HÌNH KẾT NỐI NEON (POSTGRESQL)
# ==========================================
try:
    conn = st.connection("postgresql", type="sql")
except Exception:
    st.error("Chưa thể kết nối đến cơ sở dữ liệu. Vui lòng kiểm tra lại file cấu hình Secrets.")
    st.stop()

# ==========================================
# 🛡️ LÍNH GÁC (GATEKEEPER) BẢO VỆ DỮ LIỆU
# ==========================================
def verify_database_connection(conn_obj, max_retries=3, delay=2):
    for attempt in range(max_retries):
        try:
            with conn_obj.session as session:
                session.execute(text("SELECT 1"))
            return True
        except Exception:
            if attempt < max_retries - 1:
                time.sleep(delay)
            else:
                return False

if "db_load_success" not in st.session_state:
    st.session_state["db_load_success"] = False

is_connected = verify_database_connection(conn)
st.session_state["db_load_success"] = is_connected

if not is_connected:
    st.error("🚨 HỆ THỐNG ĐANG BỊ KHÓA AN TOÀN 🚨")
    st.error("⏳ Máy chủ cơ sở dữ liệu (Neon) đang ngủ đông hoặc đứt kết nối mạng.")
    st.warning("👉 Hệ thống tự động vô hiệu hóa mọi chức năng để bảo vệ dữ liệu. Vui lòng ấn F5 (Tải lại trang) cho đến khi thông báo này biến mất.")
    st.stop()

# ==========================================
# TIỆN ÍCH XUẤT PDF & ẢNH
# ==========================================
def remove_accents(input_str):
    s = str(input_str).replace('Đ', 'D').replace('đ', 'd')
    nfkd_form = unicodedata.normalize('NFKD', s)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)])

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
    for drop_col in ["Ráp khuôn hoàn chỉnh", "Mã khuôn"]:
        if drop_col in df_export.columns:
            df_export = df_export.drop(columns=[drop_col])

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
    except Exception:
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
    except Exception:
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
    pdf.multi_cell(0, 8, txt=txt("\n".join(clean_title_lines).upper()), align='C')

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
    elif dvgc_text:
        pdf.set_x(10)
        pdf.multi_cell(0, 6, txt=txt(dvgc_text), align='L')

    pdf.set_x(10)
    pdf.set_font(font_name, '', 10)
    pdf.cell(0, 8, txt=txt(f"Ngày lập: {datetime.now().strftime('%d/%m/%Y')}"), ln=True, align='C')
    pdf.ln(5)

    if not df_export.empty:
        pdf.set_font(font_name, '', 8)
        num_cols = [
            "Số lượng", "Đơn giá", "Cắt dây", "Xung điện (EDM)", "Phay CNC", "Nhiệt Luyện",
            "Đánh bóng", "Tạo Nhám hoa văn", "Dọn phôi", "Tổng tiền",
            "Tổng Nguyên Vật Liệu (A)", "Tổng Gia Công (B)", "Tổng Vật Tư (C)",
            "TỔNG CỘNG", "Tổng giá trị khuôn", "Tổng giá gia công", "Cọc đợt 1", "Còn nợ"
        ]

        col_widths = []
        for col in df_export.columns:
            max_w = pdf.get_string_width(txt(col)) + 4
            for item in df_export[col]:
                val_str = str(item) if pd.notnull(item) else ""
                if col in num_cols and val_str.strip() != "":
                    try:
                        val_str = f"{float(item):,.0f}".replace(",", ".")
                    except Exception:
                        pass
                for para in val_str.split('\n'):
                    item_w = pdf.get_string_width(txt(para)) + 4
                    if item_w > max_w:
                        max_w = item_w
            if col in ["Các mục gia công", "Tên NVL", "Tên linh kiện", "Quy cách", "Nhà cung cấp NVL", "Khách hàng"]:
                max_w = min(max_w, 45)
            else:
                max_w = min(max_w, 50)
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
                    for w in para.split(' '):
                        ww = pdf.get_string_width(w + ' ')
                        if curr_w + ww > cw - 2:
                            lines += 1
                            curr_w = ww
                        else:
                            curr_w += ww
                if lines > max_lines:
                    max_lines = lines

            row_height = max_lines * line_h
            if pdf.get_y() + row_height > 270:
                pdf.add_page()
            start_y = pdf.get_y()
            pdf.set_x(10)
            for i, val in enumerate(row_data):
                start_x = pdf.get_x()
                align_col = 'C' if is_header else ('R' if df_export.columns[i] in num_cols else 'L')
                if is_footer and i == len(df_export.columns) - 2:
                    align_col = 'R'
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
        draw_row([txt(col) for col in df_export.columns], is_header=True)

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
                    except Exception:
                        pass
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
            valid_gc = [str(g).strip() for g in ghi_chu_data if pd.notnull(g) and str(g).strip() not in ("", "None")]
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

    temp_filename = f"temp_report_{datetime.now().strftime('%H%M%S_%f')}.pdf"
    pdf.output(temp_filename)
    with open(temp_filename, "rb") as f:
        pdf_bytes = f.read()
    if os.path.exists(temp_filename):
        os.remove(temp_filename)
    return pdf_bytes

# ==========================================
# HÀM ĐỌC / GHI DATABASE & TỰ ĐỘNG ĐỒNG BỘ
# ==========================================
@st.cache_data(show_spinner=False, ttl=86400)
def fetch_data_from_db(table_name):
    try:
        return conn.query(f"SELECT * FROM {table_name}", ttl=0)
    except Exception:
        return None

def force_reload_cache():
    fetch_data_from_db.clear()

def load_data(table_name, columns):
    df = fetch_data_from_db(table_name)
    if df is None:
        st.session_state["db_load_success"] = False
        st.error(f"⏳ Máy chủ Neon chưa sẵn sàng. Mất kết nối khi tải dữ liệu bảng '{table_name}'.")
        return pd.DataFrame(columns=columns)
    if df.empty:
        return pd.DataFrame(columns=columns)
    for col in columns:
        if col not in df.columns:
            df[col] = None
    return df

def append_data(new_row_dict, table_name, df_current):
    if not st.session_state.get("db_load_success", False):
        st.error("🚨 LỆNH BỊ CHẶN: Database đang mất kết nối. Vui lòng ấn F5.")
        st.stop()
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
    if not st.session_state.get("db_load_success", False):
        st.error("🚨 LỆNH BỊ CHẶN: Dữ liệu gốc chưa tải xong. Vui lòng ấn F5.")
        st.stop()
    try:
        try:
            with conn.session as session:
                session.execute(text(f"TRUNCATE TABLE {table_name}"))
                session.commit()
            if not df.empty:
                df.to_sql(table_name, con=conn.engine, if_exists='append', index=False, method='multi')
        except Exception:
            df.to_sql(table_name, con=conn.engine, if_exists='replace', index=False, method='multi')
        force_reload_cache()
    except Exception as e:
        st.error(f"⚠️ Lỗi khi lưu dữ liệu ({table_name}): {str(e)}")

def safe_num_sum(df, ma_khuon, col="Tổng tiền"):
    if df.empty or "Mã khuôn" not in df.columns or col not in df.columns:
        return 0.0
    sub = df[df["Mã khuôn"] == ma_khuon]
    if sub.empty:
        return 0.0
    return float(pd.to_numeric(sub[col], errors='coerce').fillna(0).sum())

def auto_sync_mold_to_D(ma_khuon, df_a, df_b, df_c, df_d):
    """Tự động tính lại tổng chi phí A+B+C cho 1 mã khuôn và lưu vào bảng wanchi_d"""
    if not ma_khuon:
        return
    sum_a = safe_num_sum(df_a, ma_khuon)
    sum_b = safe_num_sum(df_b, ma_khuon)
    sum_c = safe_num_sum(df_c, ma_khuon)
    total = sum_a + sum_b + sum_c

    df_d_copy = df_d.copy()
    today_str = datetime.today().strftime('%d/%m/%Y')

    if not df_d_copy.empty and ma_khuon in df_d_copy["Mã khuôn"].values:
        idx = df_d_copy.index[df_d_copy["Mã khuôn"] == ma_khuon].tolist()[0]
        df_d_copy.at[idx, "Tổng Nguyên Vật Liệu (A)"] = sum_a
        df_d_copy.at[idx, "Tổng Gia Công (B)"] = sum_b
        df_d_copy.at[idx, "Tổng Vật Tư (C)"] = sum_c
        df_d_copy.at[idx, "TỔNG CỘNG"] = total
        save_data(df_d_copy, "wanchi_d")
    else:
        new_row = {
            "Ngày": today_str,
            "Mã khuôn": ma_khuon,
            "Tổng Nguyên Vật Liệu (A)": sum_a,
            "Tổng Gia Công (B)": sum_b,
            "Tổng Vật Tư (C)": sum_c,
            "TỔNG CỘNG": total
        }
        append_data(new_row, "wanchi_d", df_d_copy)

def sync_all_molds_to_D(list_molds, df_a, df_b, df_c, df_d):
    """Đồng bộ toàn bộ mã khuôn vào bảng wanchi_d"""
    rows = []
    today_str = datetime.today().strftime('%d/%m/%Y')
    for mk in list_molds:
        ngay_cu = today_str
        if not df_d.empty and mk in df_d["Mã khuôn"].values:
            val = df_d.loc[df_d["Mã khuôn"] == mk, "Ngày"].values[0]
            if pd.notnull(val) and str(val).strip():
                ngay_cu = str(val)
        sum_a = safe_num_sum(df_a, mk)
        sum_b = safe_num_sum(df_b, mk)
        sum_c = safe_num_sum(df_c, mk)
        rows.append({
            "Ngày": ngay_cu,
            "Mã khuôn": mk,
            "Tổng Nguyên Vật Liệu (A)": sum_a,
            "Tổng Gia Công (B)": sum_b,
            "Tổng Vật Tư (C)": sum_c,
            "TỔNG CỘNG": sum_a + sum_b + sum_c
        })
    save_data(pd.DataFrame(rows), "wanchi_d")

def merge_filtered_edits(df_full, edited_filtered, filter_mold):
    """Gộp dữ liệu sau khi sửa ở chế độ lọc để KHÔNG làm mất dữ liệu của các khuôn khác"""
    clean_edited = edited_filtered.drop(columns=["Chọn"], errors="ignore").copy()
    if filter_mold == "Tất cả":
        return clean_edited
    if "Mã khuôn" in clean_edited.columns:
        clean_edited["Mã khuôn"] = clean_edited["Mã khuôn"].fillna(filter_mold)
        clean_edited.loc[clean_edited["Mã khuôn"].astype(str).str.strip() == "", "Mã khuôn"] = filter_mold
    df_others = df_full[df_full["Mã khuôn"] != filter_mold].copy()
    return pd.concat([df_others, clean_edited], ignore_index=True)

def render_export_image_bar(edited_df, title, file_prefix, state_key, df_a_ref, include_vendor=False):
    """Thanh xuất ảnh báo cáo gọn gàng dùng chung"""
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🖼️ Tạo ảnh báo cáo (Các dòng đã tick)", use_container_width=True, key=f"btn_{state_key}"):
            selected = edited_df[edited_df["Chọn"] == True]
            if selected.empty:
                st.warning("⚠️ Vui lòng tick chọn ít nhất 1 dòng ở cột 'Chọn' để xuất ảnh!")
            else:
                with st.spinner("Đang tạo ảnh báo cáo..."):
                    unique_molds = selected["Mã khuôn"].dropna().unique().tolist() if "Mã khuôn" in selected.columns else []
                    mold_str = unique_molds[0] if len(unique_molds) == 1 else "NHIỀU MÃ KHUÔN"

                    dvgc_str = None
                    if include_vendor and "Đơn vị gia công" in selected.columns:
                        unique_v = selected["Đơn vị gia công"].dropna().unique().tolist()
                        dvgc_str = unique_v[0] if len(unique_v) == 1 else None

                    kh_str = None
                    if mold_str != "NHIỀU MÃ KHUÔN" and not df_a_ref.empty:
                        try:
                            row_kh = df_a_ref[(df_a_ref["Mã khuôn"] == mold_str) & (df_a_ref["Tên NVL"] == "Khởi tạo khuôn")]
                            if not row_kh.empty:
                                kh_raw = str(row_kh.iloc[0]["Nhà cung cấp NVL"])
                                kh_str = kh_raw[4:] if kh_raw.startswith("KH: ") else kh_raw.strip()
                        except Exception:
                            pass

                    pdf_bytes = export_pdf(
                        selected.drop(columns=["Chọn"], errors="ignore"),
                        title=title,
                        ma_khuon_str=mold_str if mold_str != "NHIỀU MÃ KHUÔN" else None,
                        khach_hang_str=kh_str,
                        dvgc_str=dvgc_str
                    )
                    st.session_state[f"img_{state_key}"] = convert_pdf_to_png(pdf_bytes)
                    safe_suffix = f"{mold_str}_{dvgc_str}" if dvgc_str else mold_str
                    st.session_state[f"fname_{state_key}"] = f"WANCHI_{file_prefix}_{safe_suffix}.png"

    with col2:
        if st.session_state.get(f"img_{state_key}"):
            st.download_button(
                "⬇️ Tải ẢNH Xuống",
                st.session_state[f"img_{state_key}"],
                st.session_state.get(f"fname_{state_key}", f"WANCHI_{file_prefix}.png"),
                "image/png",
                type="primary",
                use_container_width=True,
                key=f"dl_{state_key}"
            )

def partner_selector(label, partner_list, key_prefix):
    """Chọn đối tác từ danh mục hoặc cho phép gõ mới linh hoạt"""
    options = ["-- Chọn từ danh mục --"] + partner_list + ["➕ Nhập tên mới..."]
    selected = st.selectbox(label, options, key=f"{key_prefix}_sel")
    if selected == "➕ Nhập tên mới...":
        return st.text_input(f"Gõ tên {label.lower()} mới:", key=f"{key_prefix}_txt").strip()
    elif selected == "-- Chọn từ danh mục --":
        return ""
    return selected

# ==========================================
# TẢI DỮ LIỆU TỪ DATABASE
# ==========================================
cols_A = ["Ngày", "Nhà cung cấp NVL", "Mã khuôn", "Tên NVL", "Quy cách", "Số lượng", "Đơn giá", "Tổng tiền"]
df_A = load_data("wanchi_a", cols_A)
df_A = df_A.loc[:, ~df_A.columns.duplicated()]

cols_B = [
    "Ngày", "Đơn vị gia công", "Mã khuôn", "Cắt dây", "Xung điện (EDM)", "Phay CNC",
    "Nhiệt Luyện", "Đánh bóng", "Tạo Nhám hoa văn", "Dọn phôi", "Ráp khuôn hoàn chỉnh", "Tổng tiền"
]
df_B = load_data("wanchi_b", cols_B)
for old_col in ["Đơn giá", "Cụm khuôn hoàn chỉnh", "Ráp khuôn hoàn thiện"]:
    if old_col in df_B.columns:
        df_B.rename(columns={old_col: "Ráp khuôn hoàn chỉnh"}, inplace=True)
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

cols_Doitac = ["Phân loại", "Tên đối tác"]
df_Doitac = load_data("wanchi_doitac", cols_Doitac)
df_Doitac = df_Doitac.loc[:, ~df_Doitac.columns.duplicated()]

# Danh sách Master Khuôn & Đối tác
all_molds_set = set()
for df_tmp in [df_A, df_B, df_C, df_D, df_F]:
    if not df_tmp.empty and "Mã khuôn" in df_tmp.columns:
        all_molds_set.update([str(x).strip() for x in df_tmp["Mã khuôn"].dropna().unique() if str(x).strip()])
list_molds_master = sorted(list(all_molds_set))

list_ncc = sorted(list(set(
    (df_Doitac[df_Doitac["Phân loại"] == "Nhà cung cấp (NCC)"]["Tên đối tác"].dropna().tolist() if not df_Doitac.empty else []) +
    (df_A["Nhà cung cấp NVL"].dropna().tolist() if not df_A.empty else []) +
    (df_C["Nhà cung cấp vật tư"].dropna().tolist() if not df_C.empty else [])
)))
list_ncc = [x for x in list_ncc if str(x).strip() and not str(x).startswith("KH: ")]

list_ngc = sorted(list(set(
    (df_Doitac[df_Doitac["Phân loại"] == "Nhà gia công (NGC)"]["Tên đối tác"].dropna().tolist() if not df_Doitac.empty else []) +
    (df_B["Đơn vị gia công"].dropna().tolist() if not df_B.empty else []) +
    (df_F["Đơn vị gia công"].dropna().tolist() if not df_F.empty else [])
)))
list_ngc = [x for x in list_ngc if str(x).strip()]

# ==========================================
# THANH ĐIỀU HƯỚNG CHÍNH (4 KHU VỰC LOGIC)
# ==========================================
st.title("🏭 Quản Lý Khuôn Mẫu WANCHI")

nav_items = [
    "📊 1. Tổng Quan & Hồ Sơ",
    "💰 2. Nhập Chi Phí (A-B-C)",
    "📋 3. Đơn Hàng Gia Công",
    "⚙️ 4. Danh Mục"
]

if "main_nav" not in st.session_state or st.session_state.main_nav not in nav_items:
    st.session_state.main_nav = nav_items[0]

nav_cols = st.columns(4)
for idx, item in enumerate(nav_items):
    btn_type = "primary" if st.session_state.main_nav == item else "secondary"
    if nav_cols[idx].button(item, use_container_width=True, type=btn_type):
        st.session_state.main_nav = item
        st.rerun()

st.markdown("---")

# ==============================================================================
# KHU VỰC 1: TỔNG QUAN, TẠO KHUÔN MỚI & BẢNG TỔNG GIÁ (D)
# ==============================================================================
if st.session_state.main_nav == nav_items[0]:
    # 1. KPI toàn xưởng
    tong_a_all = pd.to_numeric(df_A["Tổng tiền"], errors='coerce').fillna(0).sum() if not df_A.empty else 0
    tong_b_all = pd.to_numeric(df_B["Tổng tiền"], errors='coerce').fillna(0).sum() if not df_B.empty else 0
    tong_c_all = pd.to_numeric(df_C["Tổng tiền"], errors='coerce').fillna(0).sum() if not df_C.empty else 0
    tong_all = tong_a_all + tong_b_all + tong_c_all

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("📦 Tổng Số Khuôn", f"{len(list_molds_master)} khuôn")
    k2.metric("🧱 Tổng NVL (A)", f"{tong_a_all:,.0f} đ")
    k3.metric("⚙️ Tổng Gia Công (B)", f"{tong_b_all:,.0f} đ")
    k4.metric("💵 Tổng Giá Trị (A+B+C)", f"{tong_all:,.0f} đ")

    # 2. Form tạo khuôn mới gọn gàng
    with st.expander("➕ Khởi Tạo Dự Án Khuôn Mới", expanded=(len(list_molds_master) == 0)):
        with st.form("form_tao_khuon_moi", clear_on_submit=True):
            c1, c2 = st.columns([1, 2])
            ngay_tao = c1.date_input("Ngày Khởi Tạo", datetime.today())
            ma_khuon_moi = c2.text_input("Mã Khuôn Mới (*)", placeholder="VD: KHUON_ABC_01")
            if st.form_submit_button("🚀 Tạo Khuôn Mới", type="primary", use_container_width=True):
                mk_clean = ma_khuon_moi.strip().upper()
                if not mk_clean:
                    st.error("⚠️ Vui lòng nhập Mã Khuôn!")
                elif mk_clean in list_molds_master:
                    st.error(f"⚠️ Mã khuôn **{mk_clean}** đã tồn tại!")
                else:
                    with st.spinner("Đang khởi tạo..."):
                        row_d = {
                            "Ngày": ngay_tao.strftime('%d/%m/%Y'),
                            "Mã khuôn": mk_clean,
                            "Tổng Nguyên Vật Liệu (A)": 0,
                            "Tổng Gia Công (B)": 0,
                            "Tổng Vật Tư (C)": 0,
                            "TỔNG CỘNG": 0
                        }
                        append_data(row_d, "wanchi_d", df_D)
                    st.success(f"🎉 Đã tạo khuôn **{mk_clean}** thành công!")
                    time.sleep(1)
                    st.rerun()

    st.markdown("---")

    # 3. Xem nhanh hồ sơ 1 khuôn
    st.subheader("🔎 Tra Cứu Nhanh Theo Mã Khuôn")
    if list_molds_master:
        sel_profile = st.selectbox("Chọn mã khuôn cần xem hồ sơ chi tiết:", ["-- Chọn khuôn --"] + list_molds_master)
        if sel_profile != "-- Chọn khuôn --":
            sa = safe_num_sum(df_A, sel_profile)
            sb = safe_num_sum(df_B, sel_profile)
            sc = safe_num_sum(df_C, sel_profile)
            p1, p2, p3, p4 = st.columns(4)
            p1.metric("NVL (A)", f"{sa:,.0f} đ")
            p2.metric("Gia Công (B)", f"{sb:,.0f} đ")
            p3.metric("Vật Tư (C)", f"{sc:,.0f} đ")
            p4.metric("TỔNG CỘNG", f"{(sa + sb + sc):,.0f} đ")

            t_a, t_b, t_c, t_f = st.tabs(["🧱 Chi tiết NVL", "⚙️ Chi tiết Gia Công", "🔩 Chi tiết Vật Tư", "📋 Đơn Gia Công"])
            with t_a:
                sub = df_A[df_A["Mã khuôn"] == sel_profile]
                st.dataframe(sub, use_container_width=True, hide_index=True) if not sub.empty else st.info("Chưa có dữ liệu NVL.")
            with t_b:
                sub = df_B[df_B["Mã khuôn"] == sel_profile]
                st.dataframe(sub, use_container_width=True, hide_index=True) if not sub.empty else st.info("Chưa có dữ liệu Gia công.")
            with t_c:
                sub = df_C[df_C["Mã khuôn"] == sel_profile]
                st.dataframe(sub, use_container_width=True, hide_index=True) if not sub.empty else st.info("Chưa có dữ liệu Vật tư.")
            with t_f:
                sub = df_F[df_F["Mã khuôn"] == sel_profile]
                st.dataframe(sub, use_container_width=True, hide_index=True) if not sub.empty else st.info("Chưa có đơn hàng gia công.")
    else:
        st.info("Chưa có mã khuôn nào. Hãy bấm 'Khởi Tạo Dự Án Khuôn Mới' ở trên.")

    st.markdown("---")

    # 4. Bảng Tổng Hợp Giá Trị Khuôn (D)
    col_h1, col_h2 = st.columns([3, 1])
    col_h1.subheader("📑 Bảng Tổng Hợp Giá Trị Khuôn (D)")
    if col_h2.button("🔄 Đồng bộ toàn bộ số liệu", use_container_width=True, help="Quét lại toàn bộ A, B, C để cập nhật chính xác vào bảng D"):
        with st.spinner("Đang đồng bộ..."):
            sync_all_molds_to_D(list_molds_master, df_A, df_B, df_C, df_D)
        st.success("✅ Đã đồng bộ xong toàn bộ bảng D!")
        time.sleep(1)
        st.rerun()

    df_D_disp = df_D.copy()
    df_D_disp.insert(0, "Chọn", False)
    edited_D = st.data_editor(df_D_disp, num_rows="dynamic", use_container_width=True, hide_index=True, key="edit_D")
    edited_D["Chọn"] = edited_D["Chọn"].fillna(False).astype(bool)

    if st.button("💾 Lưu Chỉnh Sửa Bảng Tổng (D)", type="primary", use_container_width=True):
        with st.spinner("Đang lưu..."):
            save_data(edited_D.drop(columns=["Chọn"]), "wanchi_d")
        st.success("✅ Đã lưu thành công!")
        time.sleep(1)
        st.rerun()

    render_export_image_bar(edited_D, "BẢNG TỔNG HỢP CHI PHÍ", "TongHop", "tab_d", df_A)

# ==============================================================================
# KHU VỰC 2: QUẢN LÝ CHI PHÍ (A: NVL, B: GIA CÔNG, C: VẬT TƯ)
# ==============================================================================
elif st.session_state.main_nav == nav_items[1]:
    # Bộ lọc Mã khuôn dùng chung cho cả 3 tab A, B, C
    f_col1, f_col2 = st.columns([2, 3])
    filter_mold = f_col1.selectbox(
        "🎯 Lọc & Chọn nhanh Mã Khuôn đang thao tác:",
        ["Tất cả"] + list_molds_master,
        help="Chọn 1 mã khuôn để lọc bảng bên dưới và tự động điền sẵn vào form nhập liệu."
    )
    default_mold_idx = list_molds_master.index(filter_mold) if filter_mold in list_molds_master else 0

    if filter_mold != "Tất cả":
        sa = safe_num_sum(df_A, filter_mold)
        sb = safe_num_sum(df_B, filter_mold)
        sc = safe_num_sum(df_C, filter_mold)
        f_col2.info(f"**{filter_mold}** — NVL: `{sa:,.0f}` | Gia công: `{sb:,.0f}` | Vật tư: `{sc:,.0f}` | **Tổng: `{(sa+sb+sc):,.0f} đ`**")

    tab_A, tab_B, tab_C = st.tabs(["🧱 A. Nguyên Vật Liệu", "⚙️ B. Chi Phí Gia Công", "🔩 C. Vật Tư Khuôn Mẫu"])

    # ---------------- TAB A: NGUYÊN VẬT LIỆU ----------------
    with tab_A:
        with st.expander("➕ Nhập Nguyên Vật Liệu Mới", expanded=False):
            c1, c2, c3, c4 = st.columns(4)
            ngay_a = c1.date_input("Ngày", datetime.today(), key="ngay_a")
            ma_khuon_a = c2.selectbox("Mã khuôn", list_molds_master, index=default_mold_idx, key="mk_a") if list_molds_master else c2.text_input("Mã khuôn", key="mk_a_txt")
            with c3:
                ncc_a = partner_selector("Nhà cung cấp NVL", list_ncc, "ncc_a")
            ten_nvl = c4.text_input("Tên NVL", placeholder="VD: Thép P20, S50C...", key="ten_nvl")

            c5, c6, c7, c8 = st.columns(4)
            quy_cach = c5.text_input("Quy cách", placeholder="VD: 200x300x50", key="qc_a")
            sl_a = c6.number_input("Số lượng (kg / tấm)", min_value=0.0, step=1.0, key="sl_a")
            don_gia_a = c7.number_input("Đơn giá (VNĐ)", min_value=0, step=1000, key="dg_a")
            auto_total_a = int(round(sl_a * don_gia_a))
            override_a = c8.number_input(
                f"Tổng tiền (Tự tính: {auto_total_a:,.0f})",
                min_value=0, step=1000, value=0,
                help="Để 0 sẽ tự lấy Số lượng × Đơn giá. Chỉ nhập nếu muốn ghi đè số tiền khác.",
                key="ovr_a"
            )
            final_total_a = override_a if override_a > 0 else auto_total_a

            if st.button("💾 Lưu Nguyên Vật Liệu", type="primary", use_container_width=True, key="save_new_a"):
                if not ma_khuon_a or not ten_nvl.strip():
                    st.error("⚠️ Vui lòng chọn Mã khuôn và nhập Tên NVL!")
                else:
                    with st.spinner("Đang lưu và cập nhật bảng tổng..."):
                        mk_up = ma_khuon_a.strip().upper()
                        new_row = {
                            "Ngày": ngay_a.strftime('%d/%m/%Y'),
                            "Nhà cung cấp NVL": ncc_a,
                            "Mã khuôn": mk_up,
                            "Tên NVL": ten_nvl.strip(),
                            "Quy cách": quy_cach.strip(),
                            "Số lượng": sl_a,
                            "Đơn giá": don_gia_a,
                            "Tổng tiền": final_total_a
                        }
                        append_data(new_row, "wanchi_a", df_A)
                        df_A_new = pd.concat([df_A, pd.DataFrame([new_row])], ignore_index=True)
                        auto_sync_mold_to_D(mk_up, df_A_new, df_B, df_C, df_D)
                    st.success(f"✅ Đã lưu NVL ({final_total_a:,.0f} đ) và tự động cập nhật Bảng Tổng!")
                    time.sleep(1)
                    st.rerun()

        df_A_view = df_A[df_A["Mã khuôn"] == filter_mold].copy() if filter_mold != "Tất cả" else df_A.copy()
        df_A_view.insert(0, "Chọn", False)
        edited_A = st.data_editor(df_A_view, num_rows="dynamic", use_container_width=True, hide_index=True, key="edit_A")
        edited_A["Chọn"] = edited_A["Chọn"].fillna(False).astype(bool)

        if st.button("💾 Cập Nhật Bảng Nguyên Vật Liệu", type="primary", use_container_width=True, key="upd_a"):
            with st.spinner("Đang cập nhật..."):
                merged_A = merge_filtered_edits(df_A, edited_A, filter_mold)
                save_data(merged_A, "wanchi_a")
                if filter_mold != "Tất cả":
                    auto_sync_mold_to_D(filter_mold, merged_A, df_B, df_C, df_D)
                else:
                    sync_all_molds_to_D(list_molds_master, merged_A, df_B, df_C, df_D)
            st.success("✅ Đã cập nhật NVL và đồng bộ Bảng Tổng!")
            time.sleep(1)
            st.rerun()

        render_export_image_bar(edited_A, "BÁO CÁO NGUYÊN VẬT LIỆU", "NVL", "tab_a", df_A)

    # ---------------- TAB B: GIA CÔNG ----------------
    with tab_B:
        with st.expander("➕ Nhập Chi Phí Gia Công Mới", expanded=False):
            c1, c2, c3 = st.columns(3)
            ngay_b = c1.date_input("Ngày", datetime.today(), key="ngay_b")
            ma_khuon_b = c2.selectbox("Mã khuôn", list_molds_master, index=default_mold_idx, key="mk_b") if list_molds_master else c2.text_input("Mã khuôn", key="mk_b_txt")
            with c3:
                ncc_b = partner_selector("Đơn vị gia công", list_ngc, "ngc_b")

            st.caption("Nhập chi phí cho từng công đoạn phát sinh (để 0 nếu không làm):")
            g1, g2, g3, g4 = st.columns(4)
            cat_day = g1.number_input("Cắt dây", min_value=0, step=10000, key="b_cd")
            xung_dien = g2.number_input("Xung điện (EDM)", min_value=0, step=10000, key="b_edm")
            phay_cnc = g3.number_input("Phay CNC", min_value=0, step=10000, key="b_cnc")
            nhiet_luyen = g4.number_input("Nhiệt Luyện", min_value=0, step=10000, key="b_nl")

            g5, g6, g7, g8 = st.columns(4)
            danh_bong = g5.number_input("Đánh bóng", min_value=0, step=10000, key="b_db")
            nham = g6.number_input("Tạo Nhám hoa văn", min_value=0, step=10000, key="b_nham")
            don_phoi = g7.number_input("Dọn phôi", min_value=0, step=10000, key="b_dp")
            rap_khuon = g8.number_input("Ráp khuôn hoàn chỉnh", min_value=0, step=10000, key="b_rk")

            auto_total_b = cat_day + xung_dien + phay_cnc + nhiet_luyen + danh_bong + nham + don_phoi + rap_khuon
            st.markdown("---")
            tc1, tc2 = st.columns([2, 1])
            tc1.info(f"🧮 **Tổng tự cộng 8 công đoạn:** `{auto_total_b:,.0f} đ`")
            override_b = tc2.number_input("Ghi đè Tổng tiền (để 0 = lấy tự cộng)", min_value=0, step=10000, value=0, key="ovr_b")
            final_total_b = override_b if override_b > 0 else auto_total_b

            if st.button("💾 Lưu Chi Phí Gia Công", type="primary", use_container_width=True, key="save_new_b"):
                if not ma_khuon_b:
                    st.error("⚠️ Vui lòng chọn Mã khuôn!")
                elif final_total_b <= 0:
                    st.error("⚠️ Vui lòng nhập ít nhất 1 chi phí công đoạn!")
                else:
                    with st.spinner("Đang lưu và cập nhật bảng tổng..."):
                        mk_up = ma_khuon_b.strip().upper()
                        new_row_b = {
                            "Ngày": ngay_b.strftime('%d/%m/%Y'),
                            "Đơn vị gia công": ncc_b,
                            "Mã khuôn": mk_up,
                            "Cắt dây": cat_day,
                            "Xung điện (EDM)": xung_dien,
                            "Phay CNC": phay_cnc,
                            "Nhiệt Luyện": nhiet_luyen,
                            "Đánh bóng": danh_bong,
                            "Tạo Nhám hoa văn": nham,
                            "Dọn phôi": don_phoi,
                            "Ráp khuôn hoàn chỉnh": rap_khuon,
                            "Tổng tiền": final_total_b
                        }
                        append_data(new_row_b, "wanchi_b", df_B)
                        df_B_new = pd.concat([df_B, pd.DataFrame([new_row_b])], ignore_index=True)
                        auto_sync_mold_to_D(mk_up, df_A, df_B_new, df_C, df_D)
                    st.success(f"✅ Đã lưu Gia công ({final_total_b:,.0f} đ) và tự động cập nhật Bảng Tổng!")
                    time.sleep(1)
                    st.rerun()

        df_B_view = df_B[df_B["Mã khuôn"] == filter_mold].copy() if filter_mold != "Tất cả" else df_B.copy()
        df_B_view.insert(0, "Chọn", False)
        edited_B = st.data_editor(df_B_view, num_rows="dynamic", use_container_width=True, hide_index=True, key="edit_B")
        edited_B["Chọn"] = edited_B["Chọn"].fillna(False).astype(bool)

        if st.button("💾 Cập Nhật Bảng Gia Công", type="primary", use_container_width=True, key="upd_b"):
            with st.spinner("Đang cập nhật..."):
                merged_B = merge_filtered_edits(df_B, edited_B, filter_mold)
                save_data(merged_B, "wanchi_b")
                if filter_mold != "Tất cả":
                    auto_sync_mold_to_D(filter_mold, df_A, merged_B, df_C, df_D)
                else:
                    sync_all_molds_to_D(list_molds_master, df_A, merged_B, df_C, df_D)
            st.success("✅ Đã cập nhật Gia công và đồng bộ Bảng Tổng!")
            time.sleep(1)
            st.rerun()

        render_export_image_bar(edited_B, "BÁO CÁO CHI PHÍ GIA CÔNG", "GiaCong", "tab_b", df_A)

    # ---------------- TAB C: VẬT TƯ ----------------
    with tab_C:
        with st.expander("➕ Nhập Vật Tư Khuôn Mẫu Mới", expanded=False):
            c1, c2, c3 = st.columns(3)
            ngay_c = c1.date_input("Ngày", datetime.today(), key="ngay_c")
            ma_khuon_c = c2.selectbox("Mã khuôn", list_molds_master, index=default_mold_idx, key="mk_c") if list_molds_master else c2.text_input("Mã khuôn", key="mk_c_txt")
            with c3:
                ncc_c = partner_selector("Nhà cung cấp vật tư", list_ncc, "ncc_c")

            c4, c5, c6, c7 = st.columns([2, 1, 1, 1])
            ten_lk = c4.text_input("Tên linh kiện", placeholder="VD: Ty đẩy, Lò xo, Bạc dẫn hướng...", key="ten_lk")
            sl_c = c5.number_input("SL (tính nhẩm)", min_value=1, step=1, value=1, key="sl_c")
            don_gia_c = c6.number_input("Đơn giá (VNĐ)", min_value=0, step=1000, key="dg_c")
            auto_total_c = sl_c * don_gia_c
            override_c = c7.number_input(
                f"Tổng tiền ({auto_total_c:,.0f})",
                min_value=0, step=1000, value=0,
                help="Để 0 sẽ tự lấy SL × Đơn giá.",
                key="ovr_c"
            )
            final_total_c = override_c if override_c > 0 else auto_total_c

            if st.button("💾 Lưu Vật Tư", type="primary", use_container_width=True, key="save_new_c"):
                if not ma_khuon_c or not ten_lk.strip():
                    st.error("⚠️ Vui lòng chọn Mã khuôn và nhập Tên linh kiện!")
                else:
                    with st.spinner("Đang lưu và cập nhật bảng tổng..."):
                        mk_up = ma_khuon_c.strip().upper()
                        ten_lk_save = f"{ten_lk.strip()} (x{sl_c})" if sl_c > 1 else ten_lk.strip()
                        new_row_c = {
                            "Ngày": ngay_c.strftime('%d/%m/%Y'),
                            "Nhà cung cấp vật tư": ncc_c,
                            "Mã khuôn": mk_up,
                            "Tên linh kiện": ten_lk_save,
                            "Đơn giá": don_gia_c,
                            "Tổng tiền": final_total_c
                        }
                        append_data(new_row_c, "wanchi_c", df_C)
                        df_C_new = pd.concat([df_C, pd.DataFrame([new_row_c])], ignore_index=True)
                        auto_sync_mold_to_D(mk_up, df_A, df_B, df_C_new, df_D)
                    st.success(f"✅ Đã lưu Vật tư ({final_total_c:,.0f} đ) và tự động cập nhật Bảng Tổng!")
                    time.sleep(1)
                    st.rerun()

        df_C_view = df_C[df_C["Mã khuôn"] == filter_mold].copy() if filter_mold != "Tất cả" else df_C.copy()
        df_C_view.insert(0, "Chọn", False)
        edited_C = st.data_editor(df_C_view, num_rows="dynamic", use_container_width=True, hide_index=True, key="edit_C")
        edited_C["Chọn"] = edited_C["Chọn"].fillna(False).astype(bool)

        if st.button("💾 Cập Nhật Bảng Vật Tư", type="primary", use_container_width=True, key="upd_c"):
            with st.spinner("Đang cập nhật..."):
                merged_C = merge_filtered_edits(df_C, edited_C, filter_mold)
                save_data(merged_C, "wanchi_c")
                if filter_mold != "Tất cả":
                    auto_sync_mold_to_D(filter_mold, df_A, df_B, merged_C, df_D)
                else:
                    sync_all_molds_to_D(list_molds_master, df_A, df_B, merged_C, df_D)
            st.success("✅ Đã cập nhật Vật tư và đồng bộ Bảng Tổng!")
            time.sleep(1)
            st.rerun()

        render_export_image_bar(edited_C, "BÁO CÁO VẬT TƯ", "VatTu", "tab_c", df_A)

# ==============================================================================
# KHU VỰC 3: ĐƠN HÀNG GIA CÔNG (GỘP F + G)
# ==============================================================================
elif st.session_state.main_nav == nav_items[2]:
    # KPI công nợ đơn hàng
    tong_gia_dh = pd.to_numeric(df_F["Tổng giá gia công"], errors='coerce').fillna(0).sum() if not df_F.empty else 0
    tong_coc_dh = pd.to_numeric(df_F["Cọc đợt 1"], errors='coerce').fillna(0).sum() if not df_F.empty else 0
    tong_no_dh = pd.to_numeric(df_F["Còn nợ"], errors='coerce').fillna(0).sum() if not df_F.empty else 0

    m1, m2, m3 = st.columns(3)
    m1.metric("📄 Tổng Giá Trị Đơn Hàng", f"{tong_gia_dh:,.0f} đ")
    m2.metric("✅ Đã Đặt Cọc", f"{tong_coc_dh:,.0f} đ")
    m3.metric("⚠️ Tổng Còn Nợ", f"{tong_no_dh:,.0f} đ")

    # Form tạo đơn hàng mới ngay phía trên
    with st.expander("➕ Tạo Đơn Hàng Gia Công Mới", expanded=False):
        c1, c2 = st.columns(2)
        ma_khuon_f = c1.selectbox("Mã khuôn", list_molds_master, key="mk_f") if list_molds_master else c1.text_input("Mã khuôn", key="mk_f_txt")
        with c2:
            dv_f = partner_selector("Đơn vị gia công", list_ngc, "ngc_f")

        danh_sach_hang_muc = [
            "Cắt dây", "Xung điện (EDM)", "Phay CNC", "Nhiệt Luyện",
            "Đánh bóng", "Tạo Nhám hoa văn", "Dọn phôi", "Ráp khuôn hoàn chỉnh"
        ]
        hang_muc = st.multiselect("Các hạng mục cần gia công:", danh_sach_hang_muc, key="hm_f")

        c3, c4 = st.columns(2)
        ngay_nhan = c3.date_input("Thời gian nhận phôi/khuôn", datetime.today(), key="nn_f")
        ngay_giao = c4.date_input("Thời gian bàn giao (Dự kiến)", datetime.today(), key="ng_f")

        c5, c6, c7 = st.columns(3)
        tong_gia_f = c5.number_input("Tổng giá gia công (VNĐ)", min_value=0, step=10000, key="tg_f")
        coc_f = c6.number_input("Cọc đợt 1 (VNĐ)", min_value=0, step=10000, key="coc_f")
        con_no_preview = max(0, tong_gia_f - coc_f)
        c7.metric("Còn nợ (Tự tính)", f"{con_no_preview:,.0f} đ")

        ghi_chu_f = st.text_area("Ghi chú đơn hàng (Tự động kéo giãn khi xuất ảnh)", key="gc_f")

        if st.button("🚀 Tạo Đơn Hàng Mới", type="primary", use_container_width=True, key="btn_create_f"):
            if not ma_khuon_f:
                st.error("⚠️ Vui lòng chọn Mã khuôn!")
            elif not dv_f:
                st.error("⚠️ Vui lòng chọn hoặc nhập tên Đơn vị gia công!")
            elif not hang_muc:
                st.error("⚠️ Vui lòng chọn ít nhất 1 hạng mục gia công!")
            else:
                with st.spinner("Đang tạo đơn hàng..."):
                    new_row_f = {
                        "Mã khuôn": ma_khuon_f.strip().upper(),
                        "Đơn vị gia công": dv_f,
                        "Các mục gia công": ", ".join(hang_muc),
                        "Thời gian nhận": ngay_nhan.strftime('%d/%m/%Y'),
                        "Thời gian bàn giao": ngay_giao.strftime('%d/%m/%Y'),
                        "Tổng giá gia công": tong_gia_f,
                        "Cọc đợt 1": coc_f,
                        "Còn nợ": tong_gia_f - coc_f,
                        "Ghi chú": ghi_chu_f.strip()
                    }
                    append_data(new_row_f, "wanchi_f", df_F)
                st.success("✅ Đã tạo đơn hàng gia công mới!")
                time.sleep(1)
                st.rerun()

    st.markdown("---")
    st.subheader("📋 Danh Sách & Theo Dõi Công Nợ Đơn Hàng")

    # Bộ lọc đơn hàng
    fc1, fc2 = st.columns(2)
    f_mold_dh = fc1.selectbox("Lọc theo Mã khuôn:", ["Tất cả"] + list_molds_master, key="filter_dh_mold")
    f_ngc_dh = fc2.selectbox("Lọc theo Đơn vị gia công:", ["Tất cả"] + list_ngc, key="filter_dh_ngc")

    df_F_view = df_F.copy()
    if f_mold_dh != "Tất cả":
        df_F_view = df_F_view[df_F_view["Mã khuôn"] == f_mold_dh]
    if f_ngc_dh != "Tất cả":
        df_F_view = df_F_view[df_F_view["Đơn vị gia công"] == f_ngc_dh]

    df_F_view.insert(0, "Chọn", False)
    edited_F = st.data_editor(df_F_view, num_rows="dynamic", use_container_width=True, hide_index=True, key="edit_F")
    edited_F["Chọn"] = edited_F["Chọn"].fillna(False).astype(bool)

    is_filtered_F = (f_mold_dh != "Tất cả" or f_ngc_dh != "Tất cả")
    if is_filtered_F:
        st.caption("💡 Đang bật bộ lọc. Bỏ lọc về 'Tất cả' nếu muốn chỉnh sửa và lưu trực tiếp trên bảng.")

    if st.button("💾 Cập Nhật Đơn Hàng (Tự tính lại Còn nợ)", type="primary", use_container_width=True, disabled=is_filtered_F):
        with st.spinner("Đang cập nhật..."):
            df_save_f = edited_F.drop(columns=["Chọn"]).copy()
            tg_col = pd.to_numeric(df_save_f["Tổng giá gia công"], errors='coerce').fillna(0)
            coc_col = pd.to_numeric(df_save_f["Cọc đợt 1"], errors='coerce').fillna(0)
            df_save_f["Còn nợ"] = tg_col - coc_col
            save_data(df_save_f, "wanchi_f")
        st.success("✅ Đã cập nhật đơn hàng và tự tính lại công nợ!")
        time.sleep(1)
        st.rerun()

    render_export_image_bar(edited_F, "ĐƠN HÀNG GIA CÔNG", "DonHang", "tab_f", df_A, include_vendor=True)

# ==============================================================================
# KHU VỰC 4: DANH MỤC HỆ THỐNG (KHUÔN & ĐỐI TÁC)
# ==============================================================================
elif st.session_state.main_nav == nav_items[3]:
    col_k, col_dt = st.columns(2)

    # Cột 1: Danh sách khuôn
    with col_k:
        st.subheader("📦 Danh Sách Khuôn Mẫu")
        search_mk = st.text_input("🔍 Tìm mã khuôn:", placeholder="Gõ ký tự để lọc nhanh...")

        danh_sach_khuon = []
        for mk in list_molds_master:
            if search_mk.strip() and search_mk.strip().upper() not in mk.upper():
                continue
            dates = []
            for df_t in [df_A, df_B, df_C, df_D]:
                if not df_t.empty and "Mã khuôn" in df_t.columns and "Ngày" in df_t.columns:
                    dates.extend(df_t[df_t["Mã khuôn"] == mk]["Ngày"].dropna().tolist())
            parsed = []
            for d in dates:
                try:
                    parsed.append(datetime.strptime(str(d), '%d/%m/%Y'))
                except Exception:
                    pass
            ngay_bd = min(parsed).strftime('%d/%m/%Y') if parsed else ""
            tong_val = safe_num_sum(df_A, mk) + safe_num_sum(df_B, mk) + safe_num_sum(df_C, mk)
            danh_sach_khuon.append({
                "Ngày bắt đầu": ngay_bd,
                "Mã khuôn": mk,
                "Tổng chi phí (VNĐ)": f"{tong_val:,.0f}"
            })

        if danh_sach_khuon:
            st.dataframe(pd.DataFrame(danh_sach_khuon), use_container_width=True, hide_index=True)
        else:
            st.info("Không tìm thấy khuôn phù hợp.")

    # Cột 2: Quản lý đối tác (Thêm + Sửa + Xóa)
    with col_dt:
        st.subheader("🤝 Danh Mục Đối Tác (NCC / NGC)")
        with st.form("form_them_doitac", clear_on_submit=True):
            c_loai, c_ten = st.columns([1, 2])
            loai_dt = c_loai.selectbox("Phân loại", ["Nhà cung cấp (NCC)", "Nhà gia công (NGC)"])
            ten_dt = c_ten.text_input("Tên Đối tác mới")
            if st.form_submit_button("➕ Thêm Đối Tác", type="primary", use_container_width=True):
                if ten_dt.strip():
                    with st.spinner("Đang lưu..."):
                        append_data({"Phân loại": loai_dt, "Tên đối tác": ten_dt.strip()}, "wanchi_doitac", df_Doitac)
                    st.success("✅ Đã thêm đối tác!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.warning("⚠️ Vui lòng nhập tên đối tác!")

        st.caption("Chỉnh sửa hoặc xóa trực tiếp các dòng bên dưới rồi bấm Lưu:")
        edited_dt = st.data_editor(
            df_Doitac,
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            column_config={
                "Phân loại": st.column_config.SelectboxColumn(
                    "Phân loại",
                    options=["Nhà cung cấp (NCC)", "Nhà gia công (NGC)"],
                    required=True
                )
            },
            key="edit_doitac"
        )
        if st.button("💾 Lưu Danh Sách Đối Tác", use_container_width=True):
            with st.spinner("Đang lưu..."):
                save_data(edited_dt.dropna(subset=["Tên đối tác"]), "wanchi_doitac")
            st.success("✅ Đã cập nhật danh sách đối tác!")
            time.sleep(1)
            st.rerun()
