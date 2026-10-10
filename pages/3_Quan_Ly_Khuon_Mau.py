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

# ---> HÀM XUẤT PDF CƠ BẢN ĐÃ NÂNG CẤP <---
def export_pdf(df, title):
    df_export = df.copy()
    if "Cụm khuôn hoàn chỉnh" in df_export.columns:
        df_export = df_export.drop(columns=["Cụm khuôn hoàn chỉnh"])
    
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    
    try:
        pdf.add_font('ArialVN', '', 'arial.ttf', uni=True)
        pdf.add_font('ArialVN', 'B', 'arialbd.ttf', uni=True)
        font_name = 'ArialVN'
    except:
        font_name = 'Arial'
        st.warning("⚠️ Không tìm thấy file 'arial.ttf'. PDF sẽ bị mất dấu tiếng Việt.")

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

    if not df_export.empty:
        pdf.set_font(font_name, '', 8)
        num_cols = ["Số lượng", "Đơn giá", "Cắt dây", "Xung điện (EDM)", "Phay CNC", "Nhiệt Luyện", "Đánh bóng", "Tạo Nhám hoa văn", "Dọn phôi", "Tổng tiền", "Tổng Nguyên Vật Liệu (A)", "Tổng Gia Công (B)", "Tổng Vật Tư (C)", "TỔNG CỘNG", "Tổng giá trị khuôn", "Tổng giá gia công", "Cọc đợt 1", "Còn nợ"]
        
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
                item_w = pdf.get_string_width(val_str) + 4
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
            header_str = str(col)
            while pdf.get_string_width(header_str) > col_widths[i] - 1 and len(header_str) > 0:
                header_str = header_str[:-1]
            pdf.cell(col_widths[i], 8, txt=header_str, border=1, fill=True, align='C')
        pdf.ln()
        
        pdf.set_font(font_name, '', 8)
        sum_tong_tien = 0 
        
        for _, row in df_export.iterrows():
            for i, (col_name, item) in enumerate(row.items()):
                val_str = str(item) if pd.notnull(item) else ""
                align_col = 'L'
                
                if col_name in num_cols and str(item).strip() != "":
                    try:
                        val = float(item)
                        val_str = f"{val:,.0f}".replace(",", ".")
                        align_col = 'R'
                        if col_name in ["Tổng tiền", "TỔNG CỘNG", "Tổng giá trị khuôn", "Tổng giá gia công", "Cọc đợt 1", "Còn nợ"]:
                            sum_tong_tien += val
                    except: pass
                
                while pdf.get_string_width(val_str) > col_widths[i] - 1 and len(val_str) > 0:
                    val_str = val_str[:-1]

                pdf.cell(col_widths[i], 8, txt=val_str, border=1, align=align_col)
            pdf.ln()
            
        if any(c in df_export.columns for c in ["Tổng tiền", "TỔNG CỘNG", "Tổng giá trị khuôn"]):
            pdf.set_font(font_name, 'B' if font_name == 'ArialVN' else '', 9)
            pdf.set_fill_color(240, 240, 240)
            
            for i, col in enumerate(df_export.columns):
                if col in ["Tổng tiền", "TỔNG CỘNG", "Tổng giá trị khuôn"]:
                    tong_str = f"{sum_tong_tien:,.0f}".replace(",", ".")
                    pdf.cell(col_widths[i], 8, txt=tong_str, border=1, fill=True, align='R')
                elif i == len(df_export.columns) - 2: 
                    pdf.cell(col_widths[i], 8, txt="TỔNG CỘNG:", border=1, fill=True, align='R')
                else:
                    pdf.cell(col_widths[i], 8, txt="", border=1, fill=True) 
            pdf.ln()
            
    temp_filename = f"temp_report_{datetime.now().strftime('%H%M%S')}.pdf"
    pdf.output(temp_filename)
    
    with open(temp_filename, "rb") as f:
        pdf_bytes = f.read()
        
    if os.path.exists(temp_filename):
        os.remove(temp_filename)
        
    return pdf_bytes


