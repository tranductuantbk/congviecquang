import streamlit as st
import pandas as pd
from datetime import datetime
import os
from sqlalchemy import text
from fpdf import FPDF
import unicodedata
import json

# --- KHÓA BẢO MẬT TỪ TRANG CHỦ ---
if not st.session_state.get("logged_in", False):
    st.warning("🔒 Bạn chưa đăng nhập! Vui lòng quay lại Trang Chủ (Home) để gõ mật khẩu.")
    st.stop()

st.set_page_config(page_title="Tính Giá Cost & Báo Giá", layout="wide")

# ==========================================
# CẤU HÌNH & KẾT NỐI DB
# ==========================================
try:
    conn = st.connection("postgresql", type="sql")
except Exception as e:
    st.error("Chưa thể kết nối đến cơ sở dữ liệu.")
    st.stop()

def remove_accents(input_str):
    s = str(input_str).replace('Đ', 'D').replace('đ', 'd')
    nfkd_form = unicodedata.normalize('NFKD', s)
    return u"".join([c for c in nfkd_form if not unicodedata.combining(c)])

# ---> HÀM XUẤT PDF BẢNG BÁO GIÁ <---
def export_baogia_pdf(summary_row, df_detail):
    pdf = FPDF(orientation='P', unit='mm', format='A4') # Khổ dọc cho báo giá
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
    if os.path.exists(logo_path):
        pdf.image(logo_path, x=10, y=8, w=35)
        start_x = 50 
    else:
        start_x = 10

    pdf.set_xy(start_x, 10)
    pdf.set_font(font_name, 'B' if font_name == 'ArialVN' else '', 14)
    pdf.cell(0, 6, txt="TUẤN QUANG", ln=True, align='L')
    pdf.set_x(start_x)
    pdf.set_font(font_name, '', 10)
    pdf.cell(0, 5, txt="775 Võ Hữu Lợi, Xã Lê Minh Xuân, Huyện Bình Chánh, TP.HCM", ln=True, align='L')
    pdf.set_x(start_x)
    pdf.cell(0, 5, txt="Liên hệ: 0937572577", ln=True, align='L')
    pdf.ln(10)

    # --- Tiêu đề & Thông tin khách ---
    pdf.set_font(font_name, 'B' if font_name == 'ArialVN' else '', 16)
    pdf.cell(0, 10, txt="BẢNG TÍNH GIÁ COST & ĐỀ XUẤT BÁO GIÁ", ln=True, align='C')
    pdf.ln(5)
    
    pdf.set_font(font_name, '', 11)
    pdf.cell(0, 6, txt=f"Ngày báo giá: {summary_row['Ngày']}", ln=True)
    pdf.cell(0, 6, txt=f"Dự án / Sản phẩm: {summary_row['Sản phẩm / Dự án']}", ln=True)
    pdf.cell(0, 6, txt=f"Khách hàng: {summary_row['Khách hàng']}", ln=True)
    pdf.cell(0, 6, txt=f"Số lượng sản xuất (Lô): {summary_row['SL Lô']} Đơn vị", ln=True)
    pdf.ln(5)

    # --- Bảng Chi Tiết BOM ---
    if not df_detail.empty:
        pdf.set_font(font_name, 'B' if font_name == 'ArialVN' else '', 10)
        pdf.cell(0, 8, txt="I. CHI TIẾT ĐỊNH MỨC (GIÁ VỐN):", ln=True)
        
        pdf.set_font(font_name, 'B' if font_name == 'ArialVN' else '', 8)
        col_widths = [35, 60, 15, 20, 30, 30] # Tổng 190mm vừa vặn A4 dọc
        headers = ["Nhóm chi phí", "Tên hạng mục", "ĐVT", "Số lượng", "Đơn giá", "Thành tiền"]
        
        pdf.set_fill_color(220, 220, 220)
        for i, header in enumerate(headers):
            pdf.cell(col_widths[i], 8, txt=header, border=1, fill=True, align='C')
        pdf.ln()
        
        pdf.set_font(font_name, '', 8)
        for _, row in df_detail.iterrows():
            row_vals = [
                str(row.get("Nhóm chi phí", "")),
                str(row.get("Tên hạng mục", "")),
                str(row.get("Đơn vị", "")),
                f"{float(row.get('Số lượng / Thời gian', 0)):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if row.get("Số lượng / Thời gian") else "",
                f"{float(row.get('Đơn giá cost', 0)):,.0f}".replace(",", ".") if row.get("Đơn giá cost") else "",
                f"{float(row.get('Tổng cộng', 0)):,.0f}".replace(",", ".") if row.get("Tổng cộng") else ""
            ]
            aligns = ['L', 'L', 'C', 'R', 'R', 'R']
            
            # Xử lý xuống dòng cho cột Tên hạng mục
            line_height = 5
            est_w = pdf.get_string_width(row_vals[1])
            lines = int(est_w / (col_widths[1] - 2)) + 1
            row_height = lines * line_height
            
            x_start = pdf.get_x()
            y_start = pdf.get_y()
            for i, val in enumerate(row_vals):
                pdf.set_xy(x_start, y_start)
                pdf.multi_cell(col_widths[i], line_height, txt=val, border=0, align=aligns[i])
                pdf.set_xy(x_start, y_start)
                pdf.cell(col_widths[i], row_height, border=1)
                x_start += col_widths[i]
            pdf.set_y(y_start + row_height)

    # --- Phần Tổng Kết Chốt Giá ---
    pdf.ln(10)
    pdf.set_font(font_name, 'B' if font_name == 'ArialVN' else '', 10)
    pdf.cell(0, 8, txt="II. TỔNG KẾT BÁO GIÁ:", ln=True)
    
    pdf.set_font(font_name, '', 10)
    pdf.cell(90, 8, txt="Tổng chi phí gốc (Cost):", border=1)
    pdf.cell(100, 8, txt=f"{float(summary_row['Tổng giá vốn']):,.0f} VNĐ".replace(",", "."), border=1, align='R', ln=True)
    
    pdf.cell(90, 8, txt=f"Tỷ lệ hao hụt dự phòng ({summary_row['Hao hụt (%)']}%):", border=1)
    hao_hut_val = float(summary_row['Tổng giá vốn']) * (float(summary_row['Hao hụt (%)']) / 100)
    pdf.cell(100, 8, txt=f"{hao_hut_val:,.0f} VNĐ".replace(",", "."), border=1, align='R', ln=True)
    
    pdf.cell(90, 8, txt=f"Biên lợi nhuận kỳ vọng ({summary_row['Lợi nhuận (%)']}%):", border=1)
    loi_nhuan_val = (float(summary_row['Tổng giá vốn']) + hao_hut_val) * (float(summary_row['Lợi nhuận (%)']) / 100)
    pdf.cell(100, 8, txt=f"{loi_nhuan_val:,.0f} VNĐ".replace(",", "."), border=1, align='R', ln=True)
    
    pdf.set_font(font_name, 'B' if font_name == 'ArialVN' else '', 11)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(90, 10, txt="TỔNG GIÁ BÁN (CHO CẢ LÔ):", border=1, fill=True)
    pdf.cell(100, 10, txt=f"{float(summary_row['Tổng giá bán']):,.0f} VNĐ".replace(",", "."), border=1, fill=True, align='R', ln=True)
    
    pdf.set_fill_color(210, 250, 210)
    pdf.cell(90, 10, txt="ĐƠN GIÁ ĐỀ XUẤT CHO 1 SẢN PHẨM:", border=1, fill=True)
    pdf.cell(100, 10, txt=f"{float(summary_row['Giá bán 1 SP']):,.0f} VNĐ".replace(",", "."), border=1, fill=True, align='R', ln=True)

    temp_filename = f"temp_baogia_{datetime.now().strftime('%H%M%S')}.pdf"
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

