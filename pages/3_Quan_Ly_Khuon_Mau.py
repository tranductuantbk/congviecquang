# ==========================================
# GIAO DIỆN CHÍNH & LƯỚI ĐIỀU HƯỚNG 3 CỘT
# ==========================================
st.title("🏭 Công Cụ Quản Lý Khuôn Mẫu WANCHI")
st.markdown("---")

# 1. Khai báo biến lưu trạng thái Tab hiện tại
if "current_tab" not in st.session_state:
    st.session_state.current_tab = "A. Nguyên Vật Liệu"

menu_items = [
    "A. Nguyên Vật Liệu", 
    "B. Gia Công", 
    "C. Vật Tư Khuôn Mẫu", 
    "D. Tổng Giá Khuôn",
    "F. Tạo Đơn Hàng Gia Công",
    "G. Theo Dõi Đơn Hàng",
    "E. Danh Sách & Quản Trị"
]

# 2. Xây dựng lưới nút bấm tối đa 3 cột/dòng
for i in range(0, len(menu_items), 3):
    cols = st.columns(3)
    for j, col in enumerate(cols):
        if i + j < len(menu_items):
            item = menu_items[i + j]
            # Đổi màu nút (primary) nếu đang chọn
            btn_style = "primary" if st.session_state.current_tab == item else "secondary"
            if col.button(item, use_container_width=True, type=btn_style):
                st.session_state.current_tab = item
                st.rerun()

st.markdown("---")

# 3. Hiển thị nội dung tương ứng theo nút được chọn
if st.session_state.current_tab == "A. Nguyên Vật Liệu":
    st.header("A. Nguyên Vật Liệu")
    # [Giữ nguyên toàn bộ code bên trong with tab_A cũ paste vào đây]

elif st.session_state.current_tab == "B. Gia Công":
    st.header("B. Gia Công")
    # [Giữ nguyên code của tab_B paste vào đây]

elif st.session_state.current_tab == "C. Vật Tư Khuôn Mẫu":
    # Tương tự cho các Tab C, D, F, G, E...