# ---> HÀM XUẤT HỢP ĐỒNG PDF ĐÃ SỬA LỖI TRÀN CHỮ BẰNG ĐO CHIỀU RỘNG <---
def export_contract_pdf(context):
    pdf = FPDF()
    pdf.add_page()
    
    try:
        pdf.add_font('ArialVN', '', 'arial.ttf', uni=True)
        pdf.add_font('ArialVN', 'B', 'arialbd.ttf', uni=True)
        font_name = 'ArialVN'
    except:
        font_name = 'Arial'

    pdf.set_font(font_name, 'B' if font_name == 'ArialVN' else '', 12)
    pdf.cell(0, 6, txt="CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM", ln=True, align='C')
    pdf.cell(0, 6, txt="Độc lập - Tự do - Hạnh phúc", ln=True, align='C')
    pdf.cell(0, 6, txt="----------***---------", ln=True, align='C')
    pdf.ln(5)
    
    pdf.set_font(font_name, 'B' if font_name == 'ArialVN' else '', 16)
    pdf.cell(0, 10, txt="HỢP ĐỒNG SẢN XUẤT KHUÔN MẪU", ln=True, align='C')
    pdf.ln(2)
    
    pdf.set_font(font_name, '', 11)
    pdf.cell(0, 6, txt=f"Hôm nay, ngày {context['ngay']} tháng {context['thang']} năm {context['nam']}, các bên trong hợp đồng gồm:", ln=True, align='L')
    pdf.ln(2)
    
    pdf.set_font(font_name, 'B' if font_name == 'ArialVN' else '', 11)
    pdf.cell(0, 6, txt="1. Bên A (Bên đặt hàng):", ln=True, align='L')
    pdf.set_font(font_name, '', 11)
    
    pdf.multi_cell(0, 6, txt=f"- Tên doanh nghiệp: {context['ten_cong_ty_khach']}", align='L')
    pdf.multi_cell(0, 6, txt=f"- Đại diện là Ông/Bà: {context['nguoi_dai_dien']}        Chức vụ: {context['chuc_vu']}", align='L')
    pdf.multi_cell(0, 6, txt=f"- Địa chỉ: {context['dia_chi_khach']}", align='L')
    pdf.multi_cell(0, 6, txt=f"- Điện thoại: {context['sdt_khach']}", align='L')
    pdf.ln(2)

    pdf.set_font(font_name, 'B' if font_name == 'ArialVN' else '', 11)
    pdf.cell(0, 6, txt="2. Bên B (Bên sản xuất khuôn mẫu):", ln=True, align='L')
    pdf.set_font(font_name, '', 11)
    pdf.cell(0, 6, txt="- Bà: Thái Nhuận Chi        Chức vụ: Chủ Hộ Kinh Doanh", ln=True, align='L')
    pdf.cell(0, 6, txt="- Tên doanh nghiệp: HỘ KINH DOANH WANCHI        MST: 8289829752-001", ln=True, align='L')
    pdf.multi_cell(0, 6, txt="- Địa chỉ: 775 Võ Hữu Lợi, Ấp 16, Xã Lê Minh Xuân, Huyện Bình Chánh", align='L')
    pdf.multi_cell(0, 6, txt="- Tài Khoản Ngân Hàng Sacombank - sở giao dịch: 060329421638", align='L')
    pdf.cell(0, 6, txt="- Điện thoại: 0937572577", ln=True, align='L')
    pdf.ln(4)

    pdf.cell(0, 6, txt="Hai bên thống nhất thỏa thuận lập hợp đồng với nội dung như sau:", ln=True, align='L')
    pdf.ln(2)

    pdf.set_font(font_name, 'B' if font_name == 'ArialVN' else '', 11)
    col_w = [15, 50, 30, 15, 35, 30]
    pdf.cell(col_w[0], 8, txt="STT", border=1, align='C')
    pdf.cell(col_w[1], 8, txt="Mô tả", border=1, align='C')
    pdf.cell(col_w[2], 8, txt="Hình ảnh", border=1, align='C')
    pdf.cell(col_w[3], 8, txt="SL", border=1, align='C')
    pdf.cell(col_w[4], 8, txt="Đơn giá", border=1, align='C')
    pdf.cell(col_w[5], 8, txt="Ghi chú", border=1, align='C')
    pdf.ln()

    # Đo độ rộng tự động để gọt text tránh tràn cell
    pdf.set_font(font_name, '', 10)
    tk_hienthi = str(context['ten_khuon'])
    while pdf.get_string_width(tk_hienthi) > (col_w[1] - 3) and len(tk_hienthi) > 0:
        tk_hienthi = tk_hienthi[:-1]

    sl_hienthi = str(context['sl_khuon'])
    while pdf.get_string_width(sl_hienthi) > (col_w[3] - 3) and len(sl_hienthi) > 0:
        sl_hienthi = sl_hienthi[:-1]

    gia_hienthi = str(context['gia_khuon_str'])
    while pdf.get_string_width(gia_hienthi) > (col_w[4] - 3) and len(gia_hienthi) > 0:
        gia_hienthi = gia_hienthi[:-1]

    pdf.cell(col_w[0], 12, txt="1", border=1, align='C')
    pdf.cell(col_w[1], 12, txt=tk_hienthi, border=1, align='C')
    pdf.cell(col_w[2], 12, txt="", border=1, align='C')
    pdf.cell(col_w[3], 12, txt=sl_hienthi, border=1, align='C')
    pdf.cell(col_w[4], 12, txt=gia_hienthi, border=1, align='C')
    pdf.cell(col_w[5], 12, txt="Thép: ...", border=1, align='C')
    pdf.ln()

    pdf.set_font(font_name, 'B' if font_name == 'ArialVN' else '', 11)
    pdf.cell(sum(col_w[:4]), 8, txt="Tổng", border=1, align='C')
    pdf.cell(col_w[4], 8, txt=str(context['gia_khuon_str']), border=1, align='C')
    pdf.set_font(font_name, '', 9)
    pdf.cell(col_w[5], 8, txt="Bao gồm HĐ", border=1, align='C')
    pdf.ln(5)

    pdf.set_font(font_name, 'B' if font_name == 'ArialVN' else '', 11)
    pdf.cell(0, 8, txt="ĐIỀU 1: BẢNG KÊ CHI TIẾT KHUÔN MẪU NHƯ SAU", ln=True, align='L')
    pdf.set_font(font_name, '', 11)
    pdf.cell(0, 6, txt="Thời gian giao mẫu thử và yêu cầu kỹ thuật", ln=True, align='L')
    pdf.multi_cell(0, 6, txt=f"- Thời gian giao mẫu: {context['thoi_gian_giao']} ngày (không tính Lễ, CN) kể từ ngày nhận cọc.", align='L')
    pdf.cell(0, 6, txt="- Yêu cầu kỹ thuật: Theo bản vẽ", ln=True, align='L')
    pdf.cell(0, 6, txt="- Vật tư làm mẫu: Theo bản vẽ hoặc tương đương", ln=True, align='L')
    pdf.ln(2)

    pdf.cell(0, 6, txt="1.2 Thanh toán", ln=True, align='L')
    pdf.cell(0, 6, txt="- Lần 1: 50% sau khi ký hợp đồng", ln=True, align='L')
    pdf.cell(0, 6, txt="- Lần 2: 50% còn lại sau khi nhận nghiệm thu mẫu hoàn chỉnh", ln=True, align='L')
    pdf.ln(2)

    pdf.cell(0, 6, txt="1.3 Bảo hành khuôn", ln=True, align='L')
    pdf.cell(0, 6, txt="- Theo Đơn hàng 100.000 sản phẩm.", ln=True, align='L')
    pdf.multi_cell(0, 6, txt="- Khuôn được bảo quản, lưu kho miễn phí khi còn sản xuất tại công ty.", align='L')
    pdf.ln(2)

    pdf.cell(0, 6, txt="1.4 Bảo mật", ln=True, align='L')
    pdf.multi_cell(0, 6, txt="Bản vẽ khuôn mẫu và khuôn mẫu thuộc về công ty khách hàng không được sử dụng cho công ty thứ 3. Nếu vi phạm chịu hoàn toàn trách nhiệm.")
    pdf.ln(4)

    pdf.set_font(font_name, 'B' if font_name == 'ArialVN' else '', 11)
    pdf.cell(0, 8, txt="ĐIỀU 2: QUYỀN VÀ NGHĨA VỤ CỦA BÊN A", ln=True, align='L')
    pdf.set_font(font_name, '', 11)
    pdf.multi_cell(0, 6, txt="2.1. Bên A có các nghĩa vụ sau đây:\na) Chịu trách nhiệm đối với tính hợp pháp về quyền sở hữu trí tuệ, kiểu dáng công nghiệp và logo của khuôn mẫu.\nb) Thanh toán theo đúng tiến độ thoả thuận trong hợp đồng.")
    pdf.multi_cell(0, 6, txt="2.2 Bên A có các quyền sau đây:\na) Đơn phương chấm dứt thực hiện hợp đồng và yêu cầu bồi thường thiệt hại khi bên B vi phạm nghiêm trọng hợp đồng.\nb) Trong trường hợp sản phẩm không bảo đảm chất lượng mà bên A đồng ý nhận sản phẩm và yêu cầu sửa chữa nhưng bên B không thể sửa chữa được trong thời hạn đã thoả thuận thì bên A có quyền hủy bỏ hợp đồng và yêu cầu bồi thường thiệt hại.\nc) Khuôn mẫu thuộc quyền sở hữu bên A, có quyền thu hồi khuôn bất cứ lúc nào.")
    pdf.ln(2)

    pdf.set_font(font_name, 'B' if font_name == 'ArialVN' else '', 11)
    pdf.cell(0, 8, txt="ĐIỀU 3: QUYỀN VÀ NGHĨA VỤ CỦA BÊN B", ln=True, align='L')
    pdf.set_font(font_name, '', 11)
    pdf.multi_cell(0, 6, txt="3.1. Bên B có các nghĩa vụ sau đây:\na) Đảm bảo toàn bộ nguyên liệu, vật liệu để gia công theo thỏa thuận với bên A về số lượng, chất lượng, tiêu chuẩn kỹ thuật theo đúng bảng báo giá và bản vẽ bên A.\nb) Giao sản phẩm cho bên A đúng số lượng, chất lượng, phương thức, thời hạn và địa điểm đã thoả thuận.\nc) Giữ bí mật các thông tin về quy trình gia công và sản phẩm tạo ra.")
    pdf.multi_cell(0, 6, txt="3.2. Bên B có các quyền sau đây:\na) Từ chối sự chỉ dẫn không hợp lý của bên A, nếu thấy chỉ dẫn đó có thể làm giảm chất lượng sản phẩm, nhưng phải báo ngay cho bên A.\nb) Yêu cầu bên A trả đủ tiền công theo đúng thời hạn và phương thức đã thoả thuận.")
    pdf.ln(4)

    pdf.cell(0, 6, txt="Hợp đồng này được làm thành 2 bản có giá trị như nhau, mỗi bên giữ 1 bản.", ln=True, align='L')
    pdf.ln(10)
    
    pdf.set_font(font_name, 'B' if font_name == 'ArialVN' else '', 12)
    pdf.cell(85, 6, txt="ĐẠI DIỆN BÊN A", align='C')
    pdf.cell(85, 6, txt="ĐẠI DIỆN BÊN B", ln=True, align='C')

    temp_filename = f"temp_hd_{datetime.now().strftime('%H%M%S')}.pdf"
    pdf.output(temp_filename)
    with open(temp_filename, "rb") as f:
        pdf_bytes = f.read()
    if os.path.exists(temp_filename):
        os.remove(temp_filename)
    return pdf_bytes

