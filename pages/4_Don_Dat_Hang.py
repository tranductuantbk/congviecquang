import streamlit as st
import pandas as pd
import os
from fpdf import FPDF
import unicodedata
from datetime import datetime
from sqlalchemy import text

# --- KHÓA BẢO MẬT TỪ TRANG CHỦ ---
if not st.session_state.get("logged_in", False):
    st.warning("🔒 Bạn chưa đăng nhập! Vui lòng quay lại Trang Chủ (Home) để gõ mật khẩu.")
    st.stop()

# ==========================================
# CẤU HÌNH TRANG & KẾT NỐI NEON (POSTGRESQL)
# ==========================================
st.set_page_config(page_title="WANCHI - Đơn Đặt Hàng", layout="wide")

try:
    conn = st.connection("postgresql", type="sql")
except Exception as e:
    st.error("Chưa thể kết nối đến cơ sở dữ liệu.")
    st.stop()

def remove_accents(input_str):
    s = str(input_str).replace('Đ', 'D').replace('đ', 'd')
    nfkd_form = unicodedata.normalize('NFKD', s)
    return u"".join([c for c in nfkd_form if not unicodedata.combining(c)])

# ---> HÀM XUẤT PDF CHO ĐƠN ĐẶT HÀNG <---
def export_pdf(df, title):
    df_export = df.copy()
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    
    try:
        pdf.add_font('ArialVN', '', 'arial.ttf', uni=True)
        pdf.add_font('ArialVN', 'B', 'arialbd.ttf', uni=True)
        font_name = 'ArialVN'
    except:
        font_name = 'Arial'
        st.warning("⚠️ Không tìm thấy file 'arial.ttf'. PDF sẽ bị mất dấu tiếng Việt.")

    # --- Header ---
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
        num_cols = ["Tổng tiền", "Tạm ứng", "Còn nợ"]
        
        col_widths = []
        for col in df_export.columns:
            max_w = pdf.get_string_width(str(col)) + 4 
            for item in df_export[col]:
                val_str = str(item)
                if pd.notnull(item) and str(item).strip() != "":
                    if col in num_cols:
                        try:
                            val_str = f"{float(item):,.0f}".replace(",", ".")
                        except: pass
                # Cho cột nội dung dài nhất là 60mm để ép xuống dòng
                item_w = min(pdf.get_string_width(val_str) + 4, 60) 
                if item_w > max_w:
                    max_w = item_w
            col_widths.append(max_w)
        
        total_w = sum(col_widths)
        if total_w > 0:
            scale = 277 / total_w
            col_widths = [w * scale for w in col_widths]

        pdf.set_font(font_name, 'B' if font_name == 'ArialVN' else '', 8)
        pdf.set_fill_color(220, 220, 220)
        for i, col in enumerate(df_export.columns):
            pdf.cell(col_widths[i], 8, txt=str(col), border=1, fill=True, align='C')
        pdf.ln()
        
        pdf.set_font(font_name, '', 8)
        col_sums = {c: 0.0 for c in df_export.columns}
        
        for _, row in df_export.iterrows():
            row_texts = []
            row_aligns = []
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
            
            line_height = 5
            max_lines = 1
            for i, text_val in enumerate(row_texts):
                est_width = pdf.get_string_width(text_val) * 1.1 
                lines = int(est_width / (col_widths[i] - 1)) + 1
                lines += text_val.count('\n') 
                if lines > max_lines:
                    max_lines = lines
            row_height = max_lines * line_height
            
            if pdf.get_y() + row_height > 190: 
                pdf.add_page()
            
            x_start = pdf.get_x()
            y_start = pdf.get_y()
            for i, text_val in enumerate(row_texts):
                pdf.set_xy(x_start, y_start)
                pdf.multi_cell(col_widths[i], line_height, txt=text_val, border=0, align=row_aligns[i])
                pdf.set_xy(x_start, y_start)
                pdf.cell(col_widths[i], row_height, border=1)
                x_start += col_widths[i]
            pdf.set_y(y_start + row_height)
            
        # Dòng TỔNG CỘNG
        if any(c in df_export.columns for c in num_cols):
            pdf.set_font(font_name, 'B' if font_name == 'ArialVN' else '', 9)
            pdf.set_fill_color(240, 240, 240)
            for i, col in enumerate(df_export.columns):
                if col in num_cols:
                    tong_str = f"{col_sums[col]:,.0f}".replace(",", ".")
                    pdf.cell(col_widths[i], 8, txt=tong_str, border=1, fill=True, align='R')
                elif i == 1:
                    pdf.cell(col_widths[i], 8, txt="TỔNG CỘNG:", border=1, fill=True, align='R')
                else:
                    pdf.cell(col_widths[i], 8, txt="", border=1, fill=True) 
            pdf.ln()
            
    temp_filename = f"temp_donhang_{datetime.now().strftime('%H%M%S')}.pdf"
    pdf.output(temp_filename)
    with open(temp_filename, "rb") as f:
        pdf_bytes = f.read()
    if os.path.exists(temp_filename):
        os.remove(temp_filename)
    return pdf_bytes


# ==========================================
# QUẢN LÝ DỮ LIỆU ĐÁM MÂY
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
            st.error(f"⚠️ Lỗi: {str(e2)}")

def save_data(df, table_name):
    try:
        with conn.session as session:
            session.execute(text(f"TRUNCATE TABLE {table_name}"))
            session.commit()
        df.to_sql(table_name, con=conn.engine, if_exists='append', index=False, method='multi')
        force_reload_cache()
    except Exception:
        df.to_sql(table_name, con=conn.engine, if_exists='replace', index=False, method='multi')
        force_reload_cache()

