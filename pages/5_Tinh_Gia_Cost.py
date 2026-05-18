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

st.set_page_config(page_title="Phân Tích Giá Cost & Lợi Nhuận", layout="wide")

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

# ==========================================
# BỘ TỪ ĐIỂN TEMPLATE CÁC NGÀNH NGHỀ
# ==========================================
TEMPLATES = {
    "1. F&B (Đồ ăn / Thức uống)": [
        "Nguyên vật liệu chính (Cà phê, Trà, Thịt...)",
        "Gia vị / Vật liệu phụ",
        "Bao bì (Ly, Hộp, Túi nilon, Muỗng)",
        "Nhân công trực tiếp (Pha chế, Bếp)",
        "Chi phí vận hành (Điện, Nước, Gas)",
        "Phân bổ mặt bằng / Quản lý",
        "Hao hụt / Bỏ mứa / Hư hỏng"
    ],
    "2. Thi công Nội thất / Mộc": [
        "Gỗ / Ván công nghiệp / Phôi chính",
        "Phụ kiện (Bản lề, Ray, Tay nắm...)",
        "Vật tư phụ (Keo, Đinh, Nhám, Sơn...)",
        "Nhân công sản xuất (Thợ xưởng)",
        "Nhân công lắp đặt (Tại công trình)",
        "Khấu hao máy móc / Giờ chạy máy",
        "Chi phí Vận chuyển / Bốc vác",
        "Rủi ro bảo hành / Hao hụt ván"
    ],
    "3. Xây dựng / Công trình": [
        "Vật tư thô (Cát, Đá, Xi măng, Thép...)",
        "Vật tư hoàn thiện (Gạch, Sơn, Điện nước...)",
        "Nhân công (Khoán / Thợ xây / Thợ phụ)",
        "Ca máy / Thuê thiết bị (Múc, Trộn, Cẩu...)",
        "Vận chuyển / Đổ xà bần",
        "Quản lý dự án / Kỹ thuật hiện trường",
        "Rủi ro trượt giá vật tư / Hao hụt"
    ],
    "4. Gia công Khuôn mẫu / Cơ khí": [
        "Phôi thép / Nguyên liệu chính",
        "Linh kiện chuẩn (Chốt, Lò xo, Ốc...)",
        "Giờ chạy máy (Phay CNC, Cắt dây, Xung...)",
        "Nhân công (Lắp ráp, Đánh bóng, Nguội)",
        "Xử lý bề mặt (Nhiệt luyện, Xi mạ)",
        "Chi phí vận chuyển / Giao nhận",
        "Hao hụt phôi / Mòn dao cụ"
    ],
    "5. Đa dụng (Cơ bản)": [
        "Nguyên vật liệu",
        "Chi phí Nhân công",
        "Máy móc & Thiết bị",
        "Thuê ngoài / Dịch vụ",
        "Chi phí chung & Quản lý",
        "Hao hụt / Rủi ro"
    ]
}

# Khởi tạo trạng thái ban đầu
if "cost_template" not in st.session_state:
    st.session_state.cost_template = "5. Đa dụng (Cơ bản)"
    
if "cost_items" not in st.session_state:
    st.session_state.cost_items = pd.DataFrame(columns=[
        "Nhóm chi phí", "Tên chi tiết", "Đơn vị", "Định mức", "Đơn giá", "Thành tiền"
    ])

def tao_bang_mau_theo_nganh(ten_nganh):
    ds_nhom = TEMPLATES[ten_nganh]
    du_lieu_moi = []
    for nhom in ds_nhom:
        du_lieu_moi.append({
            "Nhóm chi phí": nhom,
            "Tên chi tiết": "",
            "Đơn vị": "",
            "Định mức": 0.0,
            "Đơn giá": 0,
            "Thành tiền": 0
        })
    st.session_state.cost_items = pd.DataFrame(du_lieu_moi)
    st.session_state.cost_template = ten_nganh

