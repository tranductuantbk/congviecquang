import streamlit as st
import pandas as pd
from sqlalchemy import text, inspect
import time
import io
import zipfile
from datetime import datetime

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="Quản Trị Hệ Thống", page_icon="⚙️", layout="wide")

# --- KHÓA BẢO MẬT ĐĂNG NHẬP ---
if not st.session_state.get("logged_in", False):
    st.warning("🔒 Bạn chưa đăng nhập! Vui lòng quay lại Trang Chủ (Home) để gõ mật khẩu.")
    st.stop()

# ==========================================
# KẾT NỐI NEON & LÍNH GÁC BẢO VỆ
# ==========================================
try:
    conn = st.connection("postgresql", type="sql")
except Exception as e:
    st.error("Chưa thể kết nối Database Neon. Vui lòng kiểm tra lại file cấu hình Secrets.")
    st.stop()

def verify_database_connection(conn_obj, max_retries=3, delay=2):
    for attempt in range(max_retries):
        try:
            with conn_obj.session as session:
                session.execute(text("SELECT 1"))
            return True
        except Exception:
            if attempt < max_retries - 1:
                time.sleep(delay)
            else:
                return False

if "db_load_success" not in st.session_state:
    st.session_state["db_load_success"] = False

is_connected = verify_database_connection(conn)
st.session_state["db_load_success"] = is_connected

if not is_connected:
    st.error("🚨 HỆ THỐNG ĐANG BỊ KHÓA AN TOÀN 🚨")
    st.error("⏳ Máy chủ cơ sở dữ liệu (Neon) đang ngủ đông hoặc đứt kết nối mạng.")
    st.warning("👉 Không thể thực hiện Sao lưu / Phục hồi lúc này. Vui lòng ấn F5 (Tải lại trang).")
    st.stop()

# ==========================================
# KHỞI TẠO BẢNG LƯU TRỮ CẤU HÌNH QUẢN TRỊ
# ==========================================
try:
    with conn.session as session:
        session.execute(text("""
            CREATE TABLE IF NOT EXISTS public.quan_tri_config (
                key_name TEXT PRIMARY KEY,
                key_value TEXT
            )
        """))
        session.commit()
except Exception:
    pass

# Lấy thông tin ngày backup gần nhất
last_backup_date = None
try:
    with conn.session as session:
        result = session.execute(text("SELECT key_value FROM public.quan_tri_config WHERE key_name='last_backup_date'")).fetchone()
        if result:
            last_backup_date = datetime.strptime(result[0], "%Y-%m-%d")
except Exception:
    pass

# ==========================================
# GIAO DIỆN QUẢN TRỊ TRUNG TÂM
# ==========================================
st.title("⚙️ BẢNG ĐIỀU KHIỂN QUẢN TRỊ TRUNG TÂM")
st.markdown("Khu vực dành riêng cho Quản lý để **Sao lưu (Backup)** và **Phục hồi (Restore)** toàn bộ dữ liệu hệ thống.")
st.write("---")

# --- CẢNH BÁO SAU 30 NGÀY CHƯA BACKUP ---
if last_backup_date:
    days_since = (datetime.today() - last_backup_date).days
    if days_since > 30:
        st.error(f"🚨 **CẢNH BÁO TỚI HẠN SAO LƯU:** Đã **{days_since} ngày** kể từ lần sao lưu cuối cùng (ngày {last_backup_date.strftime('%d/%m/%Y')}). Vui lòng tạo bản sao lưu mới để phòng tránh rủi ro mất dữ liệu!")
    else:
        st.success(f"✅ Dữ liệu an toàn. Lần sao lưu gần nhất: **{last_backup_date.strftime('%d/%m/%Y')}** ({days_since} ngày trước).")
else:
    st.warning("⚠️ Hệ thống chưa ghi nhận bất kỳ bản sao lưu nào. Vui lòng tạo bản sao lưu đầu tiên!")

st.write("---")


col_backup, col_restore = st.columns(2)