# Tải dữ liệu Bảng Lịch sử Báo giá
cols_BaoGia = ["Ngày", "Sản phẩm / Dự án", "Khách hàng", "SL Lô", "Tổng giá vốn", "Hao hụt (%)", "Lợi nhuận (%)", "Giá bán 1 SP", "Tổng giá bán", "Chi tiết BOM"]
df_BaoGia = load_data("wanchi_baogia", cols_BaoGia)
df_BaoGia = df_BaoGia.loc[:, ~df_BaoGia.columns.duplicated()]

if "costing_items" not in st.session_state:
    st.session_state.costing_items = pd.DataFrame(columns=[
        "Nhóm chi phí", "Tên hạng mục", "Đơn vị", "Số lượng / Thời gian", "Đơn giá cost", "Tổng cộng"
    ])

# ==========================================
# GIAO DIỆN CHÍNH
# ==========================================
st.title("🧮 Hệ Thống Tính Giá Cost & Lịch Sử Báo Giá")
st.markdown("---")

tab_TinhGia, tab_LichSu = st.tabs(["🧮 TÍNH GIÁ COST MỚI", "🗂️ LỊCH SỬ ĐÃ BÁO GIÁ"])

# ------------------------------------------
# TAB 1: TÍNH GIÁ COST
# ------------------------------------------
with tab_TinhGia:
    col_info1, col_info2, col_info3 = st.columns(3)
    ten_sp = col_info1.text_input("Tên Sản phẩm / Tên dự án cần tính giá:")
    khach_hang = col_info2.text_input("Tên Khách hàng (Nếu có):")
    so_luong_lo = col_info3.number_input("Số lượng sản xuất (Cái/Bộ):", min_value=1, value=1, step=1, 
                                         help="Rất quan trọng để chia đều chi phí ra đơn giá 1 sản phẩm.")

    st.markdown("---")
    st.subheader("1. Bảng Khai Báo Chi Phí (Giá Vốn)")
    st.info("💡 Hướng dẫn: Cuộn xuống cuối bảng, bấm dấu '+' để thêm dòng mới. Bạn có thể tự do gõ tên Vật liệu hoặc Tên máy móc.")

    edited_cost_df = st.data_editor(
        st.session_state.costing_items,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Nhóm chi phí": st.column_config.SelectboxColumn(
                "Nhóm chi phí",
                options=[
                    "1. Nguyên vật liệu", 
                    "2. Giờ chạy máy (Khấu hao)", 
                    "3. Nhân công trực tiếp", 
                    "4. Thuê gia công ngoài", 
                    "5. Chi phí khác (Đóng gói, Vận chuyển)"
                ],
                required=True
            ),
            "Tên hạng mục": st.column_config.TextColumn("Tên hạng mục (VD: Thép SKD11, Máy Phay, Thợ hàn...)", required=True),
            "Đơn vị": st.column_config.TextColumn("ĐVT (kg, giờ, cái...)"),
            "Số lượng / Thời gian": st.column_config.NumberColumn("Số lượng / Thời gian", min_value=0.0, format="%.2f"),
            "Đơn giá cost": st.column_config.NumberColumn("Đơn giá (VNĐ)", min_value=0, step=1000, format="%d"),
            "Tổng cộng": st.column_config.NumberColumn("Thành tiền (VNĐ)", disabled=True)
        },
        key="costing_editor"
    )

    tong_chi_phi_goc = 0
    if not edited_cost_df.empty:
        edited_cost_df["Số lượng / Thời gian"] = pd.to_numeric(edited_cost_df["Số lượng / Thời gian"], errors="coerce").fillna(0)
        edited_cost_df["Đơn giá cost"] = pd.to_numeric(edited_cost_df["Đơn giá cost"], errors="coerce").fillna(0)
        edited_cost_df["Tổng cộng"] = edited_cost_df["Số lượng / Thời gian"] * edited_cost_df["Đơn giá cost"]
        tong_chi_phi_goc = edited_cost_df["Tổng cộng"].sum()

    st.markdown("---")
    st.subheader("2. Chốt Giá & Lợi Nhuận")

    col_sum1, col_sum2 = st.columns([1, 1.5])

    with col_sum1:
        with st.container(border=True):
            st.markdown(f"### Tổng Chi Phí Gốc: **{tong_chi_phi_goc:,.0f} VNĐ**")
            hao_hut = st.slider("Tỷ lệ hao hụt / Rủi ro (%)", 0, 30, 5)
            loi_nhuan = st.slider("Biên lợi nhuận mong muốn (%)", 0, 100, 20)
            
            chi_phi_hao_hut = tong_chi_phi_goc * (hao_hut / 100)
            gia_von_cuoi_cung = tong_chi_phi_goc + chi_phi_hao_hut
            tien_loi = gia_von_cuoi_cung * (loi_nhuan / 100)
            tong_gia_ban_lo = gia_von_cuoi_cung + tien_loi
            gia_ban_1_cai = tong_gia_ban_lo / so_luong_lo if so_luong_lo > 0 else 0

    with col_sum2:
        with st.container(border=True):
            st.success("📊 KẾT QUẢ ĐỀ XUẤT BÁO GIÁ")
            st.markdown(f"""
            * Tổng giá vốn thực tế (Đã kèm {hao_hut}% hao hụt): **{gia_von_cuoi_cung:,.0f} VNĐ**
            * Lợi nhuận kỳ vọng ({loi_nhuan}%): **{tien_loi:,.0f} VNĐ**
            """)
            st.markdown("#### TỔNG BÁO GIÁ CHO LÔ HÀNG:")
            st.markdown(f"<h2 style='color: #E63946;'>{tong_gia_ban_lo:,.0f} VNĐ</h2>", unsafe_allow_html=True)
            st.markdown("#### ĐƠN GIÁ TRÊN 1 SẢN PHẨM:")
            st.markdown(f"<h3 style='color: #2A9D8F;'>{gia_ban_1_cai:,.0f} VNĐ / Đơn vị</h3>", unsafe_allow_html=True)

    st.markdown("---")
    col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 2])
    
    if col_btn1.button("💾 Lưu Lịch Sử Báo Giá"):
        if not ten_sp:
            st.error("⚠️ Vui lòng nhập tên Sản phẩm / Dự án trước khi lưu!")
        elif tong_chi_phi_goc == 0:
            st.error("⚠️ Bảng chi phí đang trống. Vui lòng nhập ít nhất 1 chi phí!")
        else:
            with st.spinner("Đang lưu lịch sử..."):
                bom_json = edited_cost_df.to_json(orient='records')
                new_quote = {
                    "Ngày": datetime.today().strftime('%d/%m/%Y'),
                    "Sản phẩm / Dự án": ten_sp,
                    "Khách hàng": khach_hang,
                    "SL Lô": so_luong_lo,
                    "Tổng giá vốn": gia_von_cuoi_cung,
                    "Hao hụt (%)": hao_hut,
                    "Lợi nhuận (%)": loi_nhuan,
                    "Giá bán 1 SP": gia_ban_1_cai,
                    "Tổng giá bán": tong_gia_ban_lo,
                    "Chi tiết BOM": bom_json # Đóng gói bảng chi tiết vào 1 ô JSON
                }
                append_data(new_quote, "wanchi_baogia", df_BaoGia)
            st.success("✅ Đã lưu vào Lịch sử thành công! (Chuyển sang Tab Lịch Sử để xem)")
            st.rerun()
            
    if col_btn2.button("✨ Làm mới Form Nhập"):
        st.session_state.costing_items = pd.DataFrame(columns=[
            "Nhóm chi phí", "Tên hạng mục", "Đơn vị", "Số lượng / Thời gian", "Đơn giá cost", "Tổng cộng"
        ])
        st.rerun()