# ---> HÀM XUẤT BÁO GIÁ KHUÔN ĐÃ SỬA LỖI BẰNG ĐO CHIỀU RỘNG <---
def export_quote_khuon_pdf(context):
    pdf = FPDF()
    pdf.add_page()
    try:
        pdf.add_font('ArialVN', '', 'arial.ttf', uni=True)
        pdf.add_font('ArialVN', 'B', 'arialbd.ttf', uni=True)
        font_name = 'ArialVN'
    except:
        font_name = 'Arial'

    pdf.set_font(font_name, 'B' if font_name == 'ArialVN' else '', 24)
    pdf.cell(0, 10, txt="WANCHI", ln=True, align='C')
    pdf.set_font(font_name, '', 12)
    pdf.cell(0, 6, txt="www.wanchi.vn", ln=True, align='C')
    pdf.ln(5)

    pdf.set_font(font_name, '', 10)
    pdf.multi_cell(0, 5, txt="Văn Phòng: 445/87 Tân Hoà Đông P. Bình Trị Đông Q.Bình Tân.", align='L')
    pdf.multi_cell(0, 5, txt="Nhà Máy: 775 Võ Hữu Lợi, Ấp 16, Xã Lê Minh Xuân, Huyện Bình Chánh, Thành phố Hồ Chí Minh", align='L')
    pdf.cell(0, 5, txt="Điện Thoại: 0937572577. A Quang", ln=True, align='L')
    
    pdf.set_xy(10, 40)
    pdf.cell(0, 5, txt=f"TP. HCM, ngày {context['ngay']} tháng {context['thang']} năm {context['nam']}", ln=True, align='R')
    pdf.ln(10)

    pdf.set_font(font_name, 'B' if font_name == 'ArialVN' else '', 16)
    pdf.cell(0, 10, txt="BÁO GIÁ KHUÔN MẪU", ln=True, align='C')
    pdf.ln(5)

    pdf.set_font(font_name, 'B' if font_name == 'ArialVN' else '', 11)
    pdf.multi_cell(0, 6, txt=f"Người Nhận: {context['ten_cong_ty_khach']} - {context['nguoi_dai_dien']}", align='L')
    pdf.ln(2)

    pdf.set_font(font_name, 'B' if font_name == 'ArialVN' else '', 11)
    col_w = [15, 85, 35, 40]
    pdf.cell(col_w[0], 8, txt="STT", border=1, align='C')
    pdf.cell(col_w[1], 8, txt="Mô tả", border=1, align='C')
    pdf.cell(col_w[2], 8, txt="Hình ảnh", border=1, align='C')
    pdf.cell(col_w[3], 8, txt="Số lượng", border=1, align='C')
    pdf.ln()

    pdf.set_font(font_name, '', 11)
    
    # Đo đạc và tự động gọt chữ cho vừa vặn bề ngang của cột
    tk_hienthi = str(context['ten_khuon'])
    while pdf.get_string_width(tk_hienthi) > (col_w[1] - 3) and len(tk_hienthi) > 0:
        tk_hienthi = tk_hienthi[:-1]

    sl_hienthi = f"{context['sl_khuon']} khuôn"
    while pdf.get_string_width(sl_hienthi) > (col_w[3] - 3) and len(sl_hienthi) > 0:
        sl_hienthi = sl_hienthi[:-1]

    pdf.cell(col_w[0], 12, txt="1", border=1, align='C')
    pdf.cell(col_w[1], 12, txt=tk_hienthi, border=1, align='L')
    pdf.cell(col_w[2], 12, txt="", border=1, align='C')
    pdf.cell(col_w[3], 12, txt=sl_hienthi, border=1, align='C')
    pdf.ln()

    pdf.set_font(font_name, '', 10)
    pdf.cell(0, 8, txt="Giá trên chưa bao gồm hóa đơn", ln=True, align='R')
    pdf.ln(5)

    pdf.set_font(font_name, 'B' if font_name == 'ArialVN' else '', 11)
    pdf.cell(0, 6, txt="Thông Tin Khuôn:", ln=True, align='L')
    pdf.set_font(font_name, '', 11)
    pdf.cell(0, 6, txt="- Nguyên Liệu sản xuất khuôn:", ln=True, align='L')
    pdf.cell(0, 6, txt="  + Vỏ khuôn: Thép SC55", ln=True, align='L')
    pdf.cell(0, 6, txt="  + Phôi khuôn: Thép 2083", ln=True, align='L')
    
    pdf.set_font(font_name, 'B' if font_name == 'ArialVN' else '', 11)
    pdf.cell(0, 6, txt="Giá Khuôn:", ln=True, align='L')
    pdf.set_font(font_name, '', 11)
    pdf.multi_cell(0, 6, txt=f"- Giá hoàn thiện khuôn: {context['gia_khuon_str']} (Mẫu bóng)", align='L')
    
    pdf.set_font(font_name, 'B' if font_name == 'ArialVN' else '', 11)
    pdf.cell(0, 6, txt="Bảo hành khuôn:", ln=True, align='L')
    pdf.set_font(font_name, '', 11)
    pdf.multi_cell(0, 6, txt="- Khuôn bảo hành miễn phí 5 năm hoặc 100.000 sản phẩm tại công ty.", align='L')
    pdf.ln(2)

    pdf.set_font(font_name, 'B' if font_name == 'ArialVN' else '', 11)
    pdf.cell(0, 6, txt="Thanh toán:", ln=True, align='L')
    pdf.set_font(font_name, '', 11)
    pdf.cell(0, 6, txt="- 50% sau khi ký báo giá hoặc ký hợp đồng", ln=True, align='L')
    pdf.multi_cell(0, 6, txt="- 50% còn lại sau khi nhận mẫu thử hoàn chỉnh", align='L')
    pdf.ln(10)
    
    pdf.set_font(font_name, '', 12)
    pdf.cell(0, 6, txt="Xin chân thành cảm ơn sự tín nhiệm của quý khách hàng!", ln=True, align='C')

    temp_filename = f"temp_bgk_{datetime.now().strftime('%H%M%S')}.pdf"
    pdf.output(temp_filename)
    with open(temp_filename, "rb") as f:
        pdf_bytes = f.read()
    if os.path.exists(temp_filename):
        os.remove(temp_filename)
    return pdf_bytes

