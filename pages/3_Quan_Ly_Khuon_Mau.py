import streamlit as st
import pandas as pd
# --- KHÓA BẢO MẬT TỪ TRANG CHỦ ---
if not st.session_state.get("logged_in", False):
    st.warning("🔒 Bạn chưa đăng nhập! Vui lòng quay lại Trang Chủ (Home) để gõ mật khẩu.")
    st.stop()
from fpdf import FPDF
import unicodedata
from datetime import datetime
from sqlalchemy import inspect
import os

# ==========================================
# CẤU HÌNH TRANG & KẾT NỐI NEON (POSTGRESQL)
# ==========================================

# Khởi tạo kết nối đến CSDL Neon
try:
    conn = st.connection("postgresql", type="sql")
except Exception as e:
    st.error("Chưa thể kết nối đến cơ sở dữ liệu. Vui lòng kiểm tra lại file cấu hình Secrets.")
    st.stop()

def remove_accents(input_str):
    s = str(input_str).replace('Đ', 'D').replace('đ', 'd')
    nfkd_form = unicodedata.normalize('NFKD', s)
    return u"".join([c for c in nfkd_form if not unicodedata.combining(c)])

# ---> HÀM XUẤT PDF ĐÃ NÂNG CẤP (CÂN CỘT + THÊM LOGO) <---
def export_pdf(df, title):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    
    # Nạp font tiếng Việt
    try:
        pdf.add_font('ArialVN', '', 'arial.ttf', uni=True)
        pdf.add_font('ArialVN', 'B', 'arialbd.ttf', uni=True)
        font_name = 'ArialVN'
    except:
        font_name = 'Arial'
        st.warning("⚠️ Không tìm thấy file 'arial.ttf'. PDF sẽ bị mất dấu tiếng Việt.")

    # 1. THÊM LOGO
    logo_path = "logo.png" # Bắt buộc phải có file logo.png nằm cùng thư mục
    try:
        if os.path.exists(logo_path):
            pdf.image(logo_path, x=10, y=8, w=35)
            start_x = 50 # Đẩy chữ sang phải nhường chỗ cho logo
        else:
            start_x = 10
    except:
        start_x = 10

    # 2. THÔNG TIN CÔNG TY
    pdf.set_xy(start_x, 10)
    pdf.set_font(font_name, 'B' if font_name == 'ArialVN' else '', 14)
    pdf.cell(0, 6, txt="WANCHI", ln=True, align='L')
    
    pdf.set_x(start_x)
    pdf.set_font(font_name, '', 10)
    pdf.cell(0, 5, txt="775 Võ Hữu Lợi, Xã Lê Minh Xuân, Huyện Bình Chánh, TP.HCM", ln=True, align='L')
    
    pdf.set_x(start_x)
    pdf.cell(0, 5, txt="SĐT: 0902.580.828 - 0937.572.577", ln=True, align='L')
    
    pdf.ln(10) # Tạo khoảng trống

    # 3. TIÊU ĐỀ BÁO CÁO
    pdf.set_font(font_name, 'B' if font_name == 'ArialVN' else '', 16)
    pdf.cell(0, 10, txt=title.upper(), ln=True, align='C')
    
    pdf.set_font(font_name, '', 10)
    pdf.cell(0, 8, txt=f"Ngày: {datetime.now().strftime('%d/%m/%Y')}", ln=True, align='C')
    pdf.ln(5)

    # 4. VẼ BẢNG VÀ CÂN CỘT TỰ ĐỘNG
    if not df.empty:
        pdf.set_font(font_name, '', 8) # Đưa font bảng về size 8 để không bị tràn chữ
        
        # Bước 4a: Tính toán độ rộng cần thiết cho từng cột
        col_widths = []
        for col in df.columns:
            max_w = pdf.get_string_width(str(col)) + 4 # Cộng 4mm lề
            for item in df[col]:
                val_str = str(item)
                if pd.notnull(item) and str(item).strip() != "":
                    # Giả lập format số tiền để tính độ rộng chính xác
                    if col in ["Số lượng", "Đơn giá", "Cắt dây", "Xung điện (EDM)", "Phay CNC", "Nhiệt Luyện", "Đánh bóng", "Tạo Nhám hoa văn", "Dọn phôi", "Ráp khuôn hoàn thiện", "Tổng tiền", "Tổng Nguyên Vật Liệu (A)", "Tổng Gia Công (B)", "Tổng Vật Tư (C)", "TỔNG CỘNG"]:
                        try:
                            val_str = f"{float(item):,.0f}".replace(",", ".")
                        except: pass
                item_w = pdf.get_string_width(val_str) + 4
                if item_w > max_w:
                    max_w = item_w
            col_widths.append(max_w)
        
        # Bước 4b: Co giãn tỉ lệ để vừa khít 277mm (Khổ ngang A4 trừ lề)
        total_w = sum(col_widths)
        if total_w > 0:
            scale = 277 / total_w
            col_widths = [w * scale for w in col_widths]

        # Bước 4c: In Header
        pdf.set_font(font_name, 'B' if font_name == 'ArialVN' else '', 8)
        pdf.set_fill_color(220, 220, 220)
        for i, col in enumerate(df.columns):
            header_str = str(col)
            # Ép chữ cắt bớt nếu vẫn dài hơn cột (bảo hiểm chống chồng chữ)
            while pdf.get_string_width(header_str) > col_widths[i] - 1 and len(header_str) > 0:
                header_str = header_str[:-1]
            pdf.cell(col_widths[i], 8, txt=header_str, border=1, fill=True, align='C')
        pdf.ln()
        
        # Bước 4d: In Nội dung
        pdf.set_font(font_name, '', 8)
        sum_tong_tien = 0 
        
        for _, row in df.iterrows():
            for i, (col_name, item) in enumerate(row.items()):
                val_str = str(item) if pd.notnull(item) else ""
                align_col = 'L'
                
                if col_name in ["Số lượng", "Đơn giá", "Cắt dây", "Xung điện (EDM)", "Phay CNC", "Nhiệt Luyện", "Đánh bóng", "Tạo Nhám hoa văn", "Dọn phôi", "Ráp khuôn hoàn thiện", "Tổng tiền", "Tổng Nguyên Vật Liệu (A)", "Tổng Gia Công (B)", "Tổng Vật Tư (C)", "TỔNG CỘNG"] and str(item).strip() != "":
                    try:
                        val = float(item)
                        val_str = f"{val:,.0f}".replace(",", ".")
                        align_col = 'R'
                        if col_name in ["Tổng tiền", "TỔNG CỘNG"]:
                            sum_tong_tien += val
                    except: pass
                
                # Ép chữ cắt bớt nếu vẫn dài hơn cột
                while pdf.get_string_width(val_str) > col_widths[i] - 1 and len(val_str) > 0:
                    val_str = val_str[:-1]

                pdf.cell(col_widths[i], 8, txt=val_str, border=1, align=align_col)
            pdf.ln()
            
        # Bước 4e: Dòng TỔNG CỘNG
        if "Tổng tiền" in df.columns or "TỔNG CỘNG" in df.columns:
            pdf.set_font(font_name, 'B' if font_name == 'ArialVN' else '', 9)
            pdf.set_fill_color(240, 240, 240)
            
            for i, col in enumerate(df.columns):
                if col in ["Tổng tiền", "TỔNG CỘNG"]:
                    tong_str = f"{sum_tong_tien:,.0f}".replace(",", ".")
                    pdf.cell(col_widths[i], 8, txt=tong_str, border=1, fill=True, align='R')
                elif i == len(df.columns) - 2: 
                    pdf.cell(col_widths[i], 8, txt="TỔNG CỘNG:", border=1, fill=True, align='R')
                else:
                    pdf.cell(col_widths[i], 8, txt="", border=1, fill=True) 
            pdf.ln()
            
    # Xử lý file vật lý chống lỗi Crash FPDF
    temp_filename = f"temp_report_{datetime.now().strftime('%H%M%S')}.pdf"
    pdf.output(temp_filename)
    
    with open(temp_filename, "rb") as f:
        pdf_bytes = f.read()
        
    if os.path.exists(temp_filename):
        os.remove(temp_filename)
        
    return pdf_bytes