# ---> HÀM XUẤT PDF PHIẾU PHÂN TÍCH NỘI BỘ <---
def export_internal_analysis_pdf(summary_row, df_detail):
    pdf = FPDF(orientation='P', unit='mm', format='A4') 
    pdf.add_page()
    
    try:
        pdf.add_font('ArialVN', '', 'arial.ttf', uni=True)
        pdf.add_font('ArialVN', 'B', 'arialbd.ttf', uni=True)
        font_name = 'ArialVN'
    except:
        font_name = 'Arial'
        st.warning("⚠️ Không tìm thấy file 'arial.ttf'. PDF sẽ bị mất dấu tiếng Việt.")

    # --- Header Nội Bộ ---
    pdf.set_xy(10, 10)
    pdf.set_font(font_name, 'B', 14)
    pdf.cell(0, 6, txt="TUẤN QUANG", ln=True, align='L')
    pdf.set_font(font_name, '', 10)
    pdf.cell(0, 5, txt="Liên hệ: 0937572577", ln=True, align='L')
    pdf.ln(10)

    # --- Tiêu đề ---
    pdf.set_font(font_name, 'B', 16)
    pdf.cell(0, 10, txt="PHIẾU PHÂN TÍCH COST & TÍNH KHẢ THI DỰ ÁN", ln=True, align='C')
    pdf.ln(5)
    
    pdf.set_font(font_name, '', 11)
    pdf.cell(0, 6, txt=f"Ngày phân tích: {summary_row['Ngày']}", ln=True)
    pdf.cell(0, 6, txt=f"Tên Dự án / Sản phẩm: {summary_row['Tên dự án']}", ln=True)
    pdf.cell(0, 6, txt=f"Lĩnh vực áp dụng: {summary_row['Ngành nghề']}", ln=True)
    pdf.cell(0, 6, txt=f"Quy mô sản xuất: {summary_row['Quy mô']} Đơn vị", ln=True)
    pdf.ln(5)

    # --- Bảng Chi Tiết Cost ---
    if not df_detail.empty:
        pdf.set_font(font_name, 'B', 10)
        pdf.cell(0, 8, txt="I. BẢNG BÓC TÁCH CHI PHÍ (COST BREAKDOWN):", ln=True)
        
        pdf.set_font(font_name, 'B', 8)
        col_widths = [45, 55, 12, 18, 30, 30] 
        headers = ["Nhóm chi phí", "Tên chi tiết", "ĐVT", "Định mức", "Đơn giá", "Thành tiền"]
        
        pdf.set_fill_color(220, 220, 220)
        for i, header in enumerate(headers):
            pdf.cell(col_widths[i], 8, txt=header, border=1, fill=True, align='C')
        pdf.ln()
        
        pdf.set_font(font_name, '', 8)
        for _, row in df_detail.iterrows():
            row_vals = [
                str(row.get("Nhóm chi phí", "")),
                str(row.get("Tên chi tiết", "")),
                str(row.get("Đơn vị", "")),
                f"{float(row.get('Định mức', 0)):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if row.get("Định mức") else "",
                f"{float(row.get('Đơn giá', 0)):,.0f}".replace(",", ".") if row.get("Đơn giá") else "",
                f"{float(row.get('Thành tiền', 0)):,.0f}".replace(",", ".") if row.get("Thành tiền") else ""
            ]
            aligns = ['L', 'L', 'C', 'R', 'R', 'R']
            
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

    # --- Phần Tổng Kết Go/No-Go ---
    pdf.ln(10)
    pdf.set_font(font_name, 'B', 10)
    pdf.cell(0, 8, txt="II. KẾT QUẢ ĐÁNH GIÁ TÀI CHÍNH:", ln=True)
    
    pdf.set_font(font_name, '', 10)
    pdf.cell(90, 8, txt="1. Tổng Giá Vốn Thực Tế (Cost):", border=1)
    pdf.cell(100, 8, txt=f"{float(summary_row['Tổng Cost']):,.0f} VNĐ".replace(",", "."), border=1, align='R', ln=True)
    
    pdf.cell(90, 8, txt="2. Giá Bán Dự Kiến / Cạnh Tranh:", border=1)
    pdf.cell(100, 8, txt=f"{float(summary_row['Giá bán']):,.0f} VNĐ".replace(",", "."), border=1, align='R', ln=True)
    
    pdf.cell(90, 8, txt="3. Lợi Nhuận Gộp Ước Tính:", border=1)
    pdf.cell(100, 8, txt=f"{float(summary_row['Lợi nhuận']):,.0f} VNĐ".replace(",", "."), border=1, align='R', ln=True)
    
    pdf.set_font(font_name, 'B', 11)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(90, 10, txt="4. TỶ SUẤT LỢI NHUẬN (MARGIN):", border=1, fill=True)
    pdf.cell(100, 10, txt=f"{float(summary_row['Margin (%)']):,.2f} %", border=1, fill=True, align='R', ln=True)
    
    pdf.cell(90, 10, txt="5. QUYẾT ĐỊNH (KẾT LUẬN):", border=1, fill=True)
    pdf.cell(100, 10, txt=str(summary_row['Đánh giá']).upper(), border=1, fill=True, align='C', ln=True)

    temp_filename = f"temp_analysis_{datetime.now().strftime('%H%M%S')}.pdf"
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

