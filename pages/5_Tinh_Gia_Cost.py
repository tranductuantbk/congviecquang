import streamlit as st
import pandas as pd
from datetime import datetime
import os
from sqlalchemy import text

# --- KHÓA BẢO MẬT TỪ TRANG CHỦ ---
if not st.session_state.get("logged_in", False):
    st.warning("🔒 Bạn chưa đăng nhập! Vui lòng quay lại Trang Chủ (Home) để gõ mật khẩu.")
    st.stop()

st.set_page_config(page_title="WANCHI - Tính Giá Cost (Báo Giá)", layout="wide")

# ==========================================
# CẤU HÌNH & KẾT NỐI DB
# ==========================================
try:
    conn = st.connection("postgresql", type="sql")
except Exception as e:
    st.error("Chưa thể kết nối đến cơ sở dữ liệu.")
    st.stop()

# Khởi tạo bảng tạm thời trong session_state để người dùng nhập liệu linh hoạt
if "costing_items" not in st.session_state:
    st.session_state.costing_items = pd.DataFrame(columns=[
        "Nhóm chi phí", "Tên hạng mục", "Đơn vị", "Số lượng / Thời gian", "Đơn giá cost", "Tổng cộng"
    ])

# ==========================================
# GIAO DIỆN CHÍNH
# ==========================================
st.title("🧮 Hệ Thống Tính Giá Cost & Báo Giá")
st.markdown("Công cụ linh hoạt áp dụng cho mọi ngành nghề (Cơ khí, Ép nhựa, Nội thất, Gia công chế tạo...).")
st.markdown("---")

# TẦNG 1: THÔNG TIN DỰ ÁN & LÔ HÀNG
col_info1, col_info2, col_info3 = st.columns(3)
ten_sp = col_info1.text_input("Tên Sản phẩm / Tên dự án cần tính giá:")
khach_hang = col_info2.text_input("Tên Khách hàng (Nếu có):")
so_luong_lo = col_info3.number_input("Số lượng sản xuất (Cái/Bộ):", min_value=1, value=1, step=1, 
                                     help="Rất quan trọng để chia đều chi phí ra đơn giá 1 sản phẩm.")

st.markdown("---")

# TẦNG 2: BẢNG NHẬP LIỆU CHI PHÍ LINH HOẠT (BOM)
st.subheader("1. Bảng Khai Báo Chi Phí (Giá Vốn)")
st.info("💡 Hướng dẫn: Cuộn xuống cuối bảng, bấm dấu '+' để thêm dòng mới. Bạn có thể tự do gõ tên Vật liệu hoặc Tên máy móc.")

# Cấu hình data_editor cực kỳ chuyên nghiệp
edited_cost_df = st.data_editor(
    st.session_state.costing_items,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "Nhóm chi phí": st.column_config.SelectboxColumn(
            "Nhóm chi phí",
            help="Phân loại để dễ quản lý",
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
        "Đơn vị": st.column_config.TextColumn("ĐVT (kg, giờ, ngày, cái...)"),
        "Số lượng / Thời gian": st.column_config.NumberColumn("Số lượng / Thời gian", min_value=0.0, format="%.2f"),
        "Đơn giá cost": st.column_config.NumberColumn("Đơn giá (VNĐ)", min_value=0, step=1000, format="%d"),
        "Tổng cộng": st.column_config.NumberColumn("Thành tiền (VNĐ)", disabled=True) # Cột này hệ thống tự tính
    },
    key="costing_editor"
)

# Logic tự động nhân Số lượng x Đơn giá
tong_chi_phi_goc = 0
if not edited_cost_df.empty:
    edited_cost_df["Số lượng / Thời gian"] = pd.to_numeric(edited_cost_df["Số lượng / Thời gian"], errors="coerce").fillna(0)
    edited_cost_df["Đơn giá cost"] = pd.to_numeric(edited_cost_df["Đơn giá cost"], errors="coerce").fillna(0)
    # Tự động tính Thành tiền
    edited_cost_df["Tổng cộng"] = edited_cost_df["Số lượng / Thời gian"] * edited_cost_df["Đơn giá cost"]
    
    # Tính tổng giá vốn
    tong_chi_phi_goc = edited_cost_df["Tổng cộng"].sum()

st.markdown("---")

# TẦNG 3: BẢNG TỔNG HỢP & CHIẾN LƯỢC GIÁ BÁN
st.subheader("2. Chốt Giá & Lợi Nhuận")

col_sum1, col_sum2 = st.columns([1, 1.5])

with col_sum1:
    with st.container(border=True):
        st.markdown(f"### Tổng Chi Phí Gốc: **{tong_chi_phi_goc:,.0f} VNĐ**")
        
        # Các biến số rủi ro và lợi nhuận
        hao_hut = st.slider("Tỷ lệ hao hụt / Rủi ro (%)", 0, 30, 5, help="Dự phòng hư hỏng, lỗi, chạy thử máy.")
        loi_nhuan = st.slider("Biên lợi nhuận mong muốn (%)", 0, 100, 20, help="Phần lời công ty giữ lại.")
        
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

# Nút Lưu lại Báo giá vào Hệ thống
st.markdown("---")
col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 2])
if col_btn1.button("💾 Lưu Bảng Báo Giá Này"):
    if not ten_sp:
        st.error("Vui lòng nhập tên Sản phẩm / Dự án trước khi lưu!")
    else:
        st.info("Tính năng kết nối lưu báo giá (Có thể phát triển thêm chức năng lưu thành Lịch sử báo giá).")
        
if col_btn2.button("🔄 Làm mới Bảng tính"):
    st.session_state.costing_items = pd.DataFrame(columns=[
        "Nhóm chi phí", "Tên hạng mục", "Đơn vị", "Số lượng / Thời gian", "Đơn giá cost", "Tổng cộng"
    ])
    st.rerun()