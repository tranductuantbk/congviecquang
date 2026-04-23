import streamlit as st

st.set_page_config(page_title="Hệ Thống WANCHI", layout="centered")

# Khởi tạo bộ nhớ đăng nhập
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# --- NẾU CHƯA ĐĂNG NHẬP: GIẤU MENU VÀ HIỆN FORM ĐĂNG NHẬP ---
if not st.session_state.logged_in:
    # Lệnh CSS giấu thanh Sidebar bên trái
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
            if pwd == "tuanquang":  # <-- BẠN CÓ THỂ ĐỔI PASS Ở ĐÂY
                st.session_state.logged_in = True
                st.rerun() # Tải lại trang để bung menu
            else:
                st.error("❌ Sai mật khẩu! Vui lòng thử lại.")

# --- NẾU ĐÃ ĐĂNG NHẬP: HIỆN TRANG CHỦ VÀ MENU ---
else:
    st.title("🏭 CHÀO MỪNG ĐẾN VỚI WANCHI")
    st.write("---")
    st.success("✅ Đăng nhập thành công!")
    st.info("👈 Thanh Menu bên trái đã được mở khóa. Bạn hãy click vào Menu góc trên cùng bên trái để chọn Module làm việc nhé!")
    
    if st.button("Đăng Xuất"):
        st.session_state.logged_in = False
        st.rerun()