# ---> HÀM XUẤT BÁO GIÁ SẢN PHẨM ĐÃ SỬA LỖI BẰNG ĐO CHIỀU RỘNG <---
def export_quote_sp_pdf(context):
    pdf = FPDF()
    pdf.add_page()
    try:
        pdf.add_font('ArialVN', '', 'arial.ttf', uni=True)
        pdf.add_font('ArialVN', 'B', 'arialbd.ttf', uni=True)
        font_name = 'ArialVN'
    except:
        font_name = 'Arial'

    pdf.set_font(font_name, 'B' if font_name == 'ArialVN' else '', 24)
    pdf.cell(0, 10, txt="WANCHI", ln=True, align='C')
    pdf.set_font(font_name, '', 12)
    pdf.cell(0, 6, txt="www.wanchi.vn", ln=True, align='C')
    pdf.ln(5)

    pdf.set_font(font_name, '', 10)
    pdf.multi_cell(0, 5, txt="Văn Phòng: 445/87 Tân Hoà Đông P. Bình Trị Đông Q.Bình Tân.", align='L')
    pdf.multi_cell(0, 5, txt="Nhà Máy: 775 Võ Hữu Lợi, Ấp 16, Xã Lê Minh Xuân, Huyện Bình Chánh, Thành phố Hồ Chí Minh", align='L')
    pdf.cell(0, 5, txt="Điện Thoại: 0937572577. A Quang", ln=True, align='L')
    
    pdf.set_xy(10, 40)
    pdf.cell(0, 5, txt=f"TP. HCM, ngày {context['ngay']} tháng {context['thang']} năm {context['nam']}", ln=True, align='R')
    pdf.ln(10)

    pdf.set_font(font_name, 'B' if font_name == 'ArialVN' else '', 16)
    pdf.cell(0, 10, txt="BÁO GIÁ SẢN PHẨM", ln=True, align='C')
    pdf.ln(5)

    pdf.set_font(font_name, 'B' if font_name == 'ArialVN' else '', 11)
    pdf.multi_cell(0, 6, txt=f"Người Nhận: {context['ten_cong_ty_khach']} - {context['nguoi_dai_dien']}", align='L')
    pdf.ln(2)

    pdf.set_font(font_name, 'B' if font_name == 'ArialVN' else '', 11)
    col_w = [15, 70, 30, 25, 35]
    pdf.cell(col_w[0], 8, txt="STT", border=1, align='C')
    pdf.cell(col_w[1], 8, txt="Mô tả sản phẩm", border=1, align='C')
    pdf.cell(col_w[2], 8, txt="Hình ảnh", border=1, align='C')
    pdf.cell(col_w[3], 8, txt="Số lượng", border=1, align='C')
    pdf.cell(col_w[4], 8, txt="Đơn giá", border=1, align='C')
    pdf.ln()

    pdf.set_font(font_name, '', 11)
    
    # Đo đạc và tự động gọt chữ cho vừa vặn bề ngang của cột
    tsp_hienthi = str(context['ten_san_pham'])
    while pdf.get_string_width(tsp_hienthi) > (col_w[1] - 3) and len(tsp_hienthi) > 0:
        tsp_hienthi = tsp_hienthi[:-1]

    sl_hienthi = f"{context['sl_san_pham']} C"
    while pdf.get_string_width(sl_hienthi) > (col_w[3] - 3) and len(sl_hienthi) > 0:
        sl_hienthi = sl_hienthi[:-1]

    gia_hienthi = f"{context['gia_san_pham_str']} đ"
    while pdf.get_string_width(gia_hienthi) > (col_w[4] - 3) and len(gia_hienthi) > 0:
        gia_hienthi = gia_hienthi[:-1]

    pdf.cell(col_w[0], 12, txt="1", border=1, align='C')
    pdf.cell(col_w[1], 12, txt=tsp_hienthi, border=1, align='L')
    pdf.cell(col_w[2], 12, txt="", border=1, align='C')
    pdf.cell(col_w[3], 12, txt=sl_hienthi, border=1, align='C')
    pdf.cell(col_w[4], 12, txt=gia_hienthi, border=1, align='C')
    pdf.ln()

    pdf.set_font(font_name, '', 10)
    pdf.cell(0, 8, txt="Giá trên chưa bao gồm hóa đơn", ln=True, align='R')
    pdf.ln(5)

    pdf.set_font(font_name, 'B' if font_name == 'ArialVN' else '', 11)
    pdf.cell(0, 6, txt="Thông tin sản phẩm:", ln=True, align='L')
    pdf.set_font(font_name, '', 11)
    pdf.multi_cell(0, 6, txt=f"- Chất liệu sản phẩm: {context['chat_lieu_nhua']}", align='L')
    pdf.multi_cell(0, 6, txt=f"- Thời gian hoàn thiện đơn hàng tùy theo số lượng đặt", align='L')
    pdf.ln(2)

    pdf.set_font(font_name, 'B' if font_name == 'ArialVN' else '', 11)
    pdf.cell(0, 6, txt="Địa điểm giao hàng:", ln=True, align='L')
    pdf.set_font(font_name, '', 11)
    pdf.cell(0, 6, txt="- Tại hãng sản xuất wanchi", ln=True, align='L')
    pdf.ln(2)

    pdf.set_font(font_name, 'B' if font_name == 'ArialVN' else '', 11)
    pdf.cell(0, 6, txt="Thanh toán:", ln=True, align='L')
    pdf.set_font(font_name, '', 11)
    pdf.cell(0, 6, txt="- Tạm ứng 50% khi đặt hàng", ln=True, align='L')
    pdf.multi_cell(0, 6, txt="- 50% còn lại thanh toán trước khi giao hàng", align='L')
    pdf.ln(10)
    
    pdf.set_font(font_name, '', 12)
    pdf.cell(0, 6, txt="Xin chân thành cảm ơn sự tín nhiệm của quý khách hàng!", ln=True, align='C')

    temp_filename = f"temp_bgsp_{datetime.now().strftime('%H%M%S')}.pdf"
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
df_F = df_F.loc[:, ~df_F.columns.duplicated()]

