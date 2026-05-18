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
# CẤU HÌNH TRANG & THƯ MỤC HÌNH ẢNH
# ==========================================
st.set_page_config(page_title="Tuấn Quang - Đơn Đặt Hàng & Giao Việc", layout="wide")

# Tự động tạo thư mục lưu trữ ảnh trên máy chủ nếu chưa có
IMG_DIR = "attached_images"
if not os.path.exists(IMG_DIR):
    os.makedirs(IMG_DIR)

try:
    conn = st.connection("postgresql", type="sql")
except Exception as e:
    st.error("Chưa thể kết nối đến cơ sở dữ liệu Neon.")
    st.stop()

def remove_accents(input_str):
    s = str(input_str).replace('Đ', 'D').replace('đ', 'd')
    nfkd_form = unicodedata.normalize('NFKD', s)
    return u"".join([c for c in nfkd_form if not unicodedata.combining(c)])

# ---> HÀM XUẤT PDF CÓ TÍCH HỢP HÌNH ẢNH BẢN VẼ <---
def export_pdf(df, title):
    # Tách cột hình ảnh ra để không in vào trong bảng chữ
    image_paths = df["Hình ảnh"].tolist() if "Hình ảnh" in df.columns else []
    df_table = df.drop(columns=["Hình ảnh"], errors="ignore")
    
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    
    try:
        pdf.add_font('ArialVN', '', 'arial.ttf', uni=True)
        pdf.add_font('ArialVN', 'B', 'arialbd.ttf', uni=True)
        font_name = 'ArialVN'
    except:
        font_name = 'Arial'
        st.warning("⚠️ Không tìm thấy file 'arial.ttf'. PDF sẽ bị mất dấu tiếng Việt.")

    # --- Header Phiếu ---
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
                # Giới hạn bề ngang cột nội dung để ép xuống dòng
                item_w = min(pdf.get_string_width(val_str) + 4, 65) 
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
            
        # In tổng cộng
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
            
    # --- In Trang Hình Ảnh Đính Kèm (Nếu có) ---
    for img_path in image_paths:
        if pd.notnull(img_path) and str(img_path).strip() != "" and os.path.exists(str(img_path)):
            pdf.add_page() # Tự động tạo trang mới chuyên chứa ảnh
            pdf.set_font(font_name, 'B' if font_name == 'ArialVN' else '', 12)
            pdf.cell(0, 10, txt="PHỤ LỤC: HÌNH ẢNH / BẢN VẼ MÔ TẢ KỸ THUẬT", ln=True, align='L')
            try:
                # Căn chỉnh ảnh chiếm tỷ lệ lớn vừa phải ở giữa trang
                pdf.image(str(img_path), x=20, y=30, w=250)
            except:
                pdf.cell(0, 10, txt="(Ảnh bị lỗi hoặc định dạng không hỗ trợ để chèn vào PDF)", ln=True, align='L')

    # Xử lý lưu file PDF
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
    # Tự động bổ sung cột nếu Data cũ bị thiếu
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
        # Nếu cột bị lệch, tự động ghi đè để cấu trúc lại bảng
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
# KHỞI TẠO DỮ LIỆU BẢNG (wanchi_donhang)
# ==========================================
cols_DonHang = ["Ngày", "Hạng mục / Dự án", "Đơn vị nhận thầu", "Nội dung chi tiết", "Hình ảnh", "Ngày bàn giao", "Tổng tiền", "Tạm ứng", "Còn nợ", "Trạng thái", "Ghi chú"]
df_DonHang = load_data("wanchi_donhang", cols_DonHang)
df_DonHang = df_DonHang.loc[:, ~df_DonHang.columns.duplicated()]

list_du_an = df_DonHang["Hạng mục / Dự án"].dropna().unique().tolist() if not df_DonHang.empty else []


# ==========================================
# GIAO DIỆN CHÍNH (ĐƯỢC CHIA LÀM 2 TAB)
# ==========================================
st.title("📦 Quản Lý Đơn Đặt Hàng & Giao Việc (Ngoại lai)")
st.markdown("Trang này dùng để quản lý các công việc không có kích thước chuẩn sẵn (Ví dụ: Cắt ván, làm nội thất, sửa chữa xưởng, đặt làm bàn ghế...).")
st.markdown("---")

