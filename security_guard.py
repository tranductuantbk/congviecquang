# File: security_guard.py
import streamlit as st
from sqlalchemy import text

def verify_database_connection(conn):
    """
    Hàm kiểm tra kết nối thực tế đến Database.
    Trả về True nếu kết nối sống, False nếu lỗi.
    """
    try:
        # Chạy một truy vấn siêu nhẹ để kiểm tra Database có phản hồi không
        with conn.session as session:
            session.execute(text("SELECT 1"))
        return True
    except Exception as e:
        return False

def setup_global_shield(conn):
    """
    Kích hoạt lá chắn bảo vệ. Hàm này phải được gọi ở ĐẦU MỖI TRANG.
    """
    # 1. Kiểm tra đăng nhập (Bảo mật 1)
    if not st.session_state.get("logged_in", False):
        st.warning("🔒 Bạn chưa đăng nhập! Vui lòng quay lại Trang Chủ (Home) để gõ mật khẩu.")
        st.stop()
        
    # 2. Kiểm tra trạng thái tải DB (Bảo mật 2 - Chống ghi đè)
    if "db_load_success" not in st.session_state:
        st.session_state["db_load_success"] = False
        
    # Thực hiện Ping tới Neon mỗi lần tải trang
    is_connected = verify_database_connection(conn)
    st.session_state["db_load_success"] = is_connected
    
    if not is_connected:
        st.error("🚨 HỆ THỐNG ĐANG BỊ KHÓA AN TOÀN 🚨")
        st.error("⏳ Máy chủ cơ sở dữ liệu (Neon) đang ngủ đông hoặc mất kết nối mạng.")
        st.warning("👉 Hệ thống đã tự động vô hiệu hóa mọi chức năng Lưu / Thêm / Sửa / Xóa để bảo vệ dữ liệu. Vui lòng ấn F5 (Tải lại trang) cho đến khi thông báo này biến mất.")
        # Dừng toàn bộ code giao diện bên dưới nếu DB chết, ngăn người dùng thao tác mù
        st.stop()