import streamlit as st
import pandas as pd
from fpdf import FPDF
import unicodedata
from datetime import datetime
from sqlalchemy import inspect

# ==========================================
# CẤU HÌNH TRANG & KẾT NỐI NEON (POSTGRESQL)
# ==========================================
st.set_page_config(page_title="WANCHI - Quản Lý Khuôn Mẫu", layout="wide")

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

def export_pdf(df, title):
    pdf = FPDF(orientation='L')
    pdf.add_page()
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, txt=f"WANCHI - {remove_accents(title)}", ln=True, align='C')
    pdf.set_font("Arial", size=10)
    pdf.cell(0, 10, txt=f"Ngay xuat: {datetime.now().strftime('%d/%m/%Y')}", ln=True, align='R')
    
    if not df.empty:
        col_width = 277 / len(df.columns)
        pdf.set_fill_color(200, 200, 200)
        for col in df.columns:
            pdf.cell(col_width, 10, txt=remove_accents(str(col)), border=1, fill=True)
        pdf.ln()
        
        sum_tong_tien = 0 
        
        for _, row in df.iterrows():
            for col_name, item in row.items():
                try:
                    if col_name in ["Số lượng", "Đơn giá", "Dọn phôi", "Ráp khuôn hoàn thiện", "Tổng tiền", "Tổng Nguyên Vật Liệu (A)", "Tổng Gia Công (B)", "Tổng Vật Tư (C)", "TỔNG CỘNG"] and pd.notnull(item) and str(item).strip() != "":
                        val = float(item)
                        formatted_item = f"{val:,.0f}"
                        pdf.cell(col_width, 10, txt=remove_accents(formatted_item), border=1)
                        if col_name == "Tổng tiền" or col_name == "TỔNG CỘNG":
                            sum_tong_tien += val
                    else:
                        pdf.cell(col_width, 10, txt=remove_accents(str(item)), border=1)
                except ValueError:
                    pdf.cell(col_width, 10, txt=remove_accents(str(item)), border=1)
            pdf.ln()
            
        if "Tổng tiền" in df.columns or "TỔNG CỘNG" in df.columns:
            pdf.set_font("Arial", "B", 10)
            pdf.set_fill_color(230, 230, 230)
            for i, col in enumerate(df.columns):
                if col == "Tổng tiền" or col == "TỔNG CỘNG":
                    pdf.cell(col_width, 10, txt=f"{sum_tong_tien:,.0f}", border=1, fill=True)
                elif i == len(df.columns) - 2: 
                    pdf.cell(col_width, 10, txt="TONG CONG:", border=1, align='R', fill=True)
                else:
                    pdf.cell(col_width, 10, txt="", border=1, fill=True) 
            pdf.ln()
            
    return bytes(pdf.output())

# Hàm tải dữ liệu từ Neon DB (AN TOÀN - CHỐNG SẬP APP)
def load_data(table_name, columns):
    try:
        # Dò xem bảng đã được tạo trên Neon chưa
        inspector = inspect(conn.engine)
        if not inspector.has_table(table_name):
            return pd.DataFrame(columns=columns)
            
        # Thêm ttl=0 để bỏ qua cache, luôn luôn lấy dữ liệu mới nhất
        df = conn.query(f"SELECT * FROM {table_name}", ttl=0)
        if df.empty:
            return pd.DataFrame(columns=columns)
        return df
    except Exception as e:
        return pd.DataFrame(columns=columns)

# Hàm lưu dữ liệu lên Neon DB (BẮT LỖI)
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
    df_export_a = edited_A if filter_pdf_a == "Tất cả" else edited_A[edited_A["Mã khuôn"] == filter_pdf_a]
    pdf_a = export_pdf(df_export_a, f"BAO CAO NGUYEN VAT LIEU - {filter_pdf_a}")
    col_pdf2.download_button(label="Tải file PDF", data=pdf_a, file_name=f"WANCHI_NVL_{filter_pdf_a}.pdf", mime="application/pdf")

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
    df_export_b = edited_B if filter_pdf_b == "Tất cả" else edited_B[edited_B["Mã khuôn"] == filter_pdf_b]
    pdf_b = export_pdf(df_export_b, f"BAO CAO GIA CONG - {filter_pdf_b}")
    col_pdf4.download_button(label="Tải file PDF", data=pdf_b, file_name=f"WANCHI_GiaCong_{filter_pdf_b}.pdf", mime="application/pdf")

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
    df_export_c = edited_C if filter_pdf_c == "Tất cả" else edited_C[edited_C["Mã khuôn"] == filter_pdf_c]
    pdf_c = export_pdf(df_export_c, f"BAO CAO VAT TU - {filter_pdf_c}")
    col_pdf6.download_button(label="Tải file PDF", data=pdf_c, file_name=f"WANCHI_VatTu_{filter_pdf_c}.pdf", mime="application/pdf")

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
    col_pdf1, col_pdf2 = st.columns([1, 2])
    filter_pdf_d = col_pdf1.selectbox("Chọn Mã khuôn để xuất PDF:", ["Tất cả"] + list_molds_master, key="pdf_d")
    df_export_d = edited_D if filter_pdf_d == "Tất cả" else edited_D[edited_D["Mã khuôn"] == filter_pdf_d]
    pdf_d = export_pdf(df_export_d, f"TONG HOP CHI PHI KHUON - {filter_pdf_d}")
    col_pdf2.download_button(label="Tải file PDF", data=pdf_d, file_name=f"WANCHI_TongHop_{filter_pdf_d}.pdf", mime="application/pdf")
