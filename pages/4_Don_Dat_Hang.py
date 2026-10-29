import streamlit as st
import pandas as pd
import os
import time
from fpdf import FPDF
import unicodedata
from datetime import datetime
from sqlalchemy import text

# --- KHÓA BẢO MẬT TỪ TRANG CHỦ ---
if not st.session_state.get("logged_in", False):
    st.warning("🔒 Bạn chưa đăng nhập! Vui lòng quay lại Trang Chủ (Home) để gõ mật khẩu.")
    st.stop()

# ==========================================
# CẤU HÌNH TRANG & THƯ MỤC HÌNH ẢNH
# ==========================================
st.set_page_config(page_title="Tuấn Quang - Đơn Đặt Hàng & Giao Việc", layout="wide")

try:
    conn = st.connection("postgresql", type="sql")
except Exception as e:
    st.error("Chưa thể kết nối đến cơ sở dữ liệu Neon.")
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
    """Hàm phụ trợ chuyển byte PDF thành byte Ảnh PNG độ nét cao"""
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

# ---> HÀM XUẤT PDF <---
def export_pdf(df, title):
    # Loại bỏ những cột không cần thiết để bảng gọn hơn
    drop_cols = ["Hình ảnh", "Ghi chú"]
    df_table = df.drop(columns=[c for c in drop_cols if c in df.columns], errors="ignore")
    
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    
    try:
        pdf.add_font('ArialVN', '', 'arial.ttf', uni=True)
        pdf.add_font('ArialVN', 'B', 'arialbd.ttf', uni=True)
        font_name = 'ArialVN'
    except:
        font_name = 'Arial'

    logo_path = "logo.png" 
    if os.path.exists(logo_path):
        pdf.image(logo_path, x=10, y=8, w=35)
        start_x = 50 
    else:
        start_x = 10

    pdf.set_xy(start_x, 10)
    pdf.set_font(font_name, 'B' if font_name == 'ArialVN' else '', 14)
    pdf.cell(0, 6, txt="Tuấn Quang", ln=True, align='L')
    pdf.set_x(start_x)
    pdf.set_font(font_name, '', 10)
    pdf.cell(0, 5, txt="Liên hệ: 0937572577", ln=True, align='L')
    pdf.ln(10)

    pdf.set_font(font_name, 'B' if font_name == 'ArialVN' else '', 16)
    pdf.cell(0, 10, txt=title.upper(), ln=True, align='C')
    pdf.set_font(font_name, '', 10)
    pdf.cell(0, 8, txt=f"Ngày xuất: {datetime.now().strftime('%d/%m/%Y')}", ln=True, align='C')
    pdf.ln(5)

    # --- In Bảng Nội Dung ---
    if not df_table.empty:
        num_cols = ["Tổng tiền", "Tạm ứng", "Còn nợ"]
        col_widths = []
        for col in df_table.columns:
            max_w = pdf.get_string_width(str(col)) + 4 
            for item in df_table[col]:
                val_str = str(item)
                if pd.notnull(item) and str(item).strip() != "":
                    if col in num_cols:
                        try:
                            val_str = f"{float(item):,.0f}".replace(",", ".")
                        except: pass
                # Điều chỉnh độ rộng tối đa của các cột văn bản để chữ không bị tràn ngang
                item_w = min(pdf.get_string_width(val_str) + 4, 80) 
                if item_w > max_w:
                    max_w = item_w
            col_widths.append(max_w)
        
        total_w = sum(col_widths)
        if total_w > 0:
            scale = 277 / total_w
            col_widths = [w * scale for w in col_widths]

        pdf.set_font(font_name, 'B' if font_name == 'ArialVN' else '', 8)
        pdf.set_fill_color(220, 220, 220)
        for i, col in enumerate(df_table.columns):
            pdf.cell(col_widths[i], 8, txt=str(col), border=1, fill=True, align='C')
        pdf.ln()
        
        pdf.set_font(font_name, '', 8)
        col_sums = {c: 0.0 for c in df_table.columns}
        
        for _, row in df_table.iterrows():
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
            
        if any(c in df_table.columns for c in num_cols):
            pdf.set_font(font_name, 'B' if font_name == 'ArialVN' else '', 9)
            pdf.set_fill_color(240, 240, 240)
            for i, col in enumerate(df_table.columns):
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
# QUẢN LÝ DỮ LIỆU ĐÁM MÂY (NEON DB)
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
            st.error(f"⚠️ Lỗi xử lý: {str(e2)}")

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
# KHỞI TẠO DỮ LIỆU BẢNG
# ==========================================
cols_DonHang = ["Ngày", "Hạng mục / Dự án", "Đơn vị nhận thầu", "Nội dung chi tiết", "Hình ảnh", "Ngày bàn giao", "Tổng tiền", "Tạm ứng", "Còn nợ", "Trạng thái", "Ghi chú"]
df_DonHang = load_data("wanchi_donhang", cols_DonHang)
df_DonHang = df_DonHang.loc[:, ~df_DonHang.columns.duplicated()]