tab_TaoDon, tab_LichSu = st.tabs(["📝 TẠO ĐƠN ĐẶT HÀNG MỚI", "🗂️ LỊCH SỬ ĐÃ ĐẶT (QUẢN LÝ & XUẤT PDF)"])

# ------------------------------------------
# TAB 1: FORM TẠO ĐƠN & TẢI ẢNH
# ------------------------------------------
with tab_TaoDon:
    with st.container(border=True):
        # Biến đếm dùng để làm mới Form tự động
        if "dh_form_key" not in st.session_state:
            st.session_state.dh_form_key = 0

        col_title, col_btn = st.columns([3, 1])
        col_title.subheader("Nhập Thông Tin Giao Việc / Đặt Hàng")
        
        # NÚT XÓA TRẮNG FORM
        if col_btn.button("✨ Tạo Đơn Mới (Xóa Trắng Form)", use_container_width=True):
            st.session_state.dh_form_key += 1
            st.rerun()
            
        with st.form(f"form_donhang_{st.session_state.dh_form_key}"):
            c1, c2, c3 = st.columns([1, 1.5, 1.5])
            ngay_dh = c1.date_input("Ngày đặt hàng")
            ten_du_an = c2.text_input("Tên Hạng mục / Dự án (VD: Làm tủ điện máy CNC)")
            nha_thau = c3.text_input("Đơn vị nhận thầu / Nhà cung cấp")
            
            st.markdown("---")
            col_text, col_img = st.columns([2, 1])
            
            with col_text:
                st.markdown("**Nội dung công việc & Kích thước chi tiết:**")
                st.caption("Nhấn phím Enter để xuống dòng liệt kê chi tiết yêu cầu, kích thước...")
                noi_dung = st.text_area("", height=150, placeholder="- Ván ép 10mm: 2 tấm 1m x 2m\n- Bo tròn 4 góc, chà nhám mịn mặt trên.")
                
            with col_img:
                st.markdown("**Đính kèm bản vẽ / Hình ảnh (NẾU CÓ):**")
                file_anh = st.file_uploader("🖼️ Hỗ trợ định dạng: png, jpg, jpeg", type=["png", "jpg", "jpeg"])
            
            st.markdown("---")
            c4, c5 = st.columns(2)
            ngay_giao = c4.date_input("Ngày yêu cầu bàn giao")
            trang_thai = c5.selectbox("Trạng thái công việc", ["Mới đặt", "Đang xử lý", "Đã hoàn thành", "Đã hủy"])
            
            st.markdown("---")
            c6, c7, c8 = st.columns(3)
            tong_tien = c6.number_input("Tổng giá trị (VNĐ)", min_value=0, step=1)
            tam_ung = c7.number_input("Đã tạm ứng (VNĐ)", min_value=0, step=1)
            ghi_chu = c8.text_input("Ghi chú thanh toán")
            
            if st.form_submit_button("Lưu Đơn Đặt Hàng Mới"):
                if not ten_du_an or not nha_thau:
                    st.error("⚠️ Vui lòng nhập Tên hạng mục và Đơn vị nhận thầu!")
                else:
                    with st.spinner("⏳ Đang lưu dữ liệu và xử lý hình ảnh..."):
                        
                        # Xử lý lưu ảnh nếu có upload
                        img_path_saved = ""
                        if file_anh is not None:
                            img_name = f"IMG_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file_anh.name}"
                            img_path_saved = os.path.join(IMG_DIR, img_name)
                            with open(img_path_saved, "wb") as f:
                                f.write(file_anh.getbuffer())

                        con_no = tong_tien - tam_ung
                        new_row = {
                            "Ngày": ngay_dh.strftime('%d/%m/%Y'),
                            "Hạng mục / Dự án": ten_du_an,
                            "Đơn vị nhận thầu": nha_thau,
                            "Nội dung chi tiết": noi_dung,
                            "Hình ảnh": img_path_saved,
                            "Ngày bàn giao": ngay_giao.strftime('%d/%m/%Y'),
                            "Tổng tiền": tong_tien,
                            "Tạm ứng": tam_ung,
                            "Còn nợ": con_no,
                            "Trạng thái": trang_thai,
                            "Ghi chú": ghi_chu
                        }
                        append_data(new_row, "wanchi_donhang", df_DonHang)
                    
                    # Tự động làm sạch form sau khi lưu thành công
                    st.session_state.dh_form_key += 1
                    st.success("✅ Đã tạo đơn thành công! (Form đã được làm sạch để nhập đơn mới).")
                    st.rerun()