# Hàm tải dữ liệu từ Neon DB
def load_data(table_name, columns):
    try:
        inspector = inspect(conn.engine)
        if not inspector.has_table(table_name):
            return pd.DataFrame(columns=columns)
            
        df = conn.query(f"SELECT * FROM {table_name}", ttl=0)
        if df.empty:
            return pd.DataFrame(columns=columns)
        return df
    except Exception as e:
        return pd.DataFrame(columns=columns)

# Hàm lưu dữ liệu lên Neon DB
def save_data(df, table_name):
    try:
        df.to_sql(table_name, con=conn.engine, if_exists='replace', index=False)
    except Exception as e:
        st.error(f"⚠️ Lỗi khi lưu dữ liệu lên đám mây ({table_name}): {str(e)}")

# ==========================================
# KHỞI TẠO DỮ LIỆU TỪ DB & XỬ LÝ CỘT
# ==========================================
cols_A = ["Ngày", "Nhà cung cấp NVL", "Mã khuôn", "Tên NVL", "Quy cách", "Số lượng", "Đơn giá", "Tổng tiền"]
df_A = load_data("wanchi_a", cols_A)

cols_B = ["Ngày", "Đơn vị gia công", "Mã khuôn", "Cắt dây", "Xung điện (EDM)", "Phay CNC", "Nhiệt Luyện", "Đánh bóng", "Tạo Nhám hoa văn", "Dọn phôi", "Ráp khuôn hoàn thiện", "Tổng tiền"]
df_B = load_data("wanchi_b", cols_B)

