import streamlit as st

# 1. Cấu hình trang phải nằm trên cùng
st.set_page_config(page_title="Hệ Thống Quang", layout="wide", initial_sidebar_state="expanded")

# 2. Khởi tạo bộ nhớ đăng nhập
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# 3. Hàm giao diện Đăng Nhập
def login_screen():
    # Lệnh CSS giấu thanh Sidebar bên trái khi chưa đăng nhập
    st.markdown("""
    <style>
        [data-testid="collapsedControl"] {display: none;}
        [data-testid="stSidebar"] {display: none;}
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown("<h1 style='text-align: center; margin-top: 50px;'>🔒 HỆ THỐNG WANCHI</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: gray;'>Vui lòng nhập mật khẩu để vào phần mềm</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        pwd = st.text_input("Mật khẩu:", type="password", placeholder="Nhập pass...")
        if st.button("🚀 ĐĂNG NHẬP", use_container_width=True):
            if pwd == "tbk1102":  # <-- Mật khẩu đồng nhất
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
    # NẾU ĐÃ ĐĂNG NHẬP: Hiển thị Nút Đăng Xuất và Tải các Module của bạn lên
    st.sidebar.markdown("### 🏭 BẢNG ĐIỀU KHIỂN")
    st.sidebar.button("Đăng Xuất", on_click=logout, use_container_width=True)
    st.sidebar.markdown("---")
    
    # Khai báo đường dẫn tới các file module của bạn theo đúng tên và thư mục modules/
    pages = {
        "QUẢN LÝ CÔNG VIỆC": [
            st.Page("modules/0_Quản lý công việc.py", title="⚙️ Quản Lý Công Việc", icon="⚙️")
        ],
        "CÔNG CỤ TÍNH TOÁN & QUẢN LÝ": [
            st.Page("modules/2_Tính giá gia công.py", title="⚙️ Tính Giá Gia Công", icon="2️⃣"),
            st.Page("modules/3_Tính giá sản xuất.py", title="💰 Tính Giá Sản Xuất", icon="3️⃣"),
            st.Page("modules/4_Quản lý khuôn mẫu.py", title="🏭 Quản Lý Khuôn Mẫu", icon="4️⃣"),
            st.Page("modules/5_Tạo đơn đặt hàng.py", title="📦 Quản Lý Giao Việc", icon="5️⃣"),
            st.Page("modules/6_Tính giá cost.py", title="📊 Tính Giá Cost", icon="6️⃣"),
            st.Page("modules/7_Tính trọng lượng.py", title="⚖️ Tính Trọng Lượng", icon="7️⃣")
        ]
    }
    
    # Chạy menu điều hướng
    pg = st.navigation(pages)
    pg.run()