all_molds_set = set()
if not df_A.empty: all_molds_set.update(df_A["Mã khuôn"].dropna().unique())
if not df_B.empty: all_molds_set.update(df_B["Mã khuôn"].dropna().unique())
if not df_C.empty: all_molds_set.update(df_C["Mã khuôn"].dropna().unique())
if not df_D.empty: all_molds_set.update(df_D["Mã khuôn"].dropna().unique())
if not df_F.empty: all_molds_set.update(df_F["Mã khuôn"].dropna().unique())
list_molds_master = sorted(list(all_molds_set))


# ==========================================
# GIAO DIỆN CHÍNH & LƯỚI ĐIỀU HƯỚNG 3 CỘT
# ==========================================
st.title("🏭 Công Cụ Quản Lý Khuôn Mẫu WANCHI")
st.markdown("---")

if "current_tab" not in st.session_state:
    st.session_state.current_tab = "A. Nguyên Vật Liệu"

menu_items = [
    "A. Nguyên Vật Liệu", 
    "B. Gia Công", 
    "C. Vật Tư Khuôn Mẫu", 
    "D. Tổng Giá Khuôn",
    "E. Danh Sách & Quản Trị",
    "F. Tạo Đơn Hàng Gia Công",
    "G. Theo Dõi Đơn Hàng",
    "H. Báo Giá",
    "I. Hợp Đồng"
]