# ------------------------------------------
# KHU VỰC 1: SAO LƯU TỰ ĐỘNG (BACKUP)
# ------------------------------------------
with col_backup:
    st.header("📥 1. Tải Bản Sao Lưu (Backup)")
    st.info("Hệ thống có radar tự động nhận diện tất cả các bảng dữ liệu hiện có trên đám mây để đóng gói thành 1 file `.zip`.")
    
    if st.button("📦 BẮT ĐẦU TẠO BẢN SAO LƯU", use_container_width=True):
        with st.spinner("⏳ Đang quét toàn bộ hệ thống và nén file..."):
            zip_buffer = io.BytesIO()
            
            # BƯỚC 1: RADAR QUÉT TÌM TẤT CẢ CÁC BẢNG TRÊN DATABASE
            try:
                inspector = inspect(conn.engine)
                all_tables = inspector.get_table_names()
            except Exception as e:
                st.error(f"Lỗi khi quét hệ thống: {e}")
                all_tables = []
            
            # BƯỚC 2: TỰ ĐỘNG LẶP VÀ ĐÓNG GÓI
            if all_tables:
                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED, False) as zip_file:
                    so_luong_bang = 0
                    for table_name in all_tables:
                        try:
                            # Bỏ qua các bảng hệ thống tự sinh của PostgreSQL nếu có
                            if table_name.startswith("pg_") or table_name.startswith("sql_"):
                                continue
                                
                            # Rút dữ liệu từng bảng
                            df = pd.read_sql(f"SELECT * FROM {table_name}", con=conn.engine)
                            if not df.empty:
                                # Chuyển thành CSV chuẩn tiếng Việt
                                csv_data = df.to_csv(index=False).encode('utf-8-sig')
                                zip_file.writestr(f"{table_name}.csv", csv_data)
                                so_luong_bang += 1
                        except Exception:
                            pass
                
                st.session_state["backup_zip"] = zip_buffer.getvalue()
                
                # BƯỚC 3: CẬP NHẬT LẠI NGÀY BACKUP VÀO DATABASE
                try:
                    today_str = datetime.today().strftime("%Y-%m-%d")
                    with conn.session as session:
                        session.execute(text(f"""
                            INSERT INTO public.quan_tri_config (key_name, key_value) 
                            VALUES ('last_backup_date', '{today_str}')
                            ON CONFLICT (key_name) DO UPDATE SET key_value = EXCLUDED.key_value
                        """))
                        session.commit()
                except Exception:
                    pass

                st.success(f"✅ Đã quét thấy và đóng gói thành công {so_luong_bang} module dữ liệu!")
                time.sleep(1)
                st.rerun() # Refresh để cập nhật lại thông báo ngày
            else:
                st.warning("⚠️ Không tìm thấy bảng dữ liệu nào trên đám mây.")
        
    if "backup_zip" in st.session_state:
        st.download_button(
            label="⬇️ CLICK VÀO ĐÂY ĐỂ TẢI FILE ZIP VỀ MÁY",
            data=st.session_state["backup_zip"],
            file_name=f"congviecquang backup {datetime.today().strftime('%d %m %Y')}.zip",
            mime="application/zip",
            type="primary",
            use_container_width=True
        )

# ------------------------------------------
# KHU VỰC 2: PHỤC HỒI (RESTORE)
# ------------------------------------------
with col_restore:
    st.header("🔥 2. Phục Hồi Sự Cố (Restore)")
    st.error("⚠️ **CẢNH BÁO NGUY HIỂM:** Khi nạp file Backup vào đây, hệ thống sẽ tự động đối chiếu tên file và xóa sạch dữ liệu cũ để ghi đè dữ liệu phục hồi lên đám mây.")
    
    uploaded_zip = st.file_uploader("Kéo thả file Backup (.zip) vào đây", type="zip")
    
    if uploaded_zip is not None:
        if st.button("🚨 XÁC NHẬN GHI ĐÈ PHỤC HỒI", type="primary", use_container_width=True):
            
            # Kiểm tra Lính gác lần cuối
            if not st.session_state.get("db_load_success", False):
                st.error("Mạng đang mất kết nối, từ chối ghi đè dữ liệu để đảm bảo an toàn.")
                st.stop()
                
            with st.spinner("⏳ Đang bung file ZIP và phân bổ dữ liệu về từng module..."):
                try:
                    with zipfile.ZipFile(uploaded_zip) as z:
                        for filename in z.namelist():
                            if filename.endswith('.csv'):
                                table_name = filename.replace('.csv', '')
                                
                                with z.open(filename) as f:
                                    df_restore = pd.read_csv(f)
                                    df_restore.to_sql(table_name, con=conn.engine, if_exists='replace', index=False)
                                    
                    st.success("🎉 PHỤC HỒI THÀNH CÔNG! Mọi thứ đã quay về thời điểm sao lưu. Vui lòng bấm F5 (Tải lại trang).")
                    time.sleep(3)
                except Exception as e:
                    st.error(f"❌ Lỗi trong quá trình phục hồi: {e}")