list_du_an = df_DonHang["Hạng mục / Dự án"].dropna().unique().tolist() if not df_DonHang.empty else []

# ==========================================
# GIAO DIỆN CHÍNH
# ==========================================
st.title("📦 Quản Lý Đơn Đặt Hàng & Giao Việc (Ngoại lai)")
st.markdown("Trang này dùng để quản lý các công việc không có kích thước chuẩn sẵn (Ví dụ: Cắt ván, làm nội thất, sửa chữa xưởng, đặt làm bàn ghế...).")
st.markdown("---")

tab_TaoDon, tab_LichSu = st.tabs(["📝 TẠO ĐƠN ĐẶT HÀNG MỚI", "🗂️ LỊCH SỬ ĐÃ ĐẶT (QUẢN LÝ & XUẤT)"])

# ------------------------------------------
# TAB 1: FORM TẠO ĐƠN
# ------------------------------------------
with tab_TaoDon:
    with st.container(border=True):
        if "dh_form_key" not in st.session_state:
            st.session_state.dh_form_key = 0

        col_title, col_btn = st.columns([3, 1])
        col_title.subheader("Nhập Thông Tin Giao Việc / Đặt Hàng")
        
        if col_btn.button("✨ Làm mới Form (Tạo mới)", use_container_width=True):
            st.session_state.dh_form_key += 1
            if 'new_order_pdf' in st.session_state: del st.session_state['new_order_pdf']
            if 'new_order_png' in st.session_state: del st.session_state['new_order_png']
            st.rerun()
            
        with st.form(f"form_donhang_{st.session_state.dh_form_key}"):
            c1, c2, c3 = st.columns([1, 1.5, 1.5])
            ngay_dh = c1.date_input("Ngày đặt hàng")
            ten_du_an = c2.text_input("Tên Hạng mục / Dự án (VD: Làm tủ điện máy CNC)")
            nha_thau = c3.text_input("Đơn vị nhận thầu / Nhà cung cấp")
            
            st.markdown("---")
            st.markdown("**Nội dung công việc & Kích thước chi tiết:**")
            st.caption("Nhập trực tiếp vào bảng dưới đây. Có thể thêm dòng bằng cách bấm biểu tượng dấu cộng (➕) phía dưới bảng.")
            
            # Bảng nhập liệu đã loại bỏ cột ảnh và STT (Hệ thống sẽ tự động đánh số khi lưu)
            df_nd_init = pd.DataFrame([{"Nội dung công việc": "", "Ghi chú": ""}])
            noi_dung_tb = st.data_editor(
                df_nd_init,
                num_rows="dynamic",
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Nội dung công việc": st.column_config.TextColumn("Nội dung công việc (Kích thước, yêu cầu)", width="large"),
                    "Ghi chú": st.column_config.TextColumn("Ghi chú", width="medium"),
                }
            )
            
            st.markdown("---")
            c4, c5 = st.columns(2)
            ngay_giao = c4.date_input("Ngày yêu cầu bàn giao")
            trang_thai = c5.selectbox("Trạng thái công việc", ["Mới đặt", "Đang xử lý", "Đã hoàn thành", "Đã hủy"])
            
            st.markdown("---")
            c6, c7, c8 = st.columns(3)
            tong_tien = c6.number_input("Tổng giá trị (VNĐ)", min_value=0, step=1)
            tam_ung = c7.number_input("Đã tạm ứng (VNĐ)", min_value=0, step=1)
            ghi_chu = c8.text_input("Ghi chú thanh toán")
            
            if st.form_submit_button("Tạo đơn hàng", type="primary"):
                if not ten_du_an or not nha_thau:
                    st.error("⚠️ Vui lòng nhập Tên hạng mục và Đơn vị nhận thầu!")
                else:
                    with st.spinner("⏳ Đang lưu dữ liệu và xuất phiếu..."):
                        # Trích xuất dữ liệu từ bảng và TỰ ĐỘNG đánh số thứ tự (1, 2, 3...)
                        noi_dung_lines = []
                        stt_counter = 1
                        for _, row in noi_dung_tb.iterrows():
                            if pd.notna(row['Nội dung công việc']) and str(row['Nội dung công việc']).strip() != "":
                                gc_val = f" ({row['Ghi chú']})" if pd.notna(row['Ghi chú']) and str(row['Ghi chú']).strip() else ""
                                noi_dung_lines.append(f"{stt_counter}. {row['Nội dung công việc']}{gc_val}")
                                stt_counter += 1
                        
                        noi_dung_final = "\n".join(noi_dung_lines)

                        con_no = tong_tien - tam_ung
                        new_row = {
                            "Ngày": ngay_dh.strftime('%d/%m/%Y'),
                            "Hạng mục / Dự án": ten_du_an,
                            "Đơn vị nhận thầu": nha_thau,
                            "Nội dung chi tiết": noi_dung_final,
                            "Hình ảnh": "", # Để rỗng
                            "Ngày bàn giao": ngay_giao.strftime('%d/%m/%Y'),
                            "Tổng tiền": tong_tien,
                            "Tạm ứng": tam_ung,
                            "Còn nợ": con_no,
                            "Trạng thái": trang_thai,
                            "Ghi chú": ghi_chu
                        }
                        
                        append_data(new_row, "wanchi_donhang", df_DonHang)
                        
                        # Sinh PDF và PNG tự động sau khi lưu
                        df_new_order = pd.DataFrame([new_row])
                        pdf_bytes = export_pdf(df_new_order, f"ĐƠN ĐẶT HÀNG - {ten_du_an.upper()}")
                        
                        st.session_state['new_order_pdf'] = pdf_bytes
                        st.session_state['new_order_png'] = convert_pdf_to_png(pdf_bytes)
                        st.session_state['new_order_filename'] = f"DonHang_{ten_du_an.replace(' ', '')}"
                        
                    st.session_state.dh_form_key += 1
                    st.rerun()

        # Hiển thị khu vực Tải xuống trực tiếp khi vừa Tạo đơn xong
        if 'new_order_pdf' in st.session_state:
            st.success("🎉 TẠO ĐƠN THÀNH CÔNG! Phiếu giao việc đã sẵn sàng để tải xuống.")
            col_d1, col_d2 = st.columns(2)
            
            if st.session_state.get('new_order_png'):
                col_d1.download_button(
                    label="🖼️ Tải File Ảnh Đơn Hàng (Khuyên dùng)", 
                    data=st.session_state['new_order_png'], 
                    file_name=f"{st.session_state['new_order_filename']}.png", 
                    mime="image/png", 
                    type="primary", 
                    use_container_width=True
                )
                
            col_d2.download_button(
                label="🖨️ Tải File PDF", 
                data=st.session_state['new_order_pdf'], 
                file_name=f"{st.session_state['new_order_filename']}.pdf", 
                mime="application/pdf", 
                use_container_width=True
            )