# Tải dữ liệu Bảng Lịch sử Phân tích
cols_Costing = ["Ngày", "Tên dự án", "Ngành nghề", "Quy mô", "Tổng Cost", "Giá bán", "Lợi nhuận", "Margin (%)", "Đánh giá", "Chi tiết BOM"]
df_Costing = load_data("wanchi_costing_v2", cols_Costing)
df_Costing = df_Costing.loc[:, ~df_Costing.columns.duplicated()]

# ==========================================
# GIAO DIỆN CHÍNH
# ==========================================
st.title("⚖️ Bóc Tách Chi Phí & Đánh Giá Dự Án Đa Ngành")
st.markdown("Dùng trong nội bộ để tính chính xác Giá vốn (Cost), xác định lợi nhuận và ra quyết định Có nên làm hay không.")
st.markdown("---")

tab_TinhCost, tab_LichSu = st.tabs(["🧩 BÓC TÁCH CHI PHÍ MỚI", "🗂️ LỊCH SỬ ĐÁNH GIÁ (GO/NO-GO)"])

# ------------------------------------------
# TAB 1: TÍNH GIÁ COST CHI TIẾT
# ------------------------------------------
with tab_TinhCost:
    with st.container(border=True):
        st.subheader("Bước 1: Chọn Ngành Nghề & Thiết Lập Dự Án")
        c_nganh, c_btn = st.columns([3, 1])
        nganh_chon = c_nganh.selectbox("Lĩnh vực kinh doanh / Loại dự án:", list(TEMPLATES.keys()), index=list(TEMPLATES.keys()).index(st.session_state.cost_template))
        
        st.caption("💡 Mẹo: Bấm 'Tạo Bảng Tính Mẫu' để phần mềm tự động lên khung các danh mục chi phí cần có cho ngành này.")
        if c_btn.button("✨ TẠO BẢNG TÍNH MẪU", use_container_width=True):
            tao_bang_mau_theo_nganh(nganh_chon)
            st.rerun()

        st.markdown("---")
        col_info1, col_info2, col_info3 = st.columns([2, 1, 1])
        ten_du_an = col_info1.text_input("Tên Công việc / Sản phẩm cần phân tích:", placeholder="VD: Ly Cafe Sữa, Thiết kế tủ áo, Xây nhà cấp 4...")
        so_luong_lo = col_info2.number_input("Quy mô / Số lượng:", min_value=1, value=1, step=1, help="Nhập 1 nếu tính cho 1 sản phẩm, nhập 1000 nếu tính cho cả lô.")
        gia_ban_du_kien = col_info3.number_input("Giá thu khách dự kiến (VNĐ):", min_value=0, step=1000, help="Giá bạn định thu của khách hoặc giá thị trường chung.")

    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("Bước 2: Điền Bảng Định Mức Trực Tiếp (BOM)")
    st.info("Hãy điền vào Tên chi tiết, Định mức (Số lượng/Thời gian) và Đơn giá. Cuộn xuống dưới cùng để ấn nút '+' nếu cần thêm dòng.")

    # Cập nhật danh sách Selectbox linh hoạt theo Ngành đã chọn
    current_categories = TEMPLATES[st.session_state.cost_template]
    
    edited_cost_df = st.data_editor(
        st.session_state.cost_items,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Nhóm chi phí": st.column_config.SelectboxColumn(
                "Nhóm Phân Loại",
                options=current_categories,
                required=True
            ),
            "Tên chi tiết": st.column_config.TextColumn("Tên chi tiết cụ thể", required=True),
            "Đơn vị": st.column_config.TextColumn("ĐVT"),
            "Định mức": st.column_config.NumberColumn("Số lượng tiêu hao", min_value=0.0, format="%.3f"),
            "Đơn giá": st.column_config.NumberColumn("Đơn giá cost (VNĐ)", min_value=0, step=1000, format="%d"),
            "Thành tiền": st.column_config.NumberColumn("Thành tiền (VNĐ)", disabled=True)
        },
        key="cost_bom_editor"
    )

    tong_cost = 0
    if not edited_cost_df.empty:
        edited_cost_df["Định mức"] = pd.to_numeric(edited_cost_df["Định mức"], errors="coerce").fillna(0)
        edited_cost_df["Đơn giá"] = pd.to_numeric(edited_cost_df["Đơn giá"], errors="coerce").fillna(0)
        edited_cost_df["Thành tiền"] = edited_cost_df["Định mức"] * edited_cost_df["Đơn giá"]
        tong_cost = edited_cost_df["Thành tiền"].sum()

    st.markdown("---")
    st.subheader("Bước 3: Phân Tích Khả Thi (Go / No-Go)")

    col_res1, col_res2 = st.columns([1, 1])
    loi_nhuan = gia_ban_du_kien - tong_cost
    margin = (loi_nhuan / gia_ban_du_kien * 100) if gia_ban_du_kien > 0 else 0

    with col_res1:
        with st.container(border=True):
            st.markdown("### CHỈ SỐ TÀI CHÍNH")
            st.write(f"**Tổng Giá Vốn (Cost):** {tong_cost:,.0f} VNĐ")
            st.write(f"**Giá Bán Dự Kiến:** {gia_ban_du_kien:,.0f} VNĐ")
            
            if loi_nhuan > 0:
                st.write(f"**Lợi Nhuận Gộp:** <span style='color:green;'>+{loi_nhuan:,.0f} VNĐ</span>", unsafe_allow_html=True)
                st.write(f"**Biên Lợi Nhuận (Margin):** <span style='color:green;'>{margin:.2f}%</span>", unsafe_allow_html=True)
            else:
                st.write(f"**Lợi Nhuận Gộp:** <span style='color:red;'>{loi_nhuan:,.0f} VNĐ</span>", unsafe_allow_html=True)
                st.write(f"**Biên Lợi Nhuận (Margin):** <span style='color:red;'>{margin:.2f}%</span>", unsafe_allow_html=True)

    with col_res2:
        with st.container(border=True):
            st.markdown("### KẾT LUẬN & ĐÁNH GIÁ")
            
            danh_gia = ""
            if tong_cost == 0 or gia_ban_du_kien == 0:
                st.info("Vui lòng nhập đủ bảng Cost và Giá bán dự kiến để hệ thống phân tích.")
                danh_gia = "Chưa đủ dữ liệu"
            elif margin >= 30:
                st.success("⭐⭐⭐ RẤT TỐT - ĐÁNG LÀM NGAY!")
                st.write("Biên lợi nhuận an toàn, thừa sức bù đắp các rủi ro phát sinh. Chốt đơn!")
                danh_gia = "Rất tốt (Nên làm)"
            elif 15 <= margin < 30:
                st.warning("⭐⭐ KHÁ - CÓ THỂ LÀM")
                st.write("Lợi nhuận tiêu chuẩn. Tuy nhiên cần giám sát chặt chẽ nhân công và vật tư để không bị đội chi phí.")
                danh_gia = "Khá (Có thể làm)"
            elif 0 < margin < 15:
                st.error("⭐ BIÊN MỎNG - RỦI RO LỖ CAO")
                st.write("Lãi rất mỏng, chỉ cần hư hỏng 1 chút hoặc trễ tiến độ là sẽ chuyển sang lỗ. **Nên đàm phán tăng giá** hoặc **Từ chối**.")
                danh_gia = "Rủi ro (Cân nhắc từ chối)"
            else:
                st.error("🛑 LỖ VỐN - TUYỆT ĐỐI KHÔNG NHẬN")
                st.write("Dự án không sinh lời, càng làm càng âm vốn. Hủy ngay!")
                danh_gia = "Lỗ vốn (Từ chối)"

    st.markdown("---")
    col_btn1, col_btn2 = st.columns([1, 4])
    
    if col_btn1.button("💾 Lưu Lưu Lịch Sử Phân Tích"):
        if not ten_du_an:
            st.error("⚠️ Vui lòng nhập Tên Công việc / Dự án!")
        elif tong_cost == 0:
            st.error("⚠️ Bảng chi phí đang trống!")
        else:
            with st.spinner("Đang lưu trữ dữ liệu..."):
                bom_json = edited_cost_df.to_json(orient='records')
                new_cost_record = {
                    "Ngày": datetime.today().strftime('%d/%m/%Y'),
                    "Tên dự án": ten_du_an,
                    "Ngành nghề": st.session_state.cost_template,
                    "Quy mô": so_luong_lo,
                    "Tổng Cost": tong_cost,
                    "Giá bán": gia_ban_du_kien,
                    "Lợi nhuận": loi_nhuan,
                    "Margin (%)": margin,
                    "Đánh giá": danh_gia,
                    "Chi tiết BOM": bom_json 
                }
                append_data(new_cost_record, "wanchi_costing_v2", df_Costing)
            
            # Làm sạch form
            tao_bang_mau_theo_nganh(st.session_state.cost_template)
            st.success("✅ Đã cất kết quả vào tủ hồ sơ thành công! (Xem bên Tab Lịch Sử)")
            st.rerun()