if "Đơn giá" in df_B.columns:
    df_B.rename(columns={"Đơn giá": "Ráp khuôn hoàn thiện"}, inplace=True)
if "Dọn phôi" not in df_B.columns:
    df_B["Dọn phôi"] = 0
df_B = df_B[[c for c in cols_B if c in df_B.columns]]

cols_C = ["Ngày", "Nhà cung cấp vật tư", "Mã khuôn", "Tên linh kiện", "Đơn giá", "Tổng tiền"]
df_C = load_data("wanchi_c", cols_C)

cols_D = ["Ngày", "Mã khuôn", "Tổng Nguyên Vật Liệu (A)", "Tổng Gia Công (B)", "Tổng Vật Tư (C)", "TỔNG CỘNG"]
df_D = load_data("wanchi_d", cols_D)

all_molds_set = set()
if not df_A.empty: all_molds_set.update(df_A["Mã khuôn"].dropna().unique())
if not df_B.empty: all_molds_set.update(df_B["Mã khuôn"].dropna().unique())
if not df_C.empty: all_molds_set.update(df_C["Mã khuôn"].dropna().unique())
if not df_D.empty: all_molds_set.update(df_D["Mã khuôn"].dropna().unique())
list_molds_master = sorted(list(all_molds_set))

# ==========================================
# GIAO DIỆN CHÍNH
# ==========================================
st.title("🏭 Công Cụ Quản Lý Khuôn Mẫu WANCHI")
st.markdown("---")