# ------------------------------------------
# TAB 2: LỊCH SỬ & XUẤT BÁO CÁO
# ------------------------------------------
with tab_LichSu:
    st.subheader("Bảng Dữ Liệu Đơn Hàng (Tự động cập nhật)")
    
    # Ẩn cột đường dẫn hình ảnh cho sạch sẽ
    display_df = df_DonHang.drop(columns=["Hình ảnh"], errors="ignore")
    
    edited_DonHang = st.data_editor(
        display_df, 
        num_rows="dynamic", 
        use_container_width=True, 
        key="edit_DH",
        hide_index=True
    )

    # Hệ thống tự động nhận diện và cập nhật khi dữ liệu trên bảng thay đổi
    if not edited_DonHang.equals(display_df):
        with st.spinner("⏳ Đang đồng bộ cập nhật dữ liệu..."):
            save_data(edited_DonHang, "wanchi_donhang")
        st.success("✅ Hệ thống đã tự động lưu thay đổi!")
        time.sleep(1)
        st.rerun()
        
    st.markdown("---")
    
    # XUẤT FILE CHUYÊN NGHIỆP TỪ LỊCH SỬ
    st.subheader("📥 Xuất Lại Phiếu Giao Việc / Đặt Hàng")
    loai_xuat = st.radio("Định dạng xuất:", ["Chỉ xuất file Ảnh (PNG)", "Chỉ xuất file PDF"], horizontal=True, index=0)
    
    col_pdf1, col_pdf2, col_pdf3 = st.columns([1, 1, 1])
    filter_pdf = col_pdf1.selectbox("Chọn dự án để in:", ["Tất cả"] + list_du_an)

    if col_pdf2.button("Tạo file", use_container_width=True):
        with st.spinner("Đang trích xuất file..."):
            df_export = edited_DonHang if filter_pdf == "Tất cả" else edited_DonHang[edited_DonHang["Hạng mục / Dự án"] == filter_pdf]
            title_pdf = f"ĐƠN ĐẶT HÀNG / GIAO VIỆC"
            if filter_pdf != "Tất cả":
                title_pdf += f" - {filter_pdf.upper()}"
                
            pdf_bytes = export_pdf(df_export, title_pdf)
            file_name = f"TuanQuang_DatHang_{filter_pdf.replace(' ', '')}"
            
            st.session_state['hist_pdf'] = pdf_bytes
            st.session_state['hist_png'] = convert_pdf_to_png(pdf_bytes)
            st.session_state['hist_name'] = file_name
    
    if 'hist_pdf' in st.session_state:
        if "Ảnh" in loai_xuat and st.session_state.get('hist_png'):
            col_pdf3.download_button("🖼️ TẢI XUỐNG ẢNH", st.session_state['hist_png'], f"{st.session_state['hist_name']}.png", "image/png", type="primary", use_container_width=True)
        elif "PDF" in loai_xuat:
            col_pdf3.download_button("🖨️ TẢI XUỐNG PDF", st.session_state['hist_pdf'], f"{st.session_state['hist_name']}.pdf", "application/pdf", type="primary", use_container_width=True)