# ------------------------------------------
# TAB 2: LỊCH SỬ ĐÁNH GIÁ NỘI BỘ
# ------------------------------------------
with tab_LichSu:
    st.subheader("Danh Sách Các Dự Án Đã Thẩm Định")
    
    edited_LichSu = st.data_editor(
        df_Costing,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Chi tiết BOM": None, 
            "Tổng Cost": st.column_config.NumberColumn(format="%d"),
            "Giá bán": st.column_config.NumberColumn(format="%d"),
            "Lợi nhuận": st.column_config.NumberColumn(format="%d"),
            "Margin (%)": st.column_config.NumberColumn(format="%.2f")
        },
        key="edit_cost_history"
    )

    if st.button("💾 Cập nhật dữ liệu Bảng Lịch Sử"):
        with st.spinner("Đang cập nhật..."):
            save_data(edited_LichSu, "wanchi_costing_v2")
        st.success("✅ Đã cập nhật thành công!")
        st.rerun()

    st.markdown("---")
    st.subheader("🔍 Xem Lại Chi Tiết & In Báo Cáo Nội Bộ")
    
    list_du_an = df_Costing["Tên dự án"].dropna().unique().tolist() if not df_Costing.empty else []
    chon_da = st.selectbox("Chọn dự án để mổ xẻ lại chi phí:", ["(Vui lòng chọn)"] + list_du_an)
    
    if chon_da != "(Vui lòng chọn)":
        row_info = df_Costing[df_Costing["Tên dự án"] == chon_da].iloc[0]
        
        c_thongtin, c_pdf = st.columns([2, 1])
        c_thongtin.markdown(f"**Lĩnh vực:** {row_info.get('Ngành nghề', '')} | **Kết luận lúc đó:** {row_info.get('Đánh giá', '')} | **Margin:** {float(row_info['Margin (%)']):.2f}%")
        
        try:
            df_chitiet = pd.read_json(row_info["Chi tiết BOM"])
            st.dataframe(df_chitiet, use_container_width=True)
            
            if c_pdf.button(f"📄 Tạo Phiếu Phân Tích PDF ({chon_da})"):
                with st.spinner("Đang trích xuất..."):
                    pdf_file = export_internal_analysis_pdf(row_info, df_chitiet)
                file_name = f"TuanQuang_PhanTich_{chon_da}.pdf"
                c_pdf.download_button("⬇️ TẢI PDF XUỐNG", pdf_file, file_name, "application/pdf")
                
        except Exception as e:
            st.error("Lỗi khi đọc dữ liệu chi tiết của dự án này.")
