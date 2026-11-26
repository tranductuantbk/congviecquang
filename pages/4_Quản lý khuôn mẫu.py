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
# CSS TỐI ƯU GIAO DIỆN GỌN ĐẸP, CHỐNG CHE CHỮ
# ==========================================
st.markdown("""
<style>
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
        max-width: 1200px;
    }
    div[data-testid="stMetric"] {
        background-color: rgba(128, 128, 128, 0.08);
        border: 1px solid rgba(128, 128, 128, 0.2);
        padding: 12px 16px;
        border-radius: 10px;
    }
    div[data-testid="stMetricLabel"] p {
        font-size: 0.9rem !important;
        white-space: normal !important;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.35rem !important;
    }
    .section-card {
        padding: 14px 18px;
        border-radius: 10px;
        border: 1px solid rgba(128, 128, 128, 0.2);
        background-color: rgba(128, 128, 128, 0.04);
        margin-bottom: 14px;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# KẾT NỐI NEON (POSTGRESQL) & LÍNH GÁC
# ==========================================
try:
    conn = st.connection("postgresql", type="sql")
except Exception:
    st.error("Chưa thể kết nối đến cơ sở dữ liệu. Vui lòng kiểm tra lại file cấu hình Secrets.")
    st.stop()

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
    st.warning("👉 Vui lòng ấn F5 (Tải lại trang) cho đến khi thông báo này biến mất.")
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
        st.error("⚠️ Hệ thống thiếu thư viện 'PyMuPDF' để xuất ảnh. Vui lòng chạy: pip install PyMuPDF")
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
    # Làm sạch tên cột hiển thị khi xuất báo cáo (bỏ chữ A, B, C)
    df_export = df_export.rename(columns={
        "Tổng Nguyên Vật Liệu (A)": "Nguyên Vật Liệu",
        "Tổng Gia Công (B)": "Gia Công",
        "Tổng Vật Tư (C)": "Vật Tư"
    })
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
            "Nguyên Vật Liệu", "Gia Công", "Vật Tư",
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
# HÀM ĐỌC / GHI DATABASE & ĐỒNG BỘ
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
        st.error(f"⏳ Mất kết nối khi tải bảng '{table_name}'.")
        return pd.DataFrame(columns=columns)
    if df.empty:
        return pd.DataFrame(columns=columns)
    for col in columns:
        if col not in df.columns:
            df[col] = None
    return df

def append_data(new_row_dict, table_name, df_current):
    if not st.session_state.get("db_load_success", False):
        st.error("🚨 Database đang mất kết nối. Vui lòng ấn F5.")
        st.stop()
    try:
        pd.DataFrame([new_row_dict]).to_sql(table_name, con=conn.engine, if_exists='append', index=False)
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
        st.error("🚨 Dữ liệu gốc chưa tải xong. Vui lòng ấn F5.")
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
        st.error(f"⚠️ Lỗi lưu dữ liệu ({table_name}): {str(e)}")

def prep_numeric_cols(df, num_cols):
    df_out = df.copy()
    for c in num_cols:
        if c in df_out.columns:
            df_out[c] = pd.to_numeric(df_out[c], errors='coerce').fillna(0)
    return df_out

def safe_num_sum(df, ma_khuon, col="Tổng tiền"):
    if df.empty or "Mã khuôn" not in df.columns or col not in df.columns:
        return 0.0
    sub = df[df["Mã khuôn"] == ma_khuon]
    if sub.empty:
        return 0.0
    return float(pd.to_numeric(sub[col], errors='coerce').fillna(0).sum())

def auto_sync_mold_to_summary(ma_khuon, df_nvl, df_gc, df_vt, df_sum):
    if not ma_khuon:
        return
    sum_nvl = safe_num_sum(df_nvl, ma_khuon)
    sum_gc = safe_num_sum(df_gc, ma_khuon)
    sum_vt = safe_num_sum(df_vt, ma_khuon)
    total = sum_nvl + sum_gc + sum_vt

    df_copy = df_sum.copy()
    today_str = datetime.today().strftime('%d/%m/%Y')
    if not df_copy.empty and ma_khuon in df_copy["Mã khuôn"].values:
        idx = df_copy.index[df_copy["Mã khuôn"] == ma_khuon].tolist()[0]
        df_copy.at[idx, "Tổng Nguyên Vật Liệu (A)"] = sum_nvl
        df_copy.at[idx, "Tổng Gia Công (B)"] = sum_gc
        df_copy.at[idx, "Tổng Vật Tư (C)"] = sum_vt
        df_copy.at[idx, "TỔNG CỘNG"] = total
        save_data(df_copy, "wanchi_d")
    else:
        append_data({
            "Ngày": today_str,
            "Mã khuôn": ma_khuon,
            "Tổng Nguyên Vật Liệu (A)": sum_nvl,
            "Tổng Gia Công (B)": sum_gc,
            "Tổng Vật Tư (C)": sum_vt,
            "TỔNG CỘNG": total
        }, "wanchi_d", df_copy)

def sync_all_molds_to_summary(list_molds, df_nvl, df_gc, df_vt, df_sum):
    rows = []
    today_str = datetime.today().strftime('%d/%m/%Y')
    for mk in list_molds:
        ngay_cu = today_str
        if not df_sum.empty and mk in df_sum["Mã khuôn"].values:
            val = df_sum.loc[df_sum["Mã khuôn"] == mk, "Ngày"].values[0]
            if pd.notnull(val) and str(val).strip():
                ngay_cu = str(val)
        s_nvl = safe_num_sum(df_nvl, mk)
        s_gc = safe_num_sum(df_gc, mk)
        s_vt = safe_num_sum(df_vt, mk)
        rows.append({
            "Ngày": ngay_cu,
            "Mã khuôn": mk,
            "Tổng Nguyên Vật Liệu (A)": s_nvl,
            "Tổng Gia Công (B)": s_gc,
            "Tổng Vật Tư (C)": s_vt,
            "TỔNG CỘNG": s_nvl + s_gc + s_vt
        })
    save_data(pd.DataFrame(rows), "wanchi_d")

def merge_filtered_edits(df_full, edited_filtered, filter_mold):
    clean_edited = edited_filtered.drop(columns=["Chọn"], errors="ignore").copy()
    if filter_mold == "Tất cả":
        return clean_edited
    if "Mã khuôn" in clean_edited.columns:
        clean_edited["Mã khuôn"] = clean_edited["Mã khuôn"].fillna(filter_mold)
        clean_edited.loc[clean_edited["Mã khuôn"].astype(str).str.strip() == "", "Mã khuôn"] = filter_mold
    df_others = df_full[df_full["Mã khuôn"] != filter_mold].copy()
    return pd.concat([df_others, clean_edited], ignore_index=True)

def partner_selector(label, partner_list, key_prefix):
    options = ["-- Chọn đối tác --"] + partner_list + ["➕ Nhập tên mới..."]
    selected = st.selectbox(label, options, key=f"{key_prefix}_sel")
    if selected == "➕ Nhập tên mới...":
        return st.text_input(f"Nhập tên {label.lower()} mới:", key=f"{key_prefix}_txt").strip()
    elif selected == "-- Chọn đối tác --":
        return ""
    return selected

def render_export_image_bar(edited_df, title, file_prefix, state_key, df_nvl_ref, include_vendor=False):
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🖼️ Xuất ảnh các dòng đã chọn", use_container_width=True, key=f"btn_{state_key}"):
            selected = edited_df[edited_df["Chọn"] == True]
            if selected.empty:
                st.warning("⚠️ Hãy tick vào cột 'Chọn' ở những dòng bạn muốn xuất ảnh.")
            else:
                with st.spinner("Đang tạo ảnh báo cáo..."):
                    unique_molds = selected["Mã khuôn"].dropna().unique().tolist() if "Mã khuôn" in selected.columns else []
                    mold_str = unique_molds[0] if len(unique_molds) == 1 else "NHIỀU MÃ KHUÔN"

                    dvgc_str = None
                    if include_vendor and "Đơn vị gia công" in selected.columns:
                        uv = selected["Đơn vị gia công"].dropna().unique().tolist()
                        dvgc_str = uv[0] if len(uv) == 1 else None

                    kh_str = None
                    if mold_str != "NHIỀU MÃ KHUÔN" and not df_nvl_ref.empty:
                        try:
                            row_kh = df_nvl_ref[(df_nvl_ref["Mã khuôn"] == mold_str) & (df_nvl_ref["Tên NVL"] == "Khởi tạo khuôn")]
                            if not row_kh.empty:
                                raw = str(row_kh.iloc[0]["Nhà cung cấp NVL"])
                                kh_str = raw[4:] if raw.startswith("KH: ") else raw.strip()
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
    with c2:
        if st.session_state.get(f"img_{state_key}"):
            st.download_button(
                "⬇️ Tải ảnh về máy",
                st.session_state[f"img_{state_key}"],
                st.session_state.get(f"fname_{state_key}", f"WANCHI_{file_prefix}.png"),
                "image/png",
                type="primary",
                use_container_width=True,
                key=f"dl_{state_key}"
            )

# ==========================================
# TẢI DỮ LIỆU TỪ DATABASE (GIỮ NGUYÊN CẤU TRÚC GỐC)
# ==========================================
cols_nvl = ["Ngày", "Nhà cung cấp NVL", "Mã khuôn", "Tên NVL", "Quy cách", "Số lượng", "Đơn giá", "Tổng tiền"]
df_nvl = load_data("wanchi_a", cols_nvl)
df_nvl = df_nvl.loc[:, ~df_nvl.columns.duplicated()]

cols_gc = [
    "Ngày", "Đơn vị gia công", "Mã khuôn", "Cắt dây", "Xung điện (EDM)", "Phay CNC",
    "Nhiệt Luyện", "Đánh bóng", "Tạo Nhám hoa văn", "Dọn phôi", "Ráp khuôn hoàn chỉnh", "Tổng tiền"
]
gc_stages = [
    "Cắt dây", "Xung điện (EDM)", "Phay CNC", "Nhiệt Luyện",
    "Đánh bóng", "Tạo Nhám hoa văn", "Dọn phôi", "Ráp khuôn hoàn chỉnh"
]
df_gc = load_data("wanchi_b", cols_gc)
for old_col in ["Đơn giá", "Cụm khuôn hoàn chỉnh", "Ráp khuôn hoàn thiện"]:
    if old_col in df_gc.columns:
        df_gc.rename(columns={old_col: "Ráp khuôn hoàn chỉnh"}, inplace=True)
df_gc = df_gc.loc[:, ~df_gc.columns.duplicated()]
if "Dọn phôi" not in df_gc.columns:
    df_gc["Dọn phôi"] = 0
df_gc = df_gc[[c for c in cols_gc if c in df_gc.columns]]

cols_vt = ["Ngày", "Nhà cung cấp vật tư", "Mã khuôn", "Tên linh kiện", "Đơn giá", "Tổng tiền"]
df_vt = load_data("wanchi_c", cols_vt)
df_vt = df_vt.loc[:, ~df_vt.columns.duplicated()]

cols_sum = ["Ngày", "Mã khuôn", "Tổng Nguyên Vật Liệu (A)", "Tổng Gia Công (B)", "Tổng Vật Tư (C)", "TỔNG CỘNG"]
df_sum = load_data("wanchi_d", cols_sum)
df_sum = df_sum.loc[:, ~df_sum.columns.duplicated()]

cols_dh = ["Mã khuôn", "Đơn vị gia công", "Các mục gia công", "Thời gian nhận", "Thời gian bàn giao", "Tổng giá gia công", "Cọc đợt 1", "Còn nợ", "Ghi chú"]
df_dh = load_data("wanchi_f", cols_dh)
df_dh = df_dh.loc[:, ~df_dh.columns.duplicated()]

cols_dt = ["Phân loại", "Tên đối tác"]
df_dt = load_data("wanchi_doitac", cols_dt)
df_dt = df_dt.loc[:, ~df_dt.columns.duplicated()]

# Danh sách Master Khuôn & Đối tác
all_molds_set = set()
for df_tmp in [df_nvl, df_gc, df_vt, df_sum, df_dh]:
    if not df_tmp.empty and "Mã khuôn" in df_tmp.columns:
        all_molds_set.update([str(x).strip() for x in df_tmp["Mã khuôn"].dropna().unique() if str(x).strip()])
list_molds = sorted(list(all_molds_set))

list_ncc = sorted(list(set(
    (df_dt[df_dt["Phân loại"] == "Nhà cung cấp (NCC)"]["Tên đối tác"].dropna().tolist() if not df_dt.empty else []) +
    (df_nvl["Nhà cung cấp NVL"].dropna().tolist() if not df_nvl.empty else []) +
    (df_vt["Nhà cung cấp vật tư"].dropna().tolist() if not df_vt.empty else [])
)))
list_ncc = [x for x in list_ncc if str(x).strip() and not str(x).startswith("KH: ")]

list_ngc = sorted(list(set(
    (df_dt[df_dt["Phân loại"] == "Nhà gia công (NGC)"]["Tên đối tác"].dropna().tolist() if not df_dt.empty else []) +
    (df_gc["Đơn vị gia công"].dropna().tolist() if not df_gc.empty else []) +
    (df_dh["Đơn vị gia công"].dropna().tolist() if not df_dh.empty else [])
)))
list_ngc = [x for x in list_ngc if str(x).strip()]

# ==========================================
# CẤU HÌNH CỘT CHUẨN (GỌN, KHÔNG CHE CHỮ)
# ==========================================
COL_CFG_NVL = {
    "Chọn": st.column_config.CheckboxColumn("Chọn", help="Tick để Xóa hoặc Xuất ảnh", width="small"),
    "Ngày": st.column_config.TextColumn("Ngày", width="small"),
    "Mã khuôn": st.column_config.TextColumn("Mã khuôn", width="small"),
    "Nhà cung cấp NVL": st.column_config.TextColumn("Nhà cung cấp", width="medium"),
    "Tên NVL": st.column_config.TextColumn("Tên vật liệu", width="medium"),
    "Quy cách": st.column_config.TextColumn("Quy cách", width="medium"),
    "Số lượng": st.column_config.NumberColumn("SL", format="%.2f", width="small"),
    "Đơn giá": st.column_config.NumberColumn("Đơn giá", format="%,.0f", width="small"),
    "Tổng tiền": st.column_config.NumberColumn("Thành tiền", format="%,.0f", width="medium"),
}

COL_CFG_GC = {
    "Chọn": st.column_config.CheckboxColumn("Chọn", help="Tick để Xóa hoặc Xuất ảnh", width="small"),
    "Ngày": st.column_config.TextColumn("Ngày", width="small"),
    "Mã khuôn": st.column_config.TextColumn("Mã khuôn", width="small"),
    "Đơn vị gia công": st.column_config.TextColumn("ĐV gia công", width="medium"),
    "Cắt dây": st.column_config.NumberColumn("Cắt dây", format="%,.0f", width="small"),
    "Xung điện (EDM)": st.column_config.NumberColumn("EDM", format="%,.0f", width="small"),
    "Phay CNC": st.column_config.NumberColumn("Phay CNC", format="%,.0f", width="small"),
    "Nhiệt Luyện": st.column_config.NumberColumn("Nhiệt luyện", format="%,.0f", width="small"),
    "Đánh bóng": st.column_config.NumberColumn("Đánh bóng", format="%,.0f", width="small"),
    "Tạo Nhám hoa văn": st.column_config.NumberColumn("Tạo nhám", format="%,.0f", width="small"),
    "Dọn phôi": st.column_config.NumberColumn("Dọn phôi", format="%,.0f", width="small"),
    "Ráp khuôn hoàn chỉnh": st.column_config.NumberColumn("Ráp khuôn", format="%,.0f", width="small"),
    "Tổng tiền": st.column_config.NumberColumn("Tổng tiền", format="%,.0f", width="medium"),
}

COL_CFG_VT = {
    "Chọn": st.column_config.CheckboxColumn("Chọn", help="Tick để Xóa hoặc Xuất ảnh", width="small"),
    "Ngày": st.column_config.TextColumn("Ngày", width="small"),
    "Mã khuôn": st.column_config.TextColumn("Mã khuôn", width="small"),
    "Nhà cung cấp vật tư": st.column_config.TextColumn("Nhà cung cấp", width="medium"),
    "Tên linh kiện": st.column_config.TextColumn("Tên linh kiện", width="large"),
    "Đơn giá": st.column_config.NumberColumn("Đơn giá", format="%,.0f", width="small"),
    "Tổng tiền": st.column_config.NumberColumn("Thành tiền", format="%,.0f", width="medium"),
}

COL_CFG_SUM = {
    "Chọn": st.column_config.CheckboxColumn("Chọn", help="Tick để Xóa hoặc Xuất ảnh", width="small"),
    "Ngày": st.column_config.TextColumn("Ngày tạo", width="small"),
    "Mã khuôn": st.column_config.TextColumn("Mã khuôn", width="medium"),
    "Tổng Nguyên Vật Liệu (A)": st.column_config.NumberColumn("Nguyên vật liệu", format="%,.0f", width="medium"),
    "Tổng Gia Công (B)": st.column_config.NumberColumn("Gia công", format="%,.0f", width="medium"),
    "Tổng Vật Tư (C)": st.column_config.NumberColumn("Vật tư", format="%,.0f", width="medium"),
    "TỔNG CỘNG": st.column_config.NumberColumn("Tổng cộng", format="%,.0f", width="medium"),
}

COL_CFG_DH = {
    "Chọn": st.column_config.CheckboxColumn("Chọn", help="Tick để Xóa hoặc Xuất ảnh", width="small"),
    "Mã khuôn": st.column_config.TextColumn("Mã khuôn", width="small"),
    "Đơn vị gia công": st.column_config.TextColumn("ĐV gia công", width="medium"),
    "Các mục gia công": st.column_config.TextColumn("Hạng mục", width="large"),
    "Thời gian nhận": st.column_config.TextColumn("Ngày nhận", width="small"),
    "Thời gian bàn giao": st.column_config.TextColumn("Ngày giao", width="small"),
    "Tổng giá gia công": st.column_config.NumberColumn("Tổng giá", format="%,.0f", width="small"),
    "Cọc đợt 1": st.column_config.NumberColumn("Đã cọc", format="%,.0f", width="small"),
    "Còn nợ": st.column_config.NumberColumn("Còn nợ", format="%,.0f", width="small"),
    "Ghi chú": st.column_config.TextColumn("Ghi chú", width="medium"),
}

# ==========================================
# THANH ĐIỀU HƯỚNG SẠCH (KHÔNG A, B, C, D)
# ==========================================
st.title("🏭 Quản Lý Khuôn Mẫu WANCHI")

nav_options = [
    "🏠 Hồ Sơ Khuôn Mẫu",
    "🧾 Nhập & Sổ Chi Phí",
    "📦 Đơn Hàng Gia Công",
    "🗂️ Danh Mục Đối Tác"
]

if "active_page" not in st.session_state or st.session_state.active_page not in nav_options:
    st.session_state.active_page = nav_options[0]

nav_cols = st.columns(4)
for idx, label in enumerate(nav_options):
    b_type = "primary" if st.session_state.active_page == label else "secondary"
    if nav_cols[idx].button(label, use_container_width=True, type=b_type):
        st.session_state.active_page = label
        st.rerun()

st.markdown("---")

# ==============================================================================
# TRANG 1: HỒ SƠ KHUÔN MẪU (BẢNG DỌC + TỔNG HỢP + TẠO KHUÔN MỚI)
# ==============================================================================
if st.session_state.active_page == nav_options[0]:
    # --- Khối 1: Tổng quan nhanh toàn xưởng ---
    tong_nvl_all = pd.to_numeric(df_nvl["Tổng tiền"], errors='coerce').fillna(0).sum() if not df_nvl.empty else 0
    tong_gc_all = pd.to_numeric(df_gc["Tổng tiền"], errors='coerce').fillna(0).sum() if not df_gc.empty else 0
    tong_vt_all = pd.to_numeric(df_vt["Tổng tiền"], errors='coerce').fillna(0).sum() if not df_vt.empty else 0
    tong_all = tong_nvl_all + tong_gc_all + tong_vt_all

    k1, k2 = st.columns(2)
    k1.metric("📦 Tổng số dự án khuôn", f"{len(list_molds)} khuôn")
    k2.metric("💵 Tổng chi phí toàn xưởng", f"{tong_all:,.0f} đ")

    # --- Khối 2: Tạo khuôn mới (dọc, thoáng) ---
    with st.expander("➕ Tạo Dự Án Khuôn Mới", expanded=(len(list_molds) == 0)):
        with st.form("form_new_mold", clear_on_submit=True):
            c1, c2 = st.columns(2)
            ngay_tao = c1.date_input("Ngày khởi tạo", datetime.today())
            ma_khuon_moi = c2.text_input("Mã khuôn mới (*)", placeholder="VD: KHUON_2026_01")
            if st.form_submit_button("🚀 Xác nhận tạo khuôn", type="primary", use_container_width=True):
                mk_clean = ma_khuon_moi.strip().upper()
                if not mk_clean:
                    st.error("⚠️ Vui lòng nhập Mã khuôn.")
                elif mk_clean in list_molds:
                    st.error(f"⚠️ Mã khuôn **{mk_clean}** đã tồn tại.")
                else:
                    with st.spinner("Đang khởi tạo..."):
                        append_data({
                            "Ngày": ngay_tao.strftime('%d/%m/%Y'),
                            "Mã khuôn": mk_clean,
                            "Tổng Nguyên Vật Liệu (A)": 0,
                            "Tổng Gia Công (B)": 0,
                            "Tổng Vật Tư (C)": 0,
                            "TỔNG CỘNG": 0
                        }, "wanchi_d", df_sum)
                    st.success(f"🎉 Đã khởi tạo khuôn **{mk_clean}** thành công!")
                    time.sleep(1)
                    st.rerun()

    st.markdown("---")

    # --- Khối 3: Xem Hồ Sơ Chi Tiết 1 Khuôn (DẠNG BẢNG DỌC) ---
    st.subheader("🔎 Hồ Sơ Chi Tiết Theo Mã Khuôn")
    if list_molds:
        selected_mold = st.selectbox("Chọn mã khuôn cần xem:", list_molds, key="profile_mold")

        s_nvl = safe_num_sum(df_nvl, selected_mold)
        s_gc = safe_num_sum(df_gc, selected_mold)
        s_vt = safe_num_sum(df_vt, selected_mold)
        s_tot = s_nvl + s_gc + s_vt

        # Bảng tổng kết theo CHIỀU DỌC (Hạng mục | Chi phí | Tỷ trọng)
        def pct(val):
            return f"{(val / s_tot * 100):.1f}%" if s_tot > 0 else "0.0%"

        df_vertical_summary = pd.DataFrame([
            {"Hạng mục chi phí": "🧱 Nguyên Vật Liệu", "Số tiền (VNĐ)": s_nvl, "Tỷ trọng": pct(s_nvl)},
            {"Hạng mục chi phí": "⚙️ Chi Phí Gia Công", "Số tiền (VNĐ)": s_gc, "Tỷ trọng": pct(s_gc)},
            {"Hạng mục chi phí": "🔩 Vật Tư & Linh Kiện", "Số tiền (VNĐ)": s_vt, "Tỷ trọng": pct(s_vt)},
            {"Hạng mục chi phí": "💰 TỔNG GIÁ TRỊ KHUÔN", "Số tiền (VNĐ)": s_tot, "Tỷ trọng": "100.0%" if s_tot > 0 else "0.0%"},
        ])

        st.dataframe(
            df_vertical_summary,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Hạng mục chi phí": st.column_config.TextColumn("Hạng mục chi phí", width="large"),
                "Số tiền (VNĐ)": st.column_config.NumberColumn("Số tiền (VNĐ)", format="%,.0f", width="medium"),
                "Tỷ trọng": st.column_config.TextColumn("Tỷ trọng", width="small"),
            }
        )

        # Chi tiết từng phần bên dưới theo chiều dọc (mở ra xem ngay)
        with st.expander(f"🧱 Chi tiết Nguyên Vật Liệu ({len(df_nvl[df_nvl['Mã khuôn'] == selected_mold])} dòng)"):
            sub_nvl = prep_numeric_cols(df_nvl[df_nvl["Mã khuôn"] == selected_mold], ["Số lượng", "Đơn giá", "Tổng tiền"])
            if not sub_nvl.empty:
                st.dataframe(sub_nvl, use_container_width=True, hide_index=True, column_config=COL_CFG_NVL)
            else:
                st.info("Chưa có dữ liệu Nguyên vật liệu.")

        with st.expander(f"⚙️ Chi tiết Gia Công ({len(df_gc[df_gc['Mã khuôn'] == selected_mold])} dòng)"):
            sub_gc = prep_numeric_cols(df_gc[df_gc["Mã khuôn"] == selected_mold], gc_stages + ["Tổng tiền"])
            if not sub_gc.empty:
                stage_totals = [{"Công đoạn gia công": stg, "Chi phí (VNĐ)": float(sub_gc[stg].sum())} for stg in gc_stages if float(sub_gc[stg].sum()) > 0]
                if stage_totals:
                    st.caption("Tóm tắt theo từng công đoạn (chiều dọc):")
                    st.dataframe(
                        pd.DataFrame(stage_totals),
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "Công đoạn gia công": st.column_config.TextColumn("Công đoạn", width="large"),
                            "Chi phí (VNĐ)": st.column_config.NumberColumn("Chi phí (VNĐ)", format="%,.0f", width="medium"),
                        }
                    )
                st.caption("Bảng chi tiết từng đợt gia công:")
                st.dataframe(sub_gc, use_container_width=True, hide_index=True, column_config=COL_CFG_GC)
            else:
                st.info("Chưa có dữ liệu Gia công.")

        with st.expander(f"🔩 Chi tiết Vật Tư & Linh Kiện ({len(df_vt[df_vt['Mã khuôn'] == selected_mold])} dòng)"):
            sub_vt = prep_numeric_cols(df_vt[df_vt["Mã khuôn"] == selected_mold], ["Đơn giá", "Tổng tiền"])
            if not sub_vt.empty:
                st.dataframe(sub_vt, use_container_width=True, hide_index=True, column_config=COL_CFG_VT)
            else:
                st.info("Chưa có dữ liệu Vật tư.")

        with st.expander(f"📦 Đơn Hàng Gia Công Liên Quan ({len(df_dh[df_dh['Mã khuôn'] == selected_mold])} đơn)"):
            sub_dh = prep_numeric_cols(df_dh[df_dh["Mã khuôn"] == selected_mold], ["Tổng giá gia công", "Cọc đợt 1", "Còn nợ"])
            if not sub_dh.empty:
                st.dataframe(sub_dh, use_container_width=True, hide_index=True, column_config=COL_CFG_DH)
            else:
                st.info("Chưa có đơn hàng gia công cho khuôn này.")
    else:
        st.info("Chưa có mã khuôn nào trong hệ thống.")

    st.markdown("---")

    # --- Khối 4: Bảng Tổng Hợp Tất Cả Các Khuôn ---
    h1, h2 = st.columns([3, 1])
    h1.subheader("📑 Danh Sách Tổng Giá Trị Các Khuôn")
    if h2.button("🔄 Đồng bộ số liệu", use_container_width=True):
        with st.spinner("Đang đồng bộ toàn bộ..."):
            sync_all_molds_to_summary(list_molds, df_nvl, df_gc, df_vt, df_sum)
        st.success("✅ Đã đồng bộ chính xác toàn bộ khuôn!")
        time.sleep(1)
        st.rerun()

    df_sum_disp = prep_numeric_cols(df_sum, ["Tổng Nguyên Vật Liệu (A)", "Tổng Gia Công (B)", "Tổng Vật Tư (C)", "TỔNG CỘNG"])
    df_sum_disp.insert(0, "Chọn", False)
    edited_sum = st.data_editor(
        df_sum_disp,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        column_config=COL_CFG_SUM,
        key="edit_sum"
    )
    edited_sum["Chọn"] = edited_sum["Chọn"].fillna(False).astype(bool)

    b_sum1, b_sum2 = st.columns(2)
    with b_sum1:
        if st.button("💾 Lưu Thay Đổi Bảng Tổng Hợp", type="primary", use_container_width=True):
            with st.spinner("Đang lưu..."):
                save_data(edited_sum.drop(columns=["Chọn"]), "wanchi_d")
            st.success("✅ Đã lưu bảng tổng hợp!")
            time.sleep(1)
            st.rerun()
    with b_sum2:
        if st.button("🗑️ Xóa Dòng Đã Chọn", use_container_width=True, key="del_sum"):
            if not edited_sum["Chọn"].any():
                st.warning("⚠️ Vui lòng tick vào cột 'Chọn' ở ít nhất 1 dòng cần xóa.")
            else:
                with st.spinner("Đang xóa dòng đã chọn..."):
                    remaining = edited_sum[edited_sum["Chọn"] == False].drop(columns=["Chọn"])
                    save_data(remaining, "wanchi_d")
                st.success("✅ Đã xóa các dòng đã chọn!")
                time.sleep(1)
                st.rerun()

    render_export_image_bar(edited_sum, "BẢNG TỔNG HỢP CHI PHÍ KHUÔN", "TongHop", "sum_page", df_nvl)

# ==============================================================================
# TRANG 2: NHẬP & SỔ CHI PHÍ (NGUYÊN VẬT LIỆU | GIA CÔNG | VẬT TƯ)
# ==============================================================================
elif st.session_state.active_page == nav_options[1]:
    # Chọn mã khuôn thao tác dùng chung
    filter_mold = st.selectbox(
        "🎯 Chọn Mã Khuôn đang thao tác (để lọc bảng và điền sẵn vào ô nhập):",
        ["Tất cả"] + list_molds,
        key="cost_filter_mold"
    )
    default_idx = list_molds.index(filter_mold) if filter_mold in list_molds else 0

    tab_nvl, tab_gc, tab_vt = st.tabs(["🧱 Nguyên Vật Liệu", "⚙️ Gia Công", "🔩 Vật Tư & Linh Kiện"])

    # ---------------- TAB 1: NGUYÊN VẬT LIỆU ----------------
    with tab_nvl:
        with st.expander("➕ Thêm Nguyên Vật Liệu Mới", expanded=False):
            r1c1, r1c2 = st.columns(2)
            ngay_a = r1c1.date_input("Ngày nhập", datetime.today(), key="ngay_nvl")
            mk_a = r1c2.selectbox("Mã khuôn", list_molds, index=default_idx, key="mk_nvl") if list_molds else r1c2.text_input("Mã khuôn", key="mk_nvl_txt")

            r2c1, r2c2 = st.columns(2)
            with r2c1:
                ncc_a = partner_selector("Nhà cung cấp", list_ncc, "ncc_nvl")
            ten_nvl = r2c2.text_input("Tên nguyên vật liệu (*)", placeholder="VD: Thép P20, S50C, SKD11...", key="ten_nvl_in")

            r3c1, r3c2 = st.columns(2)
            quy_cach = r3c1.text_input("Quy cách / Kích thước", placeholder="VD: 200x300x50", key="qc_nvl_in")
            sl_a = r3c2.number_input("Số lượng (kg / tấm)", min_value=0.0, step=1.0, key="sl_nvl_in")

            r4c1, r4c2 = st.columns(2)
            dg_a = r4c1.number_input("Đơn giá (VNĐ)", min_value=0, step=1000, key="dg_nvl_in")
            auto_a = int(round(sl_a * dg_a))
            ovr_a = r4c2.number_input(
                "Thành tiền ghi đè (để 0 = tự tính SL × Đơn giá)",
                min_value=0, step=1000, value=0, key="ovr_nvl_in"
            )
            final_a = ovr_a if ovr_a > 0 else auto_a

            st.info(f"💰 **Thành tiền sẽ lưu:** `{final_a:,.0f} đ`")
            if st.button("💾 Lưu Nguyên Vật Liệu", type="primary", use_container_width=True, key="btn_save_nvl"):
                if not mk_a or not ten_nvl.strip():
                    st.error("⚠️ Vui lòng chọn Mã khuôn và nhập Tên nguyên vật liệu.")
                else:
                    with st.spinner("Đang lưu và cập nhật hồ sơ khuôn..."):
                        mk_up = mk_a.strip().upper()
                        row_new = {
                            "Ngày": ngay_a.strftime('%d/%m/%Y'),
                            "Nhà cung cấp NVL": ncc_a,
                            "Mã khuôn": mk_up,
                            "Tên NVL": ten_nvl.strip(),
                            "Quy cách": quy_cach.strip(),
                            "Số lượng": sl_a,
                            "Đơn giá": dg_a,
                            "Tổng tiền": final_a
                        }
                        append_data(row_new, "wanchi_a", df_nvl)
                        df_nvl_new = pd.concat([df_nvl, pd.DataFrame([row_new])], ignore_index=True)
                        auto_sync_mold_to_summary(mk_up, df_nvl_new, df_gc, df_vt, df_sum)
                    st.success("✅ Đã lưu Nguyên vật liệu!")
                    time.sleep(1)
                    st.rerun()

        st.subheader("Danh Sách Nguyên Vật Liệu")
        df_nvl_view = df_nvl[df_nvl["Mã khuôn"] == filter_mold].copy() if filter_mold != "Tất cả" else df_nvl.copy()
        df_nvl_view = prep_numeric_cols(df_nvl_view, ["Số lượng", "Đơn giá", "Tổng tiền"])
        df_nvl_view.insert(0, "Chọn", False)

        edited_nvl = st.data_editor(
            df_nvl_view,
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            column_config=COL_CFG_NVL,
            key="edit_nvl"
        )
        edited_nvl["Chọn"] = edited_nvl["Chọn"].fillna(False).astype(bool)

        b_nvl1, b_nvl2 = st.columns(2)
        with b_nvl1:
            if st.button("💾 Lưu Chỉnh Sửa Bảng Nguyên Vật Liệu", type="primary", use_container_width=True, key="upd_nvl"):
                with st.spinner("Đang cập nhật..."):
                    merged = merge_filtered_edits(df_nvl, edited_nvl, filter_mold)
                    save_data(merged, "wanchi_a")
                    if filter_mold != "Tất cả":
                        auto_sync_mold_to_summary(filter_mold, merged, df_gc, df_vt, df_sum)
                    else:
                        sync_all_molds_to_summary(list_molds, merged, df_gc, df_vt, df_sum)
                st.success("✅ Đã cập nhật Nguyên vật liệu!")
                time.sleep(1)
                st.rerun()
        with b_nvl2:
            if st.button("🗑️ Xóa Dòng Đã Chọn", use_container_width=True, key="del_nvl"):
                if not edited_nvl["Chọn"].any():
                    st.warning("⚠️ Vui lòng tick vào cột 'Chọn' ở ít nhất 1 dòng cần xóa.")
                else:
                    with st.spinner("Đang xóa và đồng bộ lại bảng tổng..."):
                        remaining_view = edited_nvl[edited_nvl["Chọn"] == False]
                        merged = merge_filtered_edits(df_nvl, remaining_view, filter_mold)
                        save_data(merged, "wanchi_a")
                        if filter_mold != "Tất cả":
                            auto_sync_mold_to_summary(filter_mold, merged, df_gc, df_vt, df_sum)
                        else:
                            sync_all_molds_to_summary(list_molds, merged, df_gc, df_vt, df_sum)
                    st.success("✅ Đã xóa các dòng đã chọn!")
                    time.sleep(1)
                    st.rerun()

        render_export_image_bar(edited_nvl, "BÁO CÁO NGUYÊN VẬT LIỆU", "NVL", "exp_nvl", df_nvl)

    # ---------------- TAB 2: GIA CÔNG (NHẬP BẰNG BẢNG DỌC 2 CỘT) ----------------
    with tab_gc:
        with st.expander("➕ Thêm Chi Phí Gia Công Mới", expanded=False):
            r1c1, r1c2 = st.columns(2)
            ngay_b = r1c1.date_input("Ngày gia công", datetime.today(), key="ngay_gc")
            mk_b = r1c2.selectbox("Mã khuôn", list_molds, index=default_idx, key="mk_gc") if list_molds else r1c2.text_input("Mã khuôn", key="mk_gc_txt")

            dv_b = partner_selector("Đơn vị gia công", list_ngc, "ngc_gc")

            if "gc_stage_reset" not in st.session_state:
                st.session_state["gc_stage_reset"] = 0

            hdr_st1, hdr_st2 = st.columns([3, 1])
            hdr_st1.markdown("**Nhập chi phí theo từng công đoạn (bảng dọc):**")
            if hdr_st2.button("🧹 Xóa trắng số liệu", use_container_width=True, key="reset_gc_stage"):
                st.session_state["gc_stage_reset"] += 1
                st.rerun()

            df_stage_input = pd.DataFrame({
                "Công đoạn": gc_stages,
                "Chi phí (VNĐ)": [0] * len(gc_stages)
            })
            edited_stages = st.data_editor(
                df_stage_input,
                use_container_width=True,
                hide_index=True,
                disabled=["Công đoạn"],
                column_config={
                    "Công đoạn": st.column_config.TextColumn("Công đoạn gia công", width="large"),
                    "Chi phí (VNĐ)": st.column_config.NumberColumn("Chi phí (VNĐ)", min_value=0, step=10000, format="%,.0f", width="medium"),
                },
                key=f"stage_vertical_editor_{st.session_state['gc_stage_reset']}"
            )

            stage_map = dict(zip(edited_stages["Công đoạn"], pd.to_numeric(edited_stages["Chi phí (VNĐ)"], errors='coerce').fillna(0)))
            auto_b = int(sum(stage_map.values()))

            c_ov1, c_ov2 = st.columns(2)
            c_ov1.info(f"🧮 **Tổng tự cộng các công đoạn:** `{auto_b:,.0f} đ`")
            ovr_b = c_ov2.number_input("Ghi đè Tổng tiền (để 0 = lấy tổng tự cộng)", min_value=0, step=10000, value=0, key="ovr_gc")
            final_b = ovr_b if ovr_b > 0 else auto_b

            if st.button("💾 Lưu Chi Phí Gia Công", type="primary", use_container_width=True, key="btn_save_gc"):
                if not mk_b:
                    st.error("⚠️ Vui lòng chọn Mã khuôn.")
                elif final_b <= 0:
                    st.error("⚠️ Vui lòng nhập chi phí cho ít nhất 1 công đoạn.")
                else:
                    with st.spinner("Đang lưu và cập nhật hồ sơ khuôn..."):
                        mk_up = mk_b.strip().upper()
                        row_gc = {
                            "Ngày": ngay_b.strftime('%d/%m/%Y'),
                            "Đơn vị gia công": dv_b,
                            "Mã khuôn": mk_up,
                            "Cắt dây": stage_map.get("Cắt dây", 0),
                            "Xung điện (EDM)": stage_map.get("Xung điện (EDM)", 0),
                            "Phay CNC": stage_map.get("Phay CNC", 0),
                            "Nhiệt Luyện": stage_map.get("Nhiệt Luyện", 0),
                            "Đánh bóng": stage_map.get("Đánh bóng", 0),
                            "Tạo Nhám hoa văn": stage_map.get("Tạo Nhám hoa văn", 0),
                            "Dọn phôi": stage_map.get("Dọn phôi", 0),
                            "Ráp khuôn hoàn chỉnh": stage_map.get("Ráp khuôn hoàn chỉnh", 0),
                            "Tổng tiền": final_b
                        }
                        append_data(row_gc, "wanchi_b", df_gc)
                        df_gc_new = pd.concat([df_gc, pd.DataFrame([row_gc])], ignore_index=True)
                        auto_sync_mold_to_summary(mk_up, df_nvl, df_gc_new, df_vt, df_sum)
                        st.session_state["gc_stage_reset"] += 1
                    st.success("✅ Đã lưu chi phí Gia công!")
                    time.sleep(1)
                    st.rerun()

        st.subheader("Danh Sách Chi Phí Gia Công")
        df_gc_view = df_gc[df_gc["Mã khuôn"] == filter_mold].copy() if filter_mold != "Tất cả" else df_gc.copy()
        df_gc_view = prep_numeric_cols(df_gc_view, gc_stages + ["Tổng tiền"])
        df_gc_view.insert(0, "Chọn", False)

        edited_gc = st.data_editor(
            df_gc_view,
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            column_config=COL_CFG_GC,
            key="edit_gc"
        )
        edited_gc["Chọn"] = edited_gc["Chọn"].fillna(False).astype(bool)

        b_gc1, b_gc2 = st.columns(2)
        with b_gc1:
            if st.button("💾 Lưu Chỉnh Sửa Bảng Gia Công", type="primary", use_container_width=True, key="upd_gc"):
                with st.spinner("Đang cập nhật..."):
                    merged = merge_filtered_edits(df_gc, edited_gc, filter_mold)
                    save_data(merged, "wanchi_b")
                    if filter_mold != "Tất cả":
                        auto_sync_mold_to_summary(filter_mold, df_nvl, merged, df_vt, df_sum)
                    else:
                        sync_all_molds_to_summary(list_molds, df_nvl, merged, df_vt, df_sum)
                st.success("✅ Đã cập nhật Gia công!")
                time.sleep(1)
                st.rerun()
        with b_gc2:
            if st.button("🗑️ Xóa Dòng Đã Chọn", use_container_width=True, key="del_gc"):
                if not edited_gc["Chọn"].any():
                    st.warning("⚠️ Vui lòng tick vào cột 'Chọn' ở ít nhất 1 dòng cần xóa.")
                else:
                    with st.spinner("Đang xóa và đồng bộ lại bảng tổng..."):
                        remaining_view = edited_gc[edited_gc["Chọn"] == False]
                        merged = merge_filtered_edits(df_gc, remaining_view, filter_mold)
                        save_data(merged, "wanchi_b")
                        if filter_mold != "Tất cả":
                            auto_sync_mold_to_summary(filter_mold, df_nvl, merged, df_vt, df_sum)
                        else:
                            sync_all_molds_to_summary(list_molds, df_nvl, merged, df_vt, df_sum)
                    st.success("✅ Đã xóa các dòng đã chọn!")
                    time.sleep(1)
                    st.rerun()

        render_export_image_bar(edited_gc, "BÁO CÁO CHI PHÍ GIA CÔNG", "GiaCong", "exp_gc", df_nvl)

    # ---------------- TAB 3: VẬT TƯ & LINH KIỆN ----------------
    with tab_vt:
        with st.expander("➕ Thêm Vật Tư / Linh Kiện Mới", expanded=False):
            r1c1, r1c2 = st.columns(2)
            ngay_c = r1c1.date_input("Ngày mua", datetime.today(), key="ngay_vt")
            mk_c = r1c2.selectbox("Mã khuôn", list_molds, index=default_idx, key="mk_vt") if list_molds else r1c2.text_input("Mã khuôn", key="mk_vt_txt")

            r2c1, r2c2 = st.columns(2)
            with r2c1:
                ncc_c = partner_selector("Nhà cung cấp vật tư", list_ncc, "ncc_vt")
            ten_lk = r2c2.text_input("Tên linh kiện (*)", placeholder="VD: Ty đẩy, Lò xo, Bạc dẫn hướng...", key="ten_vt_in")

            r3c1, r3c2 = st.columns(2)
            sl_c = r3c1.number_input("Số lượng", min_value=1, step=1, value=1, key="sl_vt_in")
            dg_c = r3c2.number_input("Đơn giá (VNĐ)", min_value=0, step=1000, key="dg_vt_in")

            auto_c = sl_c * dg_c
            r4c1, r4c2 = st.columns(2)
            r4c1.info(f"💰 **Thành tiền tự tính:** `{auto_c:,.0f} đ`")
            ovr_c = r4c2.number_input("Ghi đè Thành tiền (để 0 = tự tính)", min_value=0, step=1000, value=0, key="ovr_vt_in")
            final_c = ovr_c if ovr_c > 0 else auto_c

            if st.button("💾 Lưu Vật Tư", type="primary", use_container_width=True, key="btn_save_vt"):
                if not mk_c or not ten_lk.strip():
                    st.error("⚠️ Vui lòng chọn Mã khuôn và nhập Tên linh kiện.")
                else:
                    with st.spinner("Đang lưu và cập nhật hồ sơ khuôn..."):
                        mk_up = mk_c.strip().upper()
                        ten_save = f"{ten_lk.strip()} (x{sl_c})" if sl_c > 1 else ten_lk.strip()
                        row_vt = {
                            "Ngày": ngay_c.strftime('%d/%m/%Y'),
                            "Nhà cung cấp vật tư": ncc_c,
                            "Mã khuôn": mk_up,
                            "Tên linh kiện": ten_save,
                            "Đơn giá": dg_c,
                            "Tổng tiền": final_c
                        }
                        append_data(row_vt, "wanchi_c", df_vt)
                        df_vt_new = pd.concat([df_vt, pd.DataFrame([row_vt])], ignore_index=True)
                        auto_sync_mold_to_summary(mk_up, df_nvl, df_gc, df_vt_new, df_sum)
                    st.success("✅ Đã lưu Vật tư!")
                    time.sleep(1)
                    st.rerun()

        st.subheader("Danh Sách Vật Tư & Linh Kiện")
        df_vt_view = df_vt[df_vt["Mã khuôn"] == filter_mold].copy() if filter_mold != "Tất cả" else df_vt.copy()
        df_vt_view = prep_numeric_cols(df_vt_view, ["Đơn giá", "Tổng tiền"])
        df_vt_view.insert(0, "Chọn", False)

        edited_vt = st.data_editor(
            df_vt_view,
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            column_config=COL_CFG_VT,
            key="edit_vt"
        )
        edited_vt["Chọn"] = edited_vt["Chọn"].fillna(False).astype(bool)

        b_vt1, b_vt2 = st.columns(2)
        with b_vt1:
            if st.button("💾 Lưu Chỉnh Sửa Bảng Vật Tư", type="primary", use_container_width=True, key="upd_vt"):
                with st.spinner("Đang cập nhật..."):
                    merged = merge_filtered_edits(df_vt, edited_vt, filter_mold)
                    save_data(merged, "wanchi_c")
                    if filter_mold != "Tất cả":
                        auto_sync_mold_to_summary(filter_mold, df_nvl, df_gc, merged, df_sum)
                    else:
                        sync_all_molds_to_summary(list_molds, df_nvl, df_gc, merged, df_sum)
                st.success("✅ Đã cập nhật Vật tư!")
                time.sleep(1)
                st.rerun()
        with b_vt2:
            if st.button("🗑️ Xóa Dòng Đã Chọn", use_container_width=True, key="del_vt"):
                if not edited_vt["Chọn"].any():
                    st.warning("⚠️ Vui lòng tick vào cột 'Chọn' ở ít nhất 1 dòng cần xóa.")
                else:
                    with st.spinner("Đang xóa và đồng bộ lại bảng tổng..."):
                        remaining_view = edited_vt[edited_vt["Chọn"] == False]
                        merged = merge_filtered_edits(df_vt, remaining_view, filter_mold)
                        save_data(merged, "wanchi_c")
                        if filter_mold != "Tất cả":
                            auto_sync_mold_to_summary(filter_mold, df_nvl, df_gc, merged, df_sum)
                        else:
                            sync_all_molds_to_summary(list_molds, df_nvl, df_gc, merged, df_sum)
                    st.success("✅ Đã xóa các dòng đã chọn!")
                    time.sleep(1)
                    st.rerun()

        render_export_image_bar(edited_vt, "BÁO CÁO VẬT TƯ KHUÔN MẪU", "VatTu", "exp_vt", df_nvl)

# ==============================================================================
# TRANG 3: ĐƠN HÀNG GIA CÔNG (TẠO ĐƠN + THEO DÕI CÔNG NỢ)
# ==============================================================================
elif st.session_state.active_page == nav_options[2]:
    tong_gia_dh = pd.to_numeric(df_dh["Tổng giá gia công"], errors='coerce').fillna(0).sum() if not df_dh.empty else 0
    tong_coc_dh = pd.to_numeric(df_dh["Cọc đợt 1"], errors='coerce').fillna(0).sum() if not df_dh.empty else 0
    tong_no_dh = pd.to_numeric(df_dh["Còn nợ"], errors='coerce').fillna(0).sum() if not df_dh.empty else 0

    m1, m2, m3 = st.columns(3)
    m1.metric("📄 Tổng giá trị đơn", f"{tong_gia_dh:,.0f} đ")
    m2.metric("✅ Đã đặt cọc", f"{tong_coc_dh:,.0f} đ")
    m3.metric("⚠️ Còn nợ", f"{tong_no_dh:,.0f} đ")

    with st.expander("➕ Tạo Đơn Hàng Gia Công Mới", expanded=False):
        r1c1, r1c2 = st.columns(2)
        mk_dh = r1c1.selectbox("Mã khuôn", list_molds, key="mk_dh") if list_molds else r1c1.text_input("Mã khuôn", key="mk_dh_txt")
        with r1c2:
            dv_dh = partner_selector("Đơn vị gia công", list_ngc, "ngc_dh")

        hang_muc = st.multiselect("Các hạng mục cần gia công (*):", gc_stages, key="hm_dh")

        r2c1, r2c2 = st.columns(2)
        ngay_nhan = r2c1.date_input("Ngày nhận phôi / khuôn", datetime.today(), key="nn_dh")
        ngay_giao = r2c2.date_input("Ngày bàn giao dự kiến", datetime.today(), key="ng_dh")

        r3c1, r3c2 = st.columns(2)
        tong_gia_in = r3c1.number_input("Tổng giá gia công (VNĐ)", min_value=0, step=10000, key="tg_dh")
        coc_in = r3c2.number_input("Tiền cọc đợt 1 (VNĐ)", min_value=0, step=10000, key="coc_dh")

        st.info(f"⚠️ **Số tiền còn nợ (tự tính):** `{max(0, tong_gia_in - coc_in):,.0f} đ`")
        ghi_chu_in = st.text_area("Ghi chú đơn hàng", placeholder="Yêu cầu kỹ thuật, dung sai, thời gian giao...", key="gc_dh")

        if st.button("🚀 Xác Nhận Tạo Đơn Hàng", type="primary", use_container_width=True, key="btn_new_dh"):
            if not mk_dh:
                st.error("⚠️ Vui lòng chọn Mã khuôn.")
            elif not dv_dh:
                st.error("⚠️ Vui lòng chọn hoặc nhập Đơn vị gia công.")
            elif not hang_muc:
                st.error("⚠️ Vui lòng chọn ít nhất 1 hạng mục gia công.")
            else:
                with st.spinner("Đang lưu đơn hàng..."):
                    append_data({
                        "Mã khuôn": mk_dh.strip().upper(),
                        "Đơn vị gia công": dv_dh,
                        "Các mục gia công": ", ".join(hang_muc),
                        "Thời gian nhận": ngay_nhan.strftime('%d/%m/%Y'),
                        "Thời gian bàn giao": ngay_giao.strftime('%d/%m/%Y'),
                        "Tổng giá gia công": tong_gia_in,
                        "Cọc đợt 1": coc_in,
                        "Còn nợ": tong_gia_in - coc_in,
                        "Ghi chú": ghi_chu_in.strip()
                    }, "wanchi_f", df_dh)
                st.success("✅ Đã tạo đơn hàng gia công mới!")
                time.sleep(1)
                st.rerun()

    st.markdown("---")
    st.subheader("📋 Bảng Theo Dõi Đơn Hàng & Công Nợ")

    fc1, fc2 = st.columns(2)
    f_mk = fc1.selectbox("Lọc theo Mã khuôn:", ["Tất cả"] + list_molds, key="f_dh_mk")
    f_dv = fc2.selectbox("Lọc theo Đơn vị gia công:", ["Tất cả"] + list_ngc, key="f_dh_dv")

    df_dh_view = df_dh.copy()
    if f_mk != "Tất cả":
        df_dh_view = df_dh_view[df_dh_view["Mã khuôn"] == f_mk]
    if f_dv != "Tất cả":
        df_dh_view = df_dh_view[df_dh_view["Đơn vị gia công"] == f_dv]

    df_dh_view = prep_numeric_cols(df_dh_view, ["Tổng giá gia công", "Cọc đợt 1", "Còn nợ"])
    df_dh_view.insert(0, "Chọn", False)

    edited_dh = st.data_editor(
        df_dh_view,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        column_config=COL_CFG_DH,
        key="edit_dh"
    )
    edited_dh["Chọn"] = edited_dh["Chọn"].fillna(False).astype(bool)

    is_filtered_dh = (f_mk != "Tất cả" or f_dv != "Tất cả")
    if is_filtered_dh:
        st.caption("💡 Hãy đưa 2 bộ lọc về 'Tất cả' để bật nút lưu chỉnh sửa trực tiếp (nút Xóa vẫn dùng được bình thường).")

    b_dh1, b_dh2 = st.columns(2)
    with b_dh1:
        if st.button("💾 Lưu Cập Nhật Đơn Hàng (Tự tính lại Còn nợ)", type="primary", use_container_width=True, disabled=is_filtered_dh):
            with st.spinner("Đang cập nhật..."):
                df_save = edited_dh.drop(columns=["Chọn"]).copy()
                tg = pd.to_numeric(df_save["Tổng giá gia công"], errors='coerce').fillna(0)
                cc = pd.to_numeric(df_save["Cọc đợt 1"], errors='coerce').fillna(0)
                df_save["Còn nợ"] = tg - cc
                save_data(df_save, "wanchi_f")
            st.success("✅ Đã cập nhật đơn hàng và công nợ!")
            time.sleep(1)
            st.rerun()
    with b_dh2:
        if st.button("🗑️ Xóa Dòng Đã Chọn", use_container_width=True, key="del_dh"):
            if not edited_dh["Chọn"].any():
                st.warning("⚠️ Vui lòng tick vào cột 'Chọn' ở ít nhất 1 đơn hàng cần xóa.")
            else:
                with st.spinner("Đang xóa đơn hàng đã chọn..."):
                    if not is_filtered_dh:
                        df_rem = edited_dh[edited_dh["Chọn"] == False].drop(columns=["Chọn"]).copy()
                    else:
                        idx_to_drop = [i for i in edited_dh[edited_dh["Chọn"] == True].index if i in df_dh.index]
                        df_rem = df_dh.drop(index=idx_to_drop).copy()
                    save_data(df_rem, "wanchi_f")
                st.success("✅ Đã xóa các đơn hàng đã chọn!")
                time.sleep(1)
                st.rerun()

    render_export_image_bar(edited_dh, "ĐƠN HÀNG GIA CÔNG", "DonHang", "exp_dh", df_nvl, include_vendor=True)

# ==============================================================================
# TRANG 4: DANH MỤC ĐỐI TÁC (BỐ CỤC DỌC GỌN GÀNG)
# ==============================================================================
elif st.session_state.active_page == nav_options[3]:
    st.subheader("➕ Thêm Đối Tác Mới")
    with st.form("form_add_partner", clear_on_submit=True):
        c1, c2 = st.columns(2)
        loai_dt = c1.selectbox("Phân loại", ["Nhà cung cấp (NCC)", "Nhà gia công (NGC)"])
        ten_dt = c2.text_input("Tên đối tác (*)", placeholder="Nhập tên công ty / xưởng...")
        if st.form_submit_button("💾 Lưu Đối Tác Mới", type="primary", use_container_width=True):
            if ten_dt.strip():
                with st.spinner("Đang lưu..."):
                    append_data({"Phân loại": loai_dt, "Tên đối tác": ten_dt.strip()}, "wanchi_doitac", df_dt)
                st.success("✅ Đã thêm đối tác mới!")
                time.sleep(1)
                st.rerun()
            else:
                st.warning("⚠️ Vui lòng nhập tên đối tác.")

    st.markdown("---")
    st.subheader("🤝 Danh Sách Đối Tác Hiện Hành")
    st.caption("Tick vào cột 'Chọn' để xóa nhanh, hoặc sửa trực tiếp rồi bấm Lưu.")

    df_dt_view = df_dt.copy()
    df_dt_view.insert(0, "Chọn", False)

    edited_dt = st.data_editor(
        df_dt_view,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        column_config={
            "Chọn": st.column_config.CheckboxColumn("Chọn", help="Tick để xóa đối tác", width="small"),
            "Phân loại": st.column_config.SelectboxColumn(
                "Phân loại",
                options=["Nhà cung cấp (NCC)", "Nhà gia công (NGC)"],
                required=True,
                width="medium"
            ),
            "Tên đối tác": st.column_config.TextColumn("Tên đối tác", width="large"),
        },
        key="edit_dt"
    )
    edited_dt["Chọn"] = edited_dt["Chọn"].fillna(False).astype(bool)

    b_dt1, b_dt2 = st.columns(2)
    with b_dt1:
        if st.button("💾 Lưu Danh Sách Đối Tác", type="primary", use_container_width=True):
            with st.spinner("Đang lưu..."):
                df_dt_save = edited_dt.drop(columns=["Chọn"]).dropna(subset=["Tên đối tác"])
                save_data(df_dt_save, "wanchi_doitac")
            st.success("✅ Đã cập nhật danh sách đối tác!")
            time.sleep(1)
            st.rerun()
    with b_dt2:
        if st.button("🗑️ Xóa Dòng Đã Chọn", use_container_width=True, key="del_dt"):
            if not edited_dt["Chọn"].any():
                st.warning("⚠️ Vui lòng tick vào cột 'Chọn' ở ít nhất 1 đối tác cần xóa.")
            else:
                with st.spinner("Đang xóa đối tác đã chọn..."):
                    df_dt_rem = edited_dt[edited_dt["Chọn"] == False].drop(columns=["Chọn"]).dropna(subset=["Tên đối tác"])
                    save_data(df_dt_rem, "wanchi_doitac")
                st.success("✅ Đã xóa các đối tác đã chọn!")
                time.sleep(1)
                st.rerun()
