import streamlit as st

# 1. Cấu hình trang phải nằm trên cùng
st.set_page_config(page_title="Hệ Thống WANCHI", layout="wide", initial_sidebar_state="expanded")

# 2. Khởi tạo bộ nhớ đăng nhập
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# 3. Hàm giao diện Đăng Nhập
def login_screen():
    st.markdown("<h1 style='text-align: center; margin-top: 50px;'>🔒 HỆ THỐNG WANCHI</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: gray;'>Vui lòng nhập mật khẩu để vào phần mềm</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        pwd = st.text_input("Mật khẩu:", type="password", placeholder="Nhập pass...")
        if st.button("🚀 ĐĂNG NHẬP", use_container_width=True):
            if pwd == "Wanchi@2026":  # <-- BẠN CÓ THỂ ĐỔI PASS Ở ĐÂY
                st.session_state.logged_in = True
                st.rerun() # Tải lại trang để bung menu
            else:
                st.error("❌ Sai mật khẩu! Thử lại nhé.")

# 4. Hàm Đăng xuất
def logout():
    st.session_state.logged_in = False

# ==========================================
# 5. HỆ THỐNG ĐIỀU HƯỚNG (PHÂN LUỒNG)
# ==========================================
if not st.session_state.logged_in:
    # NẾU CHƯA ĐĂNG NHẬP: Ép hệ thống chỉ có 1 trang duy nhất là trang Login
    login_page = st.Page(login_screen, title="Đăng Nhập", icon="🔒")
    pg = st.navigation([login_page])
    pg.run()
    
else:
    # NẾU ĐÃ ĐĂNG NHẬP: Hiển thị Nút Đăng Xuất và Tải 3 Module của bạn lên
    st.sidebar.markdown("### 🏭 BẢNG ĐIỀU KHIỂN")
    st.sidebar.button("Đăng Xuất", on_click=logout, use_container_width=True)
    st.sidebar.markdown("---")
    
    # Khai báo đường dẫn tới 3 file của bạn
    mod1 = st.Page("modules/1_Tinh_Gia_San_Xuat.py", title="1. Tính Giá Sản Xuất", icon="🧮")
    mod2 = st.Page("modules/2_Tinh_Gia_Gia_Cong.py", title="2. Tính Giá Gia Công", icon="⚙️")
    mod3 = st.Page("modules/3_Quan_Ly_Khuon_Mau.py", title="3. Quản Lý Khuôn", icon="🏭")
    
    # Chạy menu điều hướng
    pg = st.navigation([mod1, mod2, mod3])
    pg.run()