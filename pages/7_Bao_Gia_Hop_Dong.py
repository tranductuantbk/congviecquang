import streamlit as st
import unicodedata
from datetime import datetime
import os
from fpdf import FPDF

st.set_page_config(page_title="Báo Giá & Hợp Đồng", layout="wide")

# --- KHÓA BẢO MẬT TỪ TRANG CHỦ ---
if not st.session_state.get("logged_in", False):
    st.warning("🔒 Bạn chưa đăng nhập! Vui lòng quay lại Trang Chủ (Home) để gõ mật khẩu.")
    st.stop()

def remove_accents(input_str):
    s = str(input_str).replace('Đ', 'D').replace('đ', 'd')
    nfkd_form = unicodedata.normalize('NFKD', s)
    return u"".join([c for c in nfkd_form if not unicodedata.combining(c)])

# ==========================================
# HÀM XUẤT BÁO GIÁ PDF (MẪU GỘP KHUÔN VÀ SẢN PHẨM)
# ==========================================
def export_quote_pdf(context):
    pdf = FPDF()
    pdf.add_page()
    
    try:
        pdf.add_font('ArialVN', '', 'arial.ttf', uni=True)
        pdf.add_font('ArialVN', 'B', 'arialbd.ttf', uni=True)
        font_name = 'ArialVN'
    except:
        font_name = 'Arial'

    # Hàm bọc an toàn tránh sập hệ thống khi thiếu font
    def txt(s):
        return remove_accents(str(s)) if font_name == 'Arial' else str(s)

    # Logo (nếu có)
    logo_path = "logo.png" 
    if os.path.exists(logo_path):
        pdf.image(logo_path, x=10, y=8, w=35)

    pdf.set_font(font_name, 'B' if font_name == 'ArialVN' else '', 24)
    pdf.cell(0, 10, txt=txt("WANCHI"), ln=True, align='C')
    pdf.set_font(font_name, '', 12)
    pdf.cell(0, 6, txt=txt("www.wanchi.vn"), ln=True, align='C')
    pdf.ln(5)

    pdf.set_font(font_name, '', 10)
    pdf.multi_cell(0, 5, txt=txt("Văn Phòng: 445/87 Tân Hoà Đông P. Bình Trị Đông Q.Bình Tân."), align='L')
    pdf.multi_cell(0, 5, txt=txt("Nhà Máy: 775 Võ Hữu Lợi, Ấp 16, Xã Lê Minh Xuân, Huyện Bình Chánh, Thành phố Hồ Chí Minh"), align='L')
    pdf.cell(0, 5, txt=txt("Điện Thoại: 0937572577. A Quang"), ln=True, align='L')
    
    pdf.set_xy(10, 40)
    pdf.cell(0, 5, txt=txt(f"TP. HCM, ngày {context['ngay']} tháng {context['thang']} năm {context['nam']}"), ln=True, align='R')
    pdf.ln(10)

    pdf.set_font(font_name, 'B' if font_name == 'ArialVN' else '', 16)
    pdf.cell(0, 10, txt=txt("BÁO GIÁ KHUÔN MẪU VÀ SẢN PHẨM"), ln=True, align='C')
    pdf.ln(5)

    pdf.set_font(font_name, 'B' if font_name == 'ArialVN' else '', 11)
    pdf.multi_cell(0, 6, txt=txt(f"Người Nhận: {context['ten_cong_ty_khach']} - {context['nguoi_dai_dien']}"), align='L')
    pdf.ln(2)

    # VẼ BẢNG KẾT HỢP
    pdf.set_font(font_name, 'B' if font_name == 'ArialVN' else '', 11)
    col_w = [15, 85, 35, 40]
    pdf.cell(col_w[0], 8, txt=txt("STT"), border=1, align='C')
    pdf.cell(col_w[1], 8, txt=txt("Mô tả sản phẩm"), border=1, align='C')
    pdf.cell(col_w[2], 8, txt=txt("Hình ảnh"), border=1, align='C')
    pdf.cell(col_w[3], 8, txt=txt("Số lượng"), border=1, align='C')
    pdf.ln()

    pdf.set_font(font_name, '', 11)
    
    # 1. Dòng Khuôn
    tk_hienthi = txt(context['ten_khuon'])
    while pdf.get_string_width(tk_hienthi) > (col_w[1] - 4) and len(tk_hienthi) > 0: tk_hienthi = tk_hienthi[:-1]
    
    pdf.cell(col_w[0], 12, txt="1", border=1, align='C')
    pdf.cell(col_w[1], 12, txt=tk_hienthi, border=1, align='L')
    pdf.cell(col_w[2], 12, txt="", border=1, align='C')
    pdf.cell(col_w[3], 12, txt=txt(f"{context['sl_khuon']} khuôn"), border=1, align='C')
    pdf.ln()
    
    # 2. Dòng Sản phẩm
    tsp_hienthi = txt(context['ten_san_pham'])
    while pdf.get_string_width(tsp_hienthi) > (col_w[1] - 4) and len(tsp_hienthi) > 0: tsp_hienthi = tsp_hienthi[:-1]

    pdf.cell(col_w[0], 12, txt="2", border=1, align='C')
    pdf.cell(col_w[1], 12, txt=tsp_hienthi, border=1, align='L')
    pdf.cell(col_w[2], 12, txt="", border=1, align='C')
    pdf.cell(col_w[3], 12, txt=txt(f"{context['sl_san_pham']} Cặp"), border=1, align='C')
    pdf.ln()

    pdf.set_font(font_name, '', 10)
    pdf.cell(0, 8, txt=txt("Giá trên chưa bao gồm hóa đơn"), ln=True, align='R')
    pdf.ln(5)

    # THÔNG TIN KHUÔN
    pdf.set_font(font_name, 'B' if font_name == 'ArialVN' else '', 11)
    pdf.cell(0, 6, txt=txt("Thông Tin Khuôn:"), ln=True, align='L')
    pdf.set_font(font_name, '', 11)
    pdf.cell(0, 6, txt=txt("Nguyên Liệu sản xuất khuôn:"), ln=True, align='L')
    pdf.cell(0, 6, txt=txt("- Vỏ khuôn: Thép SC55"), ln=True, align='L')
    pdf.cell(0, 6, txt=txt("- Phôi khuôn: Thép 2083"), ln=True, align='L')
    
    pdf.set_font(font_name, 'B' if font_name == 'ArialVN' else '', 11)
    pdf.cell(0, 6, txt=txt("Giá Khuôn:"), ln=True, align='L')
    pdf.set_font(font_name, '', 11)
    pdf.multi_cell(0, 6, txt=txt(f"- Giá hoàn thiện khuôn: {context['gia_khuon_str']} (Mẫu bóng)"), align='L')
    
    pdf.set_font(font_name, 'B' if font_name == 'ArialVN' else '', 11)
    pdf.cell(0, 6, txt=txt("Bảo hành khuôn:"), ln=True, align='L')
    pdf.set_font(font_name, '', 11)
    pdf.multi_cell(0, 6, txt=txt("- Khuôn bảo hành miễn phí 5 năm hoặc 100.000 sản phẩm tại công ty."), align='L')
    pdf.ln(2)

    # THÔNG TIN SẢN PHẨM
    pdf.set_font(font_name, 'B' if font_name == 'ArialVN' else '', 11)
    pdf.cell(0, 6, txt=txt("Thông tin sản phẩm:"), ln=True, align='L')
    pdf.set_font(font_name, '', 11)
    pdf.multi_cell(0, 6, txt=txt(f"- Chất liệu sản phẩm: {context['chat_lieu_nhua']}"), align='L')
    pdf.multi_cell(0, 6, txt=txt("- 35 ngày (không tính ngày nghỉ lễ và chủ nhật) kể từ ngày nhận đặt cọc và khách hàng ký xác nhận bản vẽ sản phẩm."), align='L')
    pdf.multi_cell(0, 6, txt=txt("- Thời gian hợp đồng được tính khi ký hợp đồng"), align='L')
    pdf.ln(2)

    pdf.set_font(font_name, 'B' if font_name == 'ArialVN' else '', 11)
    pdf.cell(0, 6, txt=txt("3. Địa điểm giao hàng:"), ln=True, align='L')
    pdf.set_font(font_name, '', 11)
    pdf.cell(0, 6, txt=txt("Tại hãng sản xuất wanchi"), ln=True, align='L')
    pdf.ln(2)

    pdf.set_font(font_name, 'B' if font_name == 'ArialVN' else '', 11)
    pdf.cell(0, 6, txt=txt("4. Thanh toán:"), ln=True, align='L')
    pdf.set_font(font_name, '', 11)
    pdf.cell(0, 6, txt=txt("- 50% sau khi ký báo giá hoặc ký hợp đồng"), ln=True, align='L')
    pdf.multi_cell(0, 6, txt=txt("- 50% còn lại sau khi nhận mẫu thử hoàn chỉnh"), align='L')
    pdf.ln(2)

    pdf.set_font(font_name, 'B' if font_name == 'ArialVN' else '', 11)
    pdf.cell(0, 6, txt=txt("5. Bảo hành khuôn:"), ln=True, align='L')
    pdf.set_font(font_name, '', 11)
    pdf.multi_cell(0, 6, txt=txt("- 24 tháng hoặc 1.000.000 sản phẩm tùy theo điều kiện nào đến trước"), align='L')
    pdf.multi_cell(0, 6, txt=txt("- Khuôn được bảo hành khi sản xuất và sử dụng tại cty"), align='L')
    pdf.ln(10)
    
    pdf.set_font(font_name, '', 12)
    pdf.cell(0, 6, txt=txt("Xin chân thành cảm ơn sự tín nhiệm của quý khách hàng!"), ln=True, align='C')

    return bytes(pdf.output())