for i in range(0, len(menu_items), 3):
    cols = st.columns(3)
    for j, col in enumerate(cols):
        if i + j < len(menu_items):
            item = menu_items[i + j]
            btn_style = "primary" if st.session_state.current_tab == item else "secondary"
            if col.button(item, use_container_width=True, type=btn_style):
                st.session_state.current_tab = item
                st.rerun()

st.markdown("---")

# ------------------------------------------
# MODULE A: NGUYÊN VẬT LIỆU
# ------------------------------------------
if st.session_state.current_tab == "A. Nguyên Vật Liệu":
    st.header("A. Nguyên Vật Liệu")
    with st.expander("➕ Nhập Nguyên Vật Liệu Mới"):
        with st.form("form_A"):
            c1, c2, c3, c4 = st.columns(4)
            ngay_a = c1.date_input("Ngày", datetime.today())
            ncc_a = c2.text_input("Nhà cung cấp NVL")
            ma_khuon_a = c3.text_input("Mã khuôn (Nhập mã mới tại đây)")
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
    st.subheader("📥 Xuất Báo Cáo PDF")
    col_pdf1, col_pdf2 = st.columns([1, 2])
    filter_pdf_a = col_pdf1.selectbox("Chọn Mã khuôn để xuất PDF:", ["Tất cả"] + list_molds_master, key="pdf_a")
    
    if st.button("Tạo file PDF (Module A)"):
        with st.spinner("Đang trích xuất file PDF..."):
            df_export_a = edited_A if filter_pdf_a == "Tất cả" else edited_A[edited_A["Mã khuôn"] == filter_pdf_a]
            pdf_a = export_pdf(df_export_a, f"BÁO CÁO NGUYÊN VẬT LIỆU KHUÔN {filter_pdf_a}")
        col_pdf2.download_button("⬇️ Nhấn để Tải PDF Xuống", pdf_a, f"WANCHI_NVL_{filter_pdf_a}.pdf", "application/pdf")


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
    st.subheader("📥 Xuất Báo Cáo PDF")
    col_pdf3, col_pdf4 = st.columns([1, 2])
    filter_pdf_b = col_pdf3.selectbox("Chọn Mã khuôn để xuất PDF:", ["Tất cả"] + list_molds_master, key="pdf_b")
    
    if st.button("Tạo file PDF (Module B)"):
        with st.spinner("Đang trích xuất file PDF..."):
            df_export_b = edited_B if filter_pdf_b == "Tất cả" else edited_B[edited_B["Mã khuôn"] == filter_pdf_b]
            pdf_b = export_pdf(df_export_b, f"BÁO CÁO CHI PHÍ GIA CÔNG KHUÔN {filter_pdf_b}")
        col_pdf4.download_button("⬇️ Nhấn để Tải PDF Xuống", pdf_b, f"WANCHI_GiaCong_{filter_pdf_b}.pdf", "application/pdf")


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
    st.subheader("📥 Xuất Báo Cáo PDF")
    col_pdf5, col_pdf6 = st.columns([1, 2])
    filter_pdf_c = col_pdf5.selectbox("Chọn Mã khuôn để xuất PDF:", ["Tất cả"] + list_molds_master, key="pdf_c")
    
    if st.button("Tạo file PDF (Module C)"):
        with st.spinner("Đang trích xuất file PDF..."):
            df_export_c = edited_C if filter_pdf_c == "Tất cả" else edited_C[edited_C["Mã khuôn"] == filter_pdf_c]
            pdf_c = export_pdf(df_export_c, f"BÁO CÁO VẬT TƯ KHUÔN {filter_pdf_c}")
        col_pdf6.download_button("⬇️ Nhấn để Tải PDF Xuống", pdf_c, f"WANCHI_VatTu_{filter_pdf_c}.pdf", "application/pdf")


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
    st.subheader("📥 Xuất Báo Cáo PDF")
    col_pdf1_d, col_pdf2_d = st.columns([1, 2])
    filter_pdf_d = col_pdf1_d.selectbox("Chọn Mã khuôn để xuất PDF:", ["Tất cả"] + list_molds_master, key="pdf_d")
    
    if st.button("Tạo file PDF (Module D)"):
        with st.spinner("Đang trích xuất file PDF..."):
            df_export_d = edited_D if filter_pdf_d == "Tất cả" else edited_D[edited_D["Mã khuôn"] == filter_pdf_d]
            pdf_d = export_pdf(df_export_d, f"BẢNG TỔNG HỢP CHI PHÍ KHUÔN {filter_pdf_d}")
        col_pdf2_d.download_button("⬇️ Nhấn để Tải PDF Xuống", pdf_d, f"WANCHI_TongHop_{filter_pdf_d}.pdf", "application/pdf")


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
        st.subheader("📥 Xuất Báo Cáo PDF Danh Sách Khuôn")
        if st.button("Tạo file PDF (Module E)"):
            with st.spinner("Đang trích xuất file PDF..."):
                pdf_e = export_pdf(df_E, "DANH SÁCH TỔNG HỢP CÁC KHUÔN ĐÃ LÀM")
            st.download_button("⬇️ Nhấn để Tải PDF Xuống", pdf_e, "WANCHI_DanhSachKhuon.pdf", "application/pdf")
            
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
        ghi_chu_f = c7.text_input("Ghi chú")
        
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
    st.subheader("📥 Xuất Báo Cáo Đơn Hàng")
    
    col_pdf1_f, col_pdf2_f, col_pdf3_f = st.columns([1, 1, 2])
    
    filter_pdf_mold_f = col_pdf1_f.selectbox("1. Chọn Mã khuôn:", ["Tất cả"] + list_molds_master, key="pdf_mold_f")
    
    if filter_pdf_mold_f != "Tất cả":
        list_vendors_for_mold = edited_F[edited_F["Mã khuôn"] == filter_pdf_mold_f]["Đơn vị gia công"].dropna().unique().tolist()
    else:
        list_vendors_for_mold = edited_F["Đơn vị gia công"].dropna().unique().tolist()
        
    filter_pdf_vendor_f = col_pdf2_f.selectbox("2. Chọn Đơn vị gia công:", ["Tất cả"] + list_vendors_for_mold, key="pdf_vendor_f")
    
    if st.button("Tạo file PDF (Module Theo Dõi Đơn Hàng)"):
        with st.spinner("Đang trích xuất file PDF..."):
            df_export_f = edited_F.copy()
            title_pdf = "ĐƠN HÀNG GIA CÔNG"
            
            if filter_pdf_mold_f != "Tất cả":
                df_export_f = df_export_f[df_export_f["Mã khuôn"] == filter_pdf_mold_f]
                title_pdf += f" {filter_pdf_mold_f}"
                
            if filter_pdf_vendor_f != "Tất cả":
                df_export_f = df_export_f[df_export_f["Đơn vị gia công"] == filter_pdf_vendor_f]
                if filter_pdf_mold_f == "Tất cả":
                    title_pdf += f" - {filter_pdf_vendor_f}"
                    
            pdf_f = export_pdf(df_export_f, title_pdf)
        
        file_name_pdf = f"WANCHI_DonHang_{filter_pdf_mold_f}"
        if filter_pdf_vendor_f != "Tất cả":
            file_name_pdf += f"_{filter_pdf_vendor_f}"
        file_name_pdf += ".pdf"
        
        col_pdf3_f.markdown("<br>", unsafe_allow_html=True)
        col_pdf3_f.download_button("⬇️ Nhấn để Tải PDF Xuống", pdf_f, file_name_pdf, "application/pdf")