# ==========================================
# KHỞI TẠO DỮ LIỆU BẢNG MỚI (wanchi_donhang)
# ==========================================
# Bảng này hoàn toàn độc lập, không dùng chung với wanchi_g cũ để đảm bảo không dính dáng tới mã khuôn
cols_DonHang = ["Ngày", "Hạng mục / Dự án", "Đơn vị nhận thầu", "Nội dung chi tiết", "Ngày bàn giao", "Tổng tiền", "Tạm ứng", "Còn nợ", "Trạng thái", "Ghi chú"]
df_DonHang = load_data("wanchi_donhang", cols_DonHang)
df_DonHang = df_DonHang.loc[:, ~df_DonHang.columns.duplicated()]

list_du_an = df_DonHang["Hạng mục / Dự án"].dropna().unique().tolist() if not df_DonHang.empty else []

# ==========================================
# GIAO DIỆN CHÍNH
# ==========================================
st.title("📦 Quản Lý Đơn Đặt Hàng & Giao Việc (Ngoại lai)")
st.markdown("Trang này dùng để quản lý các công việc không liên quan đến sản xuất khuôn mẫu (Ví dụ: Cắt ván, làm nội thất, sửa chữa xưởng, v.v...)")
st.markdown("---")

with st.expander("➕ Tạo Đơn Đặt Hàng Mới", expanded=True):
    with st.form("form_donhang"):
        c1, c2, c3 = st.columns([1, 1.5, 1.5])
        ngay_dh = c1.date_input("Ngày đặt hàng")
        ten_du_an = c2.text_input("Tên Hạng mục / Dự án (VD: Làm mặt dựng nhà xưởng)")
        nha_thau = c3.text_input("Đơn vị nhận thầu / Nhà cung cấp")
        
        st.markdown("**Nội dung công việc chi tiết:**")
        st.caption("Nhấn phím Enter để xuống dòng liệt kê chi tiết yêu cầu, kích thước...")
        noi_dung = st.text_area("", height=150, placeholder="- Ván ép 10mm: 2 tấm 1m x 2m\n- Ván ép 5mm: 1 tấm 0.5m x 1m")
        
        c4, c5 = st.columns(2)
        ngay_giao = c4.date_input("Ngày yêu cầu bàn giao")
        trang_thai = c5.selectbox("Trạng thái công việc", ["Mới đặt", "Đang xử lý", "Đã hoàn thành", "Đã hủy"])
        
        st.markdown("---")
        c6, c7, c8 = st.columns(3)
        tong_tien = c6.number_input("Tổng giá trị (VNĐ)", min_value=0, step=1)
        tam_ung = c7.number_input("Đã tạm ứng (VNĐ)", min_value=0, step=1)
        ghi_chu = c8.text_input("Ghi chú thêm")
        
        if st.form_submit_button("Lưu Đơn Đặt Hàng"):
            if not ten_du_an or not nha_thau:
                st.error("⚠️ Vui lòng nhập Tên hạng mục và Đơn vị nhận thầu!")
            else:
                with st.spinner("⏳ Đang lưu dữ liệu..."):
                    con_no = tong_tien - tam_ung
                    new_row = {
                        "Ngày": ngay_dh.strftime('%d/%m/%Y'),
                        "Hạng mục / Dự án": ten_du_an,
                        "Đơn vị nhận thầu": nha_thau,
                        "Nội dung chi tiết": noi_dung,
                        "Ngày bàn giao": ngay_giao.strftime('%d/%m/%Y'),
                        "Tổng tiền": tong_tien,
                        "Tạm ứng": tam_ung,
                        "Còn nợ": con_no,
                        "Trạng thái": trang_thai,
                        "Ghi chú": ghi_chu
                    }
                    append_data(new_row, "wanchi_donhang", df_DonHang)
                st.rerun()

st.subheader("Bảng Theo Dõi Đơn Đặt Hàng")
edited_DonHang = st.data_editor(df_DonHang, num_rows="dynamic", use_container_width=True, key="edit_DH")

if st.button("💾 Cập nhật dữ liệu Bảng"):
    with st.spinner("⏳ Đang đồng bộ..."):
        save_data(edited_DonHang, "wanchi_donhang")
    st.success("✅ Đã cập nhật thành công!")
    st.rerun()
    
st.markdown("---")
st.subheader("📥 Xuất Phiếu Giao Việc / Đặt Hàng")
col_pdf1, col_pdf2 = st.columns([1, 2])

filter_pdf = col_pdf1.selectbox("Chọn dự án để xuất PDF:", ["Tất cả"] + list_du_an)

if st.button("Tạo file PDF (Đơn Đặt Hàng)"):
    with st.spinner("Đang trích xuất file PDF..."):
        df_export = edited_DonHang if filter_pdf == "Tất cả" else edited_DonHang[edited_DonHang["Hạng mục / Dự án"] == filter_pdf]
        title_pdf = f"ĐƠN ĐẶT HÀNG / GIAO VIỆC"
        if filter_pdf != "Tất cả":
            title_pdf += f" - {filter_pdf.upper()}"
        pdf_file = export_pdf(df_export, title_pdf)
    
    file_name = f"WANCHI_DatHang_{filter_pdf}.pdf"
    col_pdf2.download_button("⬇️ Nhấn để Tải PDF Xuống", pdf_file, file_name, "application/pdf")