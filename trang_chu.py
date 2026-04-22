import streamlit as st

# Cấu hình toàn bộ ứng dụng (chỉ được gọi 1 lần ở trang chủ)
st.set_page_config(
    page_title="Công Việc Quang",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Hiển thị tiêu đề
st.title("🚀 QUẢN LÝ CÔNG VIỆC CỦA QUANG")
st.markdown("---")

# Nội dung chào mừng
st.markdown("""
### Chào mừng Quang đến với Hệ thống Quản lý Cá nhân!
Đây là trung tâm điều hành mọi công việc. Hệ thống được thiết kế theo cấu trúc module đa trang rất chuyên nghiệp.

👈 **Hướng dẫn:**
1. Hãy nhìn sang thanh menu bên trái (Sidebar).
2. Click vào các module tương ứng để bắt đầu làm việc.
""")

st.info("💡 Hệ thống hiện đang chạy phiên bản ổn định nhất.")