import streamlit as st

st.set_page_config(page_title="Hệ Thống WANCHI", layout="centered")

# Kiểm tra nếu chưa có biến password_correct thì tạo mới là False
if "password_correct" not in st.session_state:
    st.session_state["password_correct"] = False

def check_password():
    # Quang có thể sửa mật khẩu trực tiếp ở đây cho nhanh hoặc dùng st.secrets
    if st.session_state["pwd_input"] == "Wanchi@2026":
        st.session_state["password_correct"] = True
        del st.session_state["pwd_input"]
    else:
        st.error("❌ Mật khẩu sai rồi Quang ơi!")

# GIAO DIỆN ĐĂNG NHẬP
if not st.session_state["password_correct"]:
    st.title("🔒 ĐĂNG NHẬP HỆ THỐNG WANCHI")
    st.text_input("Nhập mật khẩu để vào các Module:", type="password", key="pwd_input")
    st.button("🚀 Vào hệ thống", on_click=check_password)
    st.stop() # Dừng tất cả nếu chưa đăng nhập đúng

# NẾU ĐÃ ĐĂNG NHẬP ĐÚNG THÌ HIỆN NỘI DUNG DƯỚI ĐÂY
st.title("🏭 CHÀO MỪNG QUANG ĐẾN VỚI WANCHI")
st.write("---")
st.success("✅ Bạn đã đăng nhập thành công.")
st.info("👈 Bây giờ bạn hãy nhìn sang Menu bên trái để chọn Module cần làm việc nhé!")