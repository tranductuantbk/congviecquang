import streamlit as st

st.set_page_config(page_title="Hệ Thống Quang", layout="wide", initial_sidebar_state="expanded")

# Khởi tạo bộ nhớ đăng nhập
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# --- NẾU CHƯA ĐĂNG NHẬP: GIẤU MENU VÀ HIỆN FORM ĐĂNG NHẬP ---
if not st.session_state.logged_in:
    # Lệnh CSS giấu toàn bộ thanh Sidebar bên trái và Menu tự động
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
        pwd = st.text_input("Mật khẩu:", type="password", placeholder="Nhập mật khẩu...")
        if st.button("🚀 ĐĂNG NHẬP", use_container_width=True):
            if pwd == "tbk1102": 
                st.session_state.logged_in = True
                st.rerun() 
            else:
                st.error("❌ Sai mật khẩu! Vui lòng thử lại.")

# --- NẾU ĐÃ ĐĂNG NHẬP: BUNG MENU TỰ ĐỘNG ---
else:
    # Ở đây chúng ta KHÔNG dùng st.navigation nữa.
    # Streamlit sẽ tự động quét thư mục "pages" và vẽ ra Sidebar bên trái.
    
    st.title("🏭 CHÀO MỪNG QUANG ĐẾN VỚI HỆ THỐNG")
    st.write("---")
    st.success("✅ Đăng nhập thành công!")
    st.info("👈 Thanh Menu bên trái đã được mở khóa. Hãy click vào các Module để làm việc.")
    
    if st.sidebar.button("Đăng Xuất", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()