# ------------------------------------------
# TAB 2: LỊCH SỬ, TRÌNH CHIẾU ẢNH & PDF
# ------------------------------------------
with tab_LichSu:
    st.subheader("Bảng Dữ Liệu Đơn Hàng (Cho phép sửa trực tiếp)")
    
    # Ẩn cột đường dẫn hình ảnh cho bảng đỡ rối, giữ lại các cột thông tin
    display_df = df_DonHang.copy()
    
    edited_DonHang = st.data_editor(
        display_df, 
        num_rows="dynamic", 
        use_container_width=True, 
        key="edit_DH",
        column_config={
            "Hình ảnh": st.column_config.TextColumn("🖼️ File Đính Kèm", disabled=True)
        }
    )

    if st.button("💾 Cập nhật dữ liệu Bảng"):
        with st.spinner("⏳ Đang đồng bộ cập nhật..."):
            save_data(edited_DonHang, "wanchi_donhang")
        st.success("✅ Đã cập nhật thành công!")
        st.rerun()
        
    st.markdown("---")
    
    # KÊNH TRÌNH CHIẾU ẢNH
    st.subheader("🖼️ Trình Chiếu Hình Ảnh Bản Vẽ")
    df_co_anh = df_DonHang[df_DonHang["Hình ảnh"].notnull() & (df_DonHang["Hình ảnh"] != "")]
    
    if not df_co_anh.empty:
        chon_don_xem_anh = st.selectbox("Chọn dự án để xem ảnh / bản vẽ đính kèm:", df_co_anh["Hạng mục / Dự án"].unique())
        anh_can_xem = df_co_anh[df_co_anh["Hạng mục / Dự án"] == chon_don_xem_anh]["Hình ảnh"].iloc[0]
        
        if os.path.exists(anh_can_xem):
            # Căn giữa và thu nhỏ ảnh hiển thị cho đẹp
            col_z1, col_z2, col_z3 = st.columns([1, 2, 1])
            col_z2.image(anh_can_xem, caption=f"Mô tả của: {chon_don_xem_anh}", use_container_width=True)
        else:
            st.warning("⚠️ Không tìm thấy file ảnh gốc trên hệ thống (có thể đã bị xóa).")
    else:
        st.info("💡 Chưa có đơn hàng nào trong hệ thống được đính kèm hình ảnh.")

    st.markdown("---")
    
    # XUẤT PDF CHUYÊN NGHIỆP
    st.subheader("📥 Xuất Phiếu Giao Việc / Đặt Hàng (Kèm Bản Vẽ)")
    col_pdf1, col_pdf2 = st.columns([1, 2])

    filter_pdf = col_pdf1.selectbox("Chọn dự án để in PDF:", ["Tất cả"] + list_du_an)

    if st.button("Tạo file PDF"):
        with st.spinner("Đang trích xuất file PDF (Đang ghép ảnh vào nếu có)..."):
            df_export = edited_DonHang if filter_pdf == "Tất cả" else edited_DonHang[edited_DonHang["Hạng mục / Dự án"] == filter_pdf]
            title_pdf = f"ĐƠN ĐẶT HÀNG / GIAO VIỆC"
            if filter_pdf != "Tất cả":
                title_pdf += f" - {filter_pdf.upper()}"
                
            pdf_file = export_pdf(df_export, title_pdf)
        
        file_name = f"TuanQuang_DatHang_{filter_pdf}.pdf"
        col_pdf2.download_button("⬇️ Nhấn để Tải PDF Xuống", pdf_file, file_name, "application/pdf")