tab_A, tab_B, tab_C, tab_D = st.tabs([
    "A. Nguyên Vật Liệu", 
    "B. Gia Công", 
    "C. Vật Tư Khuôn Mẫu", 
    "D. Tổng Giá Khuôn"
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
            
            c5, c6, c7, c8 = st.columns(4)
            quy_cach = c5.text_input("Quy cách")
            sl_a = c6.number_input("Số lượng", min_value=0, step=1) 
            don_gia_a = c7.number_input("Đơn giá", min_value=0, step=1000)
            tong_tien_a = c8.number_input("Tổng tiền (Tự nhập)", min_value=0, step=1000)
            
            if st.form_submit_button("Lưu Dữ Liệu NVL"):
                new_row = {"Ngày": ngay_a.strftime('%d/%m/%Y'), "Nhà cung cấp NVL": ncc_a, "Mã khuôn": ma_khuon_a.strip().upper(), 
                           "Tên NVL": ten_nvl, "Quy cách": quy_cach, "Số lượng": sl_a, "Đơn giá": don_gia_a, "Tổng tiền": tong_tien_a}
                df_A = pd.concat([df_A, pd.DataFrame([new_row])], ignore_index=True)
                save_data(df_A, "wanchi_a")
                st.rerun()

    st.subheader("Bảng Dữ Liệu (Cho phép chỉnh sửa/xóa trực tiếp)")
    edited_A = st.data_editor(df_A, num_rows="dynamic", use_container_width=True, key="edit_A")
    if st.button("💾 Cập nhật dữ liệu A (Lên Neon)"):
        save_data(edited_A, "wanchi_a")
        st.success("Đã đồng bộ lên cơ sở dữ liệu!")
        st.rerun()
        
    st.markdown("---")
    st.subheader("📥 Xuất Báo Cáo PDF")
    col_pdf1, col_pdf2 = st.columns([1, 2])
    filter_pdf_a = col_pdf1.selectbox("Chọn Mã khuôn để xuất PDF:", ["Tất cả"] + list_molds_master, key="pdf_a")
    
    if st.button("Tạo file PDF (Module A)"):
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
            cat_day = c4.number_input("Cắt dây", min_value=0, step=1000)
            xung_dien = c5.number_input("Xung điện (EDM)", min_value=0, step=1000)
            phay_cnc = c6.number_input("Phay CNC", min_value=0, step=1000)
            nhiet_luyen = c7.number_input("Nhiệt Luyện", min_value=0, step=1000)
            
            c8, c9, c10, c11 = st.columns(4)
            danh_bong = c8.number_input("Đánh bóng", min_value=0, step=1000)
            nham = c9.number_input("Tạo Nhám hoa văn", min_value=0, step=1000)
            don_phoi = c10.number_input("Dọn phôi", min_value=0, step=1000)
            rap_khuon = c11.number_input("Ráp khuôn hoàn thiện", min_value=0, step=1000)
            
            tong_tien_b = c4.number_input("Tổng tiền (Tự nhập)", min_value=0, step=1000, key="tong_tien_b")
            
            if st.form_submit_button("Lưu Dữ Liệu Gia Công"):
                new_row_b = {"Ngày": ngay_b.strftime('%d/%m/%Y'), "Đơn vị gia công": ncc_b, "Mã khuôn": ma_khuon_b.strip().upper(),
                             "Cắt dây": cat_day, "Xung điện (EDM)": xung_dien, "Phay CNC": phay_cnc, "Nhiệt Luyện": nhiet_luyen,
                             "Đánh bóng": danh_bong, "Tạo Nhám hoa văn": nham, "Dọn phôi": don_phoi, 
                             "Ráp khuôn hoàn thiện": rap_khuon, "Tổng tiền": tong_tien_b}
                df_B = pd.concat([df_B, pd.DataFrame([new_row_b])], ignore_index=True)
                save_data(df_B, "wanchi_b")
                st.rerun()

    st.subheader("Bảng Dữ Liệu Gia Công")
    edited_B = st.data_editor(df_B, num_rows="dynamic", use_container_width=True, key="edit_B")
    if st.button("💾 Cập nhật dữ liệu B (Lên Neon)"):
        save_data(edited_B, "wanchi_b")
        st.success("Đã đồng bộ lên cơ sở dữ liệu!")
        st.rerun()

    st.markdown("---")
    st.subheader("📥 Xuất Báo Cáo PDF")
    col_pdf3, col_pdf4 = st.columns([1, 2])
    filter_pdf_b = col_pdf3.selectbox("Chọn Mã khuôn để xuất PDF:", ["Tất cả"] + list_molds_master, key="pdf_b")
    
    if st.button("Tạo file PDF (Module B)"):
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
            
            c4, c5, c6 = st.columns(3)
            ten_lk = c4.text_input("Tên linh kiện")
            don_gia_c = c5.number_input("Đơn giá", min_value=0, step=1000, key="dg_c")
            tong_tien_c = c6.number_input("Tổng tiền", min_value=0, step=1000, key="tt_c")
            
            if st.form_submit_button("Lưu Dữ Liệu Vật Tư"):
                new_row_c = {"Ngày": ngay_c.strftime('%d/%m/%Y'), "Nhà cung cấp vật tư": ncc_c, "Mã khuôn": ma_khuon_c.strip().upper(),
                             "Tên linh kiện": ten_lk, "Đơn giá": don_gia_c, "Tổng tiền": tong_tien_c}
                df_C = pd.concat([df_C, pd.DataFrame([new_row_c])], ignore_index=True)
                save_data(df_C, "wanchi_c")
                st.rerun()

    st.subheader("Bảng Dữ Liệu Vật Tư")
    edited_C = st.data_editor(df_C, num_rows="dynamic", use_container_width=True, key="edit_C")
    if st.button("💾 Cập nhật dữ liệu C (Lên Neon)"):
        save_data(edited_C, "wanchi_c")
        st.success("Đã đồng bộ lên cơ sở dữ liệu!")
        st.rerun()

    st.markdown("---")
    st.subheader("📥 Xuất Báo Cáo PDF")
    col_pdf5, col_pdf6 = st.columns([1, 2])
    filter_pdf_c = col_pdf5.selectbox("Chọn Mã khuôn để xuất PDF:", ["Tất cả"] + list_molds_master, key="pdf_c")
    
    if st.button("Tạo file PDF (Module C)"):
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
                else:
                    df_D = pd.concat([df_D, pd.DataFrame([new_row_D])], ignore_index=True)
                
                save_data(df_D, "wanchi_d")
                st.success("Đã ghi vào Bảng Tổng và đồng bộ lên DB!")
                st.rerun()

    st.markdown("---")
    st.subheader("Bảng Tổng Hợp Chi Phí")
    edited_D = st.data_editor(df_D, num_rows="dynamic", use_container_width=True, key="edit_D")
    if st.button("💾 Cập nhật bảng Tổng (Lên Neon)"):
        save_data(edited_D, "wanchi_d")
        st.success("Đã lưu các thay đổi!")
        st.rerun()
        
    st.markdown("---")
    st.subheader("📥 Xuất Báo Cáo PDF")
    col_pdf1_d, col_pdf2_d = st.columns([1, 2])
    filter_pdf_d = col_pdf1_d.selectbox("Chọn Mã khuôn để xuất PDF:", ["Tất cả"] + list_molds_master, key="pdf_d")
    
    if st.button("Tạo file PDF (Module D)"):
        df_export_d = edited_D if filter_pdf_d == "Tất cả" else edited_D[edited_D["Mã khuôn"] == filter_pdf_d]
        pdf_d = export_pdf(df_export_d, f"BẢNG TỔNG HỢP CHI PHÍ KHUÔN {filter_pdf_d}")
        col_pdf2_d.download_button("⬇️ Nhấn để Tải PDF Xuống", pdf_d, f"WANCHI_TongHop_{filter_pdf_d}.pdf", "application/pdf")