# ==========================================
# HÀM XUẤT HỢP ĐỒNG PDF
# ==========================================
def export_contract_pdf(context):
    pdf = FPDF()
    pdf.add_page()
    
    try:
        pdf.add_font('ArialVN', '', 'arial.ttf', uni=True)
        pdf.add_font('ArialVN', 'B', 'arialbd.ttf', uni=True)
        font_name = 'ArialVN'
    except:
        font_name = 'Arial'

    def txt(s):
        return remove_accents(str(s)) if font_name == 'Arial' else str(s)

    pdf.set_font(font_name, 'B' if font_name == 'ArialVN' else '', 12)
    pdf.cell(0, 6, txt=txt("CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM"), ln=True, align='C')
    pdf.cell(0, 6, txt=txt("Độc lập - Tự do - Hạnh phúc"), ln=True, align='C')
    pdf.cell(0, 6, txt=txt("----------***---------"), ln=True, align='C')
    pdf.ln(5)
    
    pdf.set_font(font_name, 'B' if font_name == 'ArialVN' else '', 16)
    pdf.cell(0, 10, txt=txt("HỢP ĐỒNG SẢN XUẤT KHUÔN MẪU"), ln=True, align='C')
    pdf.ln(2)
    
    pdf.set_font(font_name, '', 11)
    pdf.cell(0, 6, txt=txt(f"Hôm nay, ngày {context['ngay']} tháng {context['thang']} năm {context['nam']}, các bên trong hợp đồng gồm:"), ln=True, align='L')
    pdf.ln(2)
    
    pdf.set_font(font_name, 'B' if font_name == 'ArialVN' else '', 11)
    pdf.cell(0, 6, txt=txt("1. Bên A (Bên đặt hàng):"), ln=True, align='L')
    pdf.set_font(font_name, '', 11)
    
    pdf.multi_cell(0, 6, txt=txt(f"- Tên doanh nghiệp: {context['ten_cong_ty_khach']}"), align='L')
    pdf.multi_cell(0, 6, txt=txt(f"- Đại diện là Ông/Bà: {context['nguoi_dai_dien']}        Chức vụ: {context['chuc_vu']}"), align='L')
    pdf.multi_cell(0, 6, txt=txt(f"- Địa chỉ: {context['dia_chi_khach']}"), align='L')
    pdf.multi_cell(0, 6, txt=txt(f"- Điện thoại: {context['sdt_khach']}"), align='L')
    pdf.ln(2)

    pdf.set_font(font_name, 'B' if font_name == 'ArialVN' else '', 11)
    pdf.cell(0, 6, txt=txt("2. Bên B (Bên sản xuất khuôn mẫu):"), ln=True, align='L')
    pdf.set_font(font_name, '', 11)
    pdf.cell(0, 6, txt=txt("- Bà: Thái Nhuận Chi        Chức vụ: Chủ Hộ Kinh Doanh"), ln=True, align='L')
    pdf.cell(0, 6, txt=txt("- Tên doanh nghiệp: HỘ KINH DOANH WANCHI        MST: 8289829752-001"), ln=True, align='L')
    pdf.multi_cell(0, 6, txt=txt("- Địa chỉ: 775 Võ Hữu Lợi, Ấp 16, Xã Lê Minh Xuân, Huyện Bình Chánh"), align='L')
    pdf.multi_cell(0, 6, txt=txt("- Tài Khoản Ngân Hàng Sacombank - sở giao dịch: 060329421638"), align='L')
    pdf.cell(0, 6, txt=txt("- Điện thoại: 0937572577"), ln=True, align='L')
    pdf.ln(4)

    pdf.cell(0, 6, txt=txt("Hai bên thống nhất thỏa thuận lập hợp đồng với nội dung như sau:"), ln=True, align='L')
    pdf.ln(2)

    pdf.set_font(font_name, 'B' if font_name == 'ArialVN' else '', 11)
    col_w = [15, 50, 30, 15, 35, 30]
    pdf.cell(col_w[0], 8, txt=txt("STT"), border=1, align='C')
    pdf.cell(col_w[1], 8, txt=txt("Mô tả"), border=1, align='C')
    pdf.cell(col_w[2], 8, txt=txt("Hình ảnh"), border=1, align='C')
    pdf.cell(col_w[3], 8, txt=txt("SL"), border=1, align='C')
    pdf.cell(col_w[4], 8, txt=txt("Đơn giá"), border=1, align='C')
    pdf.cell(col_w[5], 8, txt=txt("Ghi chú"), border=1, align='C')
    pdf.ln()

    # Sử dụng kỹ thuật ngắt dòng Multi-cell và lấy tọa độ an toàn
    pdf.set_font(font_name, '', 10)
    x_start = pdf.get_x()
    y_start = pdf.get_y()
    
    txt_khuon = txt(context['ten_khuon'])
    pdf.set_xy(x_start + col_w[0], y_start)
    lines = max(1, int(pdf.get_string_width(txt_khuon) / col_w[1]) + 1)
    line_height = lines * 6 if lines > 1 else 12 
    
    pdf.set_xy(x_start, y_start)
    pdf.cell(col_w[0], line_height, txt="1", border=1, align='C')
    
    # Ô Mô tả
    pdf.rect(x_start + col_w[0], y_start, col_w[1], line_height) 
    pdf.set_xy(x_start + col_w[0], y_start + (line_height - lines*6)/2)
    pdf.multi_cell(col_w[1], 6, txt=txt_khuon, align='C')
    
    pdf.set_xy(x_start + col_w[0] + col_w[1], y_start)
    
    sl_hienthi = txt(str(context['sl_khuon']))
    while pdf.get_string_width(sl_hienthi) > (col_w[3] - 2) and len(sl_hienthi) > 0: sl_hienthi = sl_hienthi[:-1]
    
    gia_hienthi = txt(str(context['gia_khuon_str']))
    while pdf.get_string_width(gia_hienthi) > (col_w[4] - 2) and len(gia_hienthi) > 0: gia_hienthi = gia_hienthi[:-1]

    pdf.cell(col_w[2], line_height, txt="", border=1, align='C')
    pdf.cell(col_w[3], line_height, txt=sl_hienthi, border=1, align='C')
    pdf.cell(col_w[4], line_height, txt=gia_hienthi, border=1, align='C')
    pdf.cell(col_w[5], line_height, txt=txt("Thép: ..."), border=1, align='C')
    pdf.ln(line_height)

    pdf.set_font(font_name, 'B' if font_name == 'ArialVN' else '', 11)
    pdf.cell(sum(col_w[:4]), 8, txt=txt("Tổng"), border=1, align='C')
    pdf.cell(col_w[4], 8, txt=txt(context['gia_khuon_str']), border=1, align='C')
    pdf.set_font(font_name, '', 9)
    pdf.cell(col_w[5], 8, txt=txt("Bao gồm HĐ"), border=1, align='C')
    pdf.ln(5)

    pdf.set_font(font_name, 'B' if font_name == 'ArialVN' else '', 11)
    pdf.cell(0, 8, txt=txt("ĐIỀU 1: BẢNG KÊ CHI TIẾT KHUÔN MẪU NHƯ SAU"), ln=True, align='L')
    pdf.set_font(font_name, '', 11)
    pdf.cell(0, 6, txt=txt("Thời gian giao mẫu thử và yêu cầu kỹ thuật"), ln=True, align='L')
    pdf.multi_cell(0, 6, txt=txt(f"- Thời gian giao mẫu: {context['thoi_gian_giao']} ngày (không tính Lễ, CN) kể từ ngày nhận cọc."), align='L')
    pdf.cell(0, 6, txt=txt("- Yêu cầu kỹ thuật: Theo bản vẽ"), ln=True, align='L')
    pdf.cell(0, 6, txt=txt("- Vật tư làm mẫu: Theo bản vẽ hoặc tương đương"), ln=True, align='L')
    pdf.ln(2)

    pdf.cell(0, 6, txt=txt("1.2 Thanh toán"), ln=True, align='L')
    pdf.cell(0, 6, txt=txt("- Lần 1: 50% sau khi ký hợp đồng"), ln=True, align='L')
    pdf.cell(0, 6, txt=txt("- Lần 2: 50% còn lại sau khi nhận nghiệm thu mẫu hoàn chỉnh"), ln=True, align='L')
    pdf.ln(2)

    pdf.cell(0, 6, txt=txt("1.3 Bảo hành khuôn"), ln=True, align='L')
    pdf.cell(0, 6, txt=txt("- Theo Đơn hàng 100.000 sản phẩm."), ln=True, align='L')
    pdf.multi_cell(0, 6, txt=txt("- Khuôn được bảo quản, lưu kho miễn phí khi còn sản xuất tại công ty."), align='L')
    pdf.ln(2)

    pdf.cell(0, 6, txt=txt("1.4 Bảo mật"), ln=True, align='L')
    pdf.multi_cell(0, 6, txt=txt("Bản vẽ khuôn mẫu và khuôn mẫu thuộc về công ty khách hàng không được sử dụng cho công ty thứ 3. Nếu vi phạm chịu hoàn toàn trách nhiệm."), align='L')
    pdf.ln(4)

    pdf.set_font(font_name, 'B' if font_name == 'ArialVN' else '', 11)
    pdf.cell(0, 8, txt=txt("ĐIỀU 2: QUYỀN VÀ NGHĨA VỤ CỦA BÊN A"), ln=True, align='L')
    pdf.set_font(font_name, '', 11)
    pdf.multi_cell(0, 6, txt=txt("2.1. Bên A có các nghĩa vụ sau đây:\na) Chịu trách nhiệm đối với tính hợp pháp về quyền sở hữu trí tuệ, kiểu dáng công nghiệp và logo của khuôn mẫu.\nb) Thanh toán theo đúng tiến độ thoả thuận trong hợp đồng."), align='L')
    pdf.multi_cell(0, 6, txt=txt("2.2 Bên A có các quyền sau đây:\na) Đơn phương chấm dứt thực hiện hợp đồng và yêu cầu bồi thường thiệt hại khi bên B vi phạm nghiêm trọng hợp đồng.\nb) Trong trường hợp sản phẩm không bảo đảm chất lượng mà bên A đồng ý nhận sản phẩm và yêu cầu sửa chữa nhưng bên B không thể sửa chữa được trong thời hạn đã thoả thuận thì bên A có quyền hủy bỏ hợp đồng và yêu cầu bồi thường thiệt hại.\nc) Khuôn mẫu thuộc quyền sở hữu bên A, có quyền thu hồi khuôn bất cứ lúc nào."), align='L')
    pdf.ln(2)

    pdf.set_font(font_name, 'B' if font_name == 'ArialVN' else '', 11)
    pdf.cell(0, 8, txt=txt("ĐIỀU 3: QUYỀN VÀ NGHĨA VỤ CỦA BÊN B"), ln=True, align='L')
    pdf.set_font(font_name, '', 11)
    pdf.multi_cell(0, 6, txt=txt("3.1. Bên B có các nghĩa vụ sau đây:\na) Đảm bảo toàn bộ nguyên liệu, vật liệu để gia công theo thỏa thuận với bên A về số lượng, chất lượng, tiêu chuẩn kỹ thuật theo đúng bảng báo giá và bản vẽ bên A.\nb) Giao sản phẩm cho bên A đúng số lượng, chất lượng, phương thức, thời hạn và địa điểm đã thoả thuận.\nc) Giữ bí mật các thông tin về quy trình gia công và sản phẩm tạo ra."), align='L')
    pdf.multi_cell(0, 6, txt=txt("3.2. Bên B có các quyền sau đây:\na) Từ chối sự chỉ dẫn không hợp lý của bên A, nếu thấy chỉ dẫn đó có thể làm giảm chất lượng sản phẩm, nhưng phải báo ngay cho bên A.\nb) Yêu cầu bên A trả đủ tiền công theo đúng thời hạn và phương thức đã thoả thuận."), align='L')
    pdf.ln(4)

    pdf.cell(0, 6, txt=txt("Hợp đồng này được làm thành 2 bản có giá trị như nhau, mỗi bên giữ 1 bản."), ln=True, align='L')
    pdf.ln(10)
    
    pdf.set_font(font_name, 'B' if font_name == 'ArialVN' else '', 12)
    pdf.cell(85, 6, txt=txt("ĐẠI DIỆN BÊN A"), align='C')
    pdf.cell(85, 6, txt=txt("ĐẠI DIỆN BÊN B"), ln=True, align='C')

    return bytes(pdf.output())