# ------------------------------------------
# TAB 2: LỊCH SỬ BÁO GIÁ & XUẤT PDF
# ------------------------------------------
with tab_LichSu:
    st.subheader("Bảng Tóm Tắt Các Dự Án Đã Tính Giá")
    
    # Sử dụng column_config để ẩn cột JSON dài dòng nhưng vẫn giữ data khi sửa
    edited_BaoGia = st.data_editor(
        df_BaoGia,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Chi tiết BOM": None, # Ẩn cột chứa cấu trúc chi tiết
            "Tổng giá vốn": st.column_config.NumberColumn(format="%d"),
            "Giá bán 1 SP": st.column_config.NumberColumn(format="%d"),
            "Tổng giá bán": st.column_config.NumberColumn(format="%d")
        },
        key="edit_bg"
    )

    if st.button("💾 Cập nhật thay đổi Lịch Sử"):
        with st.spinner("Đang đồng bộ..."):
            save_data(edited_BaoGia, "wanchi_baogia")
        st.success("✅ Đã cập nhật thành công!")
        st.rerun()

    st.markdown("---")
    st.subheader("🔍 Truy Xuất Chi Tiết & In Báo Giá PDF")
    
    list_du_an = df_BaoGia["Sản phẩm / Dự án"].dropna().unique().tolist() if not df_BaoGia.empty else []
    chon_bg = st.selectbox("Chọn dự án để xem lại Chi tiết / Xuất PDF:", ["(Vui lòng chọn)"] + list_du_an)
    
    if chon_bg != "(Vui lòng chọn)":
        row_info = df_BaoGia[df_BaoGia["Sản phẩm / Dự án"] == chon_bg].iloc[0]
        
        c_thongtin, c_pdf = st.columns([2, 1])
        c_thongtin.markdown(f"**Khách hàng:** {row_info.get('Khách hàng', '')} | **Đơn giá 1 SP:** {float(row_info['Giá bán 1 SP']):,.0f} VNĐ")
        
        try:
            # Giải nén chuỗi JSON để hiển thị lại bảng chi phí
            df_chitiet = pd.read_json(row_info["Chi tiết BOM"])
            st.dataframe(df_chitiet, use_container_width=True)
            
            # Tính năng tải PDF Báo Giá
            if c_pdf.button(f"📄 Tạo file PDF Báo Giá cho {chon_bg}"):
                with st.spinner("Đang trích xuất..."):
                    pdf_file = export_baogia_pdf(row_info, df_chitiet)
                file_name = f"TuanQuang_BaoGia_{chon_bg}.pdf"
                c_pdf.download_button("⬇️ TẢI PDF XUỐNG", pdf_file, file_name, "application/pdf")
                
        except Exception as e:
            st.error("Lỗi khi đọc dữ liệu chi tiết của dự án này.")