# ------------------------------------------
# MODULE H: BÁO GIÁ
# ------------------------------------------
elif st.session_state.current_tab == "H. Báo Giá":
    st.header("H. Báo Giá Khuôn & Sản Phẩm (PDF)")
    st.markdown("Nhập thông tin bên dưới để tự động tạo file **PDF Báo Giá Khuôn** và **Báo Giá Sản Phẩm**.")
    
    with st.form("form_bao_gia"):
        st.subheader("1. Thông tin Khách hàng")
        c1, c2 = st.columns(2)
        ten_cong_ty_khach = c1.text_input("Tên doanh nghiệp / Khách hàng")
        nguoi_dai_dien = c2.text_input("Người đại diện (Ông/Bà)")
        
        st.markdown("---")
        st.subheader("2. Thông tin chung")
        c3, c4 = st.columns(2)
        ngay_lap = c3.date_input("Ngày lập báo giá", datetime.today())
        chat_lieu_nhua = c4.text_input("Chất liệu sản phẩm (nhựa)", value="Nhựa ABS")

        st.markdown("---")
        st.subheader("3. Dành cho Báo Giá Khuôn")
        c5, c6, c7 = st.columns(3)
        ten_khuon = c5.text_input("Tên khuôn (VD: Khuôn Anten)")
        sl_khuon = c6.number_input("Số lượng khuôn", min_value=1, value=1)
        gia_khuon = c7.number_input("Giá khuôn (VNĐ)", min_value=0, value=24000000, step=1000000)

        st.markdown("---")
        st.subheader("4. Dành cho Báo Giá Sản Phẩm")
        c8, c9, c10 = st.columns(3)
        ten_san_pham = c8.text_input("Tên sản phẩm (VD: Sản phẩm Anten)")
        sl_san_pham = c9.number_input("Số lượng sản phẩm", min_value=1, value=1000)
        gia_san_pham = c10.number_input("Đơn giá sản phẩm (VNĐ)", min_value=0, value=5000, step=100)
        
        submitted_bg = st.form_submit_button("Tạo File Báo Giá (PDF)", use_container_width=True, type="primary")

    if submitted_bg:
        if not ten_cong_ty_khach:
            st.error("⚠️ Vui lòng nhập Tên doanh nghiệp / Khách hàng.")
        else:
            with st.spinner("⏳ Đang tạo các file PDF Báo Giá..."):
                context_bg = {
                    "ngay": ngay_lap.strftime("%d"),
                    "thang": ngay_lap.strftime("%m"),
                    "nam": ngay_lap.strftime("%Y"),
                    "ten_cong_ty_khach": ten_cong_ty_khach,
                    "nguoi_dai_dien": nguoi_dai_dien,
                    "ten_khuon": ten_khuon if ten_khuon else "Khuôn",
                    "sl_khuon": sl_khuon,
                    "gia_khuon_str": f"{gia_khuon:,.0f}".replace(",", "."),
                    "ten_san_pham": ten_san_pham if ten_san_pham else "Sản phẩm",
                    "sl_san_pham": f"{sl_san_pham:,.0f}".replace(",", "."),
                    "gia_san_pham_str": f"{gia_san_pham:,.0f}".replace(",", "."),
                    "chat_lieu_nhua": chat_lieu_nhua
                }

                col_down1, col_down2 = st.columns(2)

                # 1. XUẤT FILE BÁO GIÁ KHUÔN
                try:
                    pdf_bgk_bytes = export_quote_khuon_pdf(context_bg)
                    col_down1.success("✅ Báo Giá Khuôn đã sẵn sàng")
                    col_down1.download_button(
                        label="⬇️ Tải BÁO GIÁ KHUÔN",
                        data=pdf_bgk_bytes,
                        file_name=f"BaoGia_Khuon_{ten_cong_ty_khach}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                except Exception as e:
                    col_down1.error(f"Lỗi tạo Báo Giá Khuôn: {e}")
                    
                # 2. XUẤT FILE BÁO GIÁ SẢN PHẨM
                try:
                    pdf_bgsp_bytes = export_quote_sp_pdf(context_bg)
                    col_down2.success("✅ Báo Giá Sản Phẩm đã sẵn sàng")
                    col_down2.download_button(
                        label="⬇️ Tải BÁO GIÁ SẢN PHẨM",
                        data=pdf_bgsp_bytes,
                        file_name=f"BaoGia_SanPham_{ten_cong_ty_khach}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                except Exception as e:
                    col_down2.error(f"Lỗi tạo Báo Giá Sản Phẩm: {e}")


# ------------------------------------------
# MODULE I: HỢP ĐỒNG
# ------------------------------------------
elif st.session_state.current_tab == "I. Hợp Đồng":
    st.header("I. Hợp Đồng Khuôn Mẫu (PDF)")
    st.markdown("Nhập thông tin bên dưới để tự động tạo file **Hợp Đồng Sản Xuất Khuôn Mẫu**.")
    
    with st.form("form_hop_dong"):
        st.subheader("1. Thông tin Khách hàng (Bên A)")
        c1, c2 = st.columns(2)
        ten_cong_ty_khach = c1.text_input("Tên doanh nghiệp / Khách hàng")
        dia_chi_khach = c2.text_input("Địa chỉ doanh nghiệp")
        
        c3, c4, c5 = st.columns(3)
        nguoi_dai_dien = c3.text_input("Người đại diện (Ông/Bà)")
        chuc_vu = c4.text_input("Chức vụ", value="Giám Đốc")
        sdt_khach = c5.text_input("Số điện thoại")
        
        st.markdown("---")
        st.subheader("2. Thông tin Khuôn mẫu & Giao nhận")
        c6, c7 = st.columns(2)
        ten_khuon = c6.text_input("Tên khuôn (VD: Khuôn Anten)")
        sl_khuon = c7.number_input("Số lượng khuôn", min_value=1, value=1)
        
        c8, c9, c10 = st.columns(3)
        gia_khuon = c8.number_input("Giá khuôn (VNĐ)", min_value=0, value=24000000, step=1000000)
        thoi_gian_giao = c9.number_input("Thời gian giao mẫu (Ngày)", min_value=1, value=30)
        ngay_lap = c10.date_input("Ngày lập hợp đồng", datetime.today())
        
        submitted_hd = st.form_submit_button("Tạo File Hợp Đồng (PDF)", use_container_width=True, type="primary")

    if submitted_hd:
        if not ten_cong_ty_khach or not ten_khuon:
            st.error("⚠️ Vui lòng nhập Tên doanh nghiệp và Tên khuôn.")
        else:
            with st.spinner("⏳ Đang tạo file PDF Hợp Đồng..."):
                context_hd = {
                    "ngay": ngay_lap.strftime("%d"),
                    "thang": ngay_lap.strftime("%m"),
                    "nam": ngay_lap.strftime("%Y"),
                    "ten_cong_ty_khach": ten_cong_ty_khach,
                    "nguoi_dai_dien": nguoi_dai_dien,
                    "chuc_vu": chuc_vu,
                    "dia_chi_khach": dia_chi_khach,
                    "sdt_khach": sdt_khach,
                    "ten_khuon": ten_khuon,
                    "sl_khuon": sl_khuon,
                    "gia_khuon_str": f"{gia_khuon:,.0f}".replace(",", "."),
                    "thoi_gian_giao": thoi_gian_giao
                }

                # XUẤT FILE HỢP ĐỒNG
                try:
                    pdf_hd_bytes = export_contract_pdf(context_hd)
                    st.success("✅ File Hợp Đồng đã sẵn sàng!")
                    st.download_button(
                        label="⬇️ Tải xuống HỢP ĐỒNG (PDF)",
                        data=pdf_hd_bytes,
                        file_name=f"HopDong_KhuonMau_{ten_cong_ty_khach}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                except Exception as e:
                    st.error(f"Lỗi tạo Hợp Đồng PDF. Chi tiết: {e}")