# ==========================================
# GIAO DIỆN CHÍNH
# ==========================================
st.title("📝 Công Cụ Tạo Báo Giá & Hợp Đồng")
st.markdown("---")

tab1, tab2 = st.tabs(["📑 BÁO GIÁ", "🤝 HỢP ĐỒNG"])

# ------------------------------------------
# TAB 1: BÁO GIÁ
# ------------------------------------------
with tab1:
    st.header("Báo Giá Khuôn & Sản Phẩm (Xuất PDF)")
    st.markdown("Hệ thống tạo 1 file **PDF Báo Giá** kết hợp khuôn và sản phẩm theo chuẩn Form của Công ty.")
    
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
        
        submitted_bg = st.form_submit_button("Tạo File Báo Giá (PDF)", use_container_width=True, type="primary")

    if submitted_bg:
        if not ten_cong_ty_khach:
            st.error("⚠️ Vui lòng nhập Tên doanh nghiệp / Khách hàng.")
        else:
            with st.spinner("⏳ Đang tạo file PDF Báo Giá..."):
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
                    "chat_lieu_nhua": chat_lieu_nhua
                }

                try:
                    pdf_bg_bytes = export_quote_pdf(context_bg)
                    st.success("✅ File Báo Giá đã sẵn sàng!")
                    st.download_button(
                        label="⬇️ Tải xuống BÁO GIÁ (PDF)",
                        data=pdf_bg_bytes,
                        file_name=f"BaoGia_KhuonVaSP_{remove_accents(ten_cong_ty_khach)}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                except Exception as e:
                    st.error(f"Lỗi tạo Báo Giá: {e}")

# ------------------------------------------
# TAB 2: HỢP ĐỒNG
# ------------------------------------------
with tab2:
    st.header("Hợp Đồng Khuôn Mẫu (Xuất PDF)")
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

                try:
                    pdf_hd_bytes = export_contract_pdf(context_hd)
                    st.success("✅ File Hợp Đồng đã sẵn sàng!")
                    st.download_button(
                        label="⬇️ Tải xuống HỢP ĐỒNG (PDF)",
                        data=pdf_hd_bytes,
                        file_name=f"HopDong_KhuonMau_{remove_accents(ten_cong_ty_khach)}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                except Exception as e:
                    st.error(f"Lỗi tạo Hợp Đồng PDF. Chi tiết: {e}")
