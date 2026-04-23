import streamlit as st

# --- CẤU HÌNH TRANG CHỦ ---
st.set_page_config(page_title="Hệ Thống WANCHI", layout="centered", initial_sidebar_state="collapsed")

# Khởi tạo trạng thái đăng nhập
if "password_correct" not in st.session_state:
    st.session_state["password_correct"] = False

# Hàm xử lý khi ấn nút Đăng nhập
def check_password():
    if st.session_state["pwd_input"] == st.secrets["APP_PASSWORD"]:
        st.session_state["password_correct"] = True
        del st.session_state["pwd_input"] # Xóa pass khỏi bộ nhớ cho an toàn
    else:
        st.session_state["password_correct"] = False

# --- GIAO DIỆN KIỂM TRA MẬT KHẨU ---
if not st.session_state["password_correct"]:
    st.markdown("<h1 style='text-align: center; margin-top: 50px;'>🔒 HỆ THỐNG WANCHI</h1>", unsafe_allow_html=True)
    st.markdown("<h4 style='text-align: center; color: #555;'>Vui lòng nhập mật khẩu để truy cập phần mềm</h4>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.text_input(
            "Mật khẩu:", 
            type="password", 
            key="pwd_input", 
            on_change=check_password,
            placeholder="Nhập mật khẩu tại đây..."
        )
        if st.button("🚀 ĐĂNG NHẬP", use_container_width=True):
            check_password()
            
        if "pwd_input" not in st.session_state and st.session_state.get("password_correct") is False:
             st.error("❌ Mật khẩu không chính xác! Vui lòng thử lại.")
             
else:
    # NẾU NHẬP ĐÚNG PASS -> HIỆN TRANG CHỦ
    st.title("🏭 CHÀO MỪNG ĐẾN VỚI HỆ THỐNG WANCHI")
    st.markdown("---")
    st.success("✅ Đăng nhập thành công! Bạn có quyền truy cập tất cả các Module.")
    
    st.markdown("### 📌 Bảng Điều Khiển (Dashboard)")
    st.info("👈 **Hãy mở thanh Menu bên trái màn hình (Sidebar) để chọn các Module tính toán:**")
    st.markdown("- **Module 1:** Tính Giá Sản Xuất")
    st.markdown("- **Module 2:** Tính Giá Gia Công")
    st.markdown("- **Module 3:** Quản Lý Khuôn Mẫu")
    
    # Tùy chọn: Nút Đăng xuất
    if st.button("Đăng Xuất"):
        st.session_state["password_correct"] = False
        st.rerun()