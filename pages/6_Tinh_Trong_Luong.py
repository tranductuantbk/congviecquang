import streamlit as st
import pandas as pd
from datetime import datetime
from sqlalchemy import text
import json

# --- KHÓA BẢO MẬT TỪ TRANG CHỦ ---
if not st.session_state.get("logged_in", False):
    st.warning("🔒 Bạn chưa đăng nhập! Vui lòng quay lại Trang Chủ (Home) để gõ mật khẩu.")
    st.stop()

st.set_page_config(page_title="WANCHI - Tính Trọng Lượng Sản Phẩm", layout="wide")

# ==========================================
# CẤU HÌNH & KẾT NỐI DB
# ==========================================
try:
    conn = st.connection("postgresql", type="sql")
except Exception as e:
    st.error("Chưa thể kết nối đến cơ sở dữ liệu.")
    st.stop()

# ==========================================
# QUẢN LÝ DỮ LIỆU ĐÁM MÂY (BẢN VÁ LỖI CHỐNG SẬP CLOUD)
# ==========================================
@st.cache_data(show_spinner=False, ttl=86400) 
def fetch_data_from_db(table_name):
    try:
        return conn.query(f'SELECT * FROM "{table_name}"', ttl=0)
    except Exception:
        return pd.DataFrame()

def force_reload_cache():
    fetch_data_from_db.clear()

def load_data(table_name, columns):
    df = fetch_data_from_db(table_name)
    if df.empty:
        return pd.DataFrame(columns=columns)
    for col in columns:
        if col not in df.columns:
            df[col] = None
    return df

def append_data(new_row_dict, table_name, df_current):
    try:
        df_new = pd.DataFrame([new_row_dict])
        df_new.to_sql(table_name, con=conn.engine, if_exists='append', index=False)
        force_reload_cache()
    except Exception:
        try:
            df_combined = pd.concat([df_current, pd.DataFrame([new_row_dict])], ignore_index=True)
            df_combined.to_sql(table_name, con=conn.engine, if_exists='replace', index=False)
            force_reload_cache()
        except Exception as e2:
            st.error(f"⚠️ Lỗi cấu trúc: {str(e2)}")

def save_data(df, table_name):
    try:
        # Sử dụng lệnh ghi đè trực tiếp để tránh lỗi Transaction Rollback trên Neon DB
        df.to_sql(table_name, con=conn.engine, if_exists='replace', index=False)
        force_reload_cache()
    except Exception as e:
        st.error(f"⚠️ Lỗi khi lưu dữ liệu lên đám mây ({table_name}): {str(e)}")

# ==========================================
# KHỞI TẠO BẢNG TỪ ĐIỂN TỈ TRỌNG NHỰA
# ==========================================
DEFAULT_PLASTICS = [
    {"Tên nhựa": "Nhựa ABS", "Tỉ trọng (g/cm3)": 1.04},
    {"Tên nhựa": "Nhựa PP", "Tỉ trọng (g/cm3)": 0.90},
    {"Tên nhựa": "Nhựa PC", "Tỉ trọng (g/cm3)": 1.20},
    {"Tên nhựa": "Nhựa POM", "Tỉ trọng (g/cm3)": 1.41},
    {"Tên nhựa": "Nhựa PVC", "Tỉ trọng (g/cm3)": 1.38}
]

df_plastics = load_data("wanchi_plastics", ["Tên nhựa", "Tỉ trọng (g/cm3)"])
if df_plastics.empty:
    df_plastics = pd.DataFrame(DEFAULT_PLASTICS)
    save_data(df_plastics, "wanchi_plastics")

# Loại bỏ trùng lặp nếu có
df_plastics = df_plastics.loc[:, ~df_plastics.columns.duplicated()]

# ==========================================
# KHỞI TẠO BẢNG LỊCH SỬ TÍNH TRỌNG LƯỢNG
# ==========================================
cols_Weights = ["Ngày", "Khách hàng", "Tên sản phẩm", "Loại nhựa", "Tỉ trọng áp dụng", "Tổng trọng lượng (gram)", "Chi tiết khối"]
df_Weights = load_data("wanchi_weights", cols_Weights)
df_Weights = df_Weights.loc[:, ~df_Weights.columns.duplicated()]

# Biến tạm lưu các dòng tính toán
if "weight_items" not in st.session_state:
    st.session_state.weight_items = pd.DataFrame(columns=[
        "Tên/Khu vực bộ phận", "Dài (mm)", "Rộng (mm)", "Dày (mm)", "Thể tích (cm3)", "Trọng lượng (gram)"
    ])

# ==========================================
# GIAO DIỆN CHÍNH
# ==========================================
st.title("⚖️ Công Cụ Tính Trọng Lượng Sản Phẩm Nhựa")
st.markdown("Quy đổi tự động từ Kích thước sang Thể tích và Trọng lượng dựa theo tỉ trọng của từng loại nguyên vật liệu.")
st.markdown("---")

tab_TinhToan, tab_LichSu, tab_CauHinh = st.tabs(["🧩 TÍNH TRỌNG LƯỢNG", "🗂️ LỊCH SỬ ĐÃ TÍNH", "⚙️ CẤU HÌNH TỈ TRỌNG VẬT LIỆU"])

# ------------------------------------------
# TAB 1: BẢNG TÍNH TRỌNG LƯỢNG
# ------------------------------------------
with tab_TinhToan:
    with st.container(border=True):
        st.subheader("1. Thông tin Sản phẩm & Vật liệu")
        c1, c2, c3 = st.columns([1.5, 1.5, 2])
        khach_hang = c1.text_input("Tên Khách hàng:")
        ten_sp = c2.text_input("Tên Sản phẩm:")
        
        # Tạo danh sách thả xuống kết hợp tên và tỉ trọng để dễ nhìn
        danh_sach_nhua = []
        dict_ti_trong = {}
        for _, row in df_plastics.iterrows():
            ten = row["Tên nhựa"]
            ti_trong = row["Tỉ trọng (g/cm3)"]
            label = f"{ten} (Tỉ trọng: {ti_trong})"
            danh_sach_nhua.append(label)
            dict_ti_trong[label] = ti_trong
            
        chon_nhua = c3.selectbox("Chọn Nguyên Vật Liệu:", danh_sach_nhua)
        ti_trong_hien_tai = dict_ti_trong.get(chon_nhua, 1.0)
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("2. Khai báo kích thước từng phần")
    st.info("💡 Hướng dẫn: Cuộn xuống cuối bảng và ấn biểu tượng '+' để thêm nhiều khối hình học. Hệ thống sẽ tự động tính Thể tích và Trọng lượng.")
    
    edited_weight_df = st.data_editor(
        st.session_state.weight_items,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Tên/Khu vực bộ phận": st.column_config.TextColumn("Tên/Khu vực bộ phận (VD: Mặt đáy, Gân tăng cứng...)"),
            "Dài (mm)": st.column_config.NumberColumn("Dài (mm)", min_value=0.0, format="%.2f"),
            "Rộng (mm)": st.column_config.NumberColumn("Rộng (mm)", min_value=0.0, format="%.2f"),
            "Dày (mm)": st.column_config.NumberColumn("Dày (mm)", min_value=0.0, format="%.2f"),
            "Thể tích (cm3)": st.column_config.NumberColumn("Thể tích (cm3) - Tự tính", disabled=True),
            "Trọng lượng (gram)": st.column_config.NumberColumn("Trọng lượng (gram) - Tự tính", disabled=True)
        },
        key="weight_editor"
    )

    tong_trong_luong = 0
    if not edited_weight_df.empty:
        # Ép kiểu dữ liệu về số
        edited_weight_df["Dài (mm)"] = pd.to_numeric(edited_weight_df["Dài (mm)"], errors="coerce").fillna(0)
        edited_weight_df["Rộng (mm)"] = pd.to_numeric(edited_weight_df["Rộng (mm)"], errors="coerce").fillna(0)
        edited_weight_df["Dày (mm)"] = pd.to_numeric(edited_weight_df["Dày (mm)"], errors="coerce").fillna(0)
        
        # Tính Thể tích (cm3) = (Dài * Rộng * Dày) / 1000
        edited_weight_df["Thể tích (cm3)"] = (edited_weight_df["Dài (mm)"] * edited_weight_df["Rộng (mm)"] * edited_weight_df["Dày (mm)"]) / 1000
        
        # Tính Trọng lượng (gram) = Thể tích (cm3) * Tỉ trọng
        edited_weight_df["Trọng lượng (gram)"] = edited_weight_df["Thể tích (cm3)"] * ti_trong_hien_tai
        
        tong_trong_luong = edited_weight_df["Trọng lượng (gram)"].sum()
        
        # Lưu ngược lại vào session để giao diện cập nhật ngay lập tức (Xóa chữ None)
        st.session_state.weight_items = edited_weight_df.copy()

    st.markdown("---")
    c_kq1, c_kq2 = st.columns([2, 1])
    
    with c_kq1:
        st.markdown("### KẾT QUẢ TÍNH TOÁN TỔNG")
        st.write(f"- Vật liệu áp dụng: **{chon_nhua}**")
        st.write(f"- Tỉ trọng: **{ti_trong_hien_tai} g/cm3**")
        st.markdown(f"<h2 style='color: #E63946;'>Tổng Trọng Lượng: {tong_trong_luong:,.2f} gram</h2>", unsafe_allow_html=True)
        if tong_trong_luong > 0:
            kg = tong_trong_luong / 1000
            st.markdown(f"<h4 style='color: #2A9D8F;'>(Tương đương: {kg:,.3f} kg)</h4>", unsafe_allow_html=True)

    with c_kq2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("💾 Lưu Lịch Sử Tính Toán Này", use_container_width=True):
            if not ten_sp or not khach_hang:
                st.error("⚠️ Vui lòng nhập Tên khách hàng và Tên sản phẩm!")
            elif tong_trong_luong == 0:
                st.error("⚠️ Bảng kích thước đang trống hoặc bằng 0!")
            else:
                with st.spinner("Đang lưu trữ dữ liệu..."):
                    chi_tiet_json = edited_weight_df.to_json(orient='records')
                    new_record = {
                        "Ngày": datetime.today().strftime('%d/%m/%Y'),
                        "Khách hàng": khach_hang,
                        "Tên sản phẩm": ten_sp,
                        "Loại nhựa": chon_nhua.split(" (")[0], 
                        "Tỉ trọng áp dụng": ti_trong_hien_tai,
                        "Tổng trọng lượng (gram)": tong_trong_luong,
                        "Chi tiết khối": chi_tiet_json 
                    }
                    append_data(new_record, "wanchi_weights", df_Weights)
                
                # Làm sạch bảng sau khi lưu
                st.session_state.weight_items = pd.DataFrame(columns=[
                    "Tên/Khu vực bộ phận", "Dài (mm)", "Rộng (mm)", "Dày (mm)", "Thể tích (cm3)", "Trọng lượng (gram)"
                ])
                st.success("✅ Đã lưu kết quả thành công! (Xem bên Tab Lịch Sử)")
                st.rerun()
                
        if st.button("✨ Xóa Trắng Bảng Để Tính Lại", use_container_width=True):
            st.session_state.weight_items = pd.DataFrame(columns=[
                "Tên/Khu vực bộ phận", "Dài (mm)", "Rộng (mm)", "Dày (mm)", "Thể tích (cm3)", "Trọng lượng (gram)"
            ])
            st.rerun()

# ------------------------------------------
# TAB 2: LỊCH SỬ ĐÃ TÍNH TOÁN
# ------------------------------------------
with tab_LichSu:
    st.subheader("Danh Sách Sản Phẩm Đã Tính Trọng Lượng")
    
    edited_LichSu = st.data_editor(
        df_Weights,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Chi tiết khối": None, 
            "Tỉ trọng áp dụng": st.column_config.NumberColumn(format="%.2f"),
            "Tổng trọng lượng (gram)": st.column_config.NumberColumn(format="%.2f")
        },
        key="edit_weights_history"
    )

    if st.button("💾 Cập nhật dữ liệu Bảng Lịch Sử"):
        with st.spinner("Đang cập nhật..."):
            save_data(edited_LichSu, "wanchi_weights")
        st.success("✅ Đã cập nhật thành công!")
        st.rerun()

    st.markdown("---")
    st.subheader("🔍 Xem Lại Kích Thước Chi Tiết Khối")
    
    list_sp = df_Weights["Tên sản phẩm"].dropna().unique().tolist() if not df_Weights.empty else []
    chon_sp = st.selectbox("Chọn Sản phẩm để xem lại các kích thước cấu thành:", ["(Vui lòng chọn)"] + list_sp)
    
    if chon_sp != "(Vui lòng chọn)":
        row_info = df_Weights[df_Weights["Tên sản phẩm"] == chon_sp].iloc[0]
        st.markdown(f"**Khách hàng:** {row_info.get('Khách hàng', '')} | **Vật liệu:** {row_info.get('Loại nhựa', '')} | **Tổng:** {float(row_info['Tổng trọng lượng (gram)']):,.2f} gram")
        
        try:
            df_chitiet = pd.read_json(row_info["Chi tiết khối"])
            st.dataframe(df_chitiet, use_container_width=True)
        except Exception as e:
            st.error("Lỗi khi đọc dữ liệu chi tiết của sản phẩm này.")

# ------------------------------------------
# TAB 3: QUẢN LÝ / CẬP NHẬT TỈ TRỌNG NHỰA
# ------------------------------------------
with tab_CauHinh:
    st.header("⚙️ Cấu Hình Tỉ Trọng Nguyên Vật Liệu")
    st.markdown("Vì mỗi nhà cung cấp hoặc mỗi loại nhựa pha (nhựa tái sinh, thêm bột thủy tinh...) sẽ có tỉ trọng khác nhau. Tại đây bạn có thể chủ động **Thêm, Sửa, Xóa** danh sách nhựa của xưởng.")
    
    c_edit_nhua, c_add_nhua = st.columns([2, 1])
    
    with c_edit_nhua.container(border=True):
        st.subheader("Danh Sách Tỉ Trọng Hiện Có")
        st.info("💡 Bạn có thể sửa tên, xóa dòng hoặc thêm dòng mới bằng nút '+' ở cuối bảng.")
        
        edited_plastics = st.data_editor(
            df_plastics, 
            num_rows="dynamic", 
            use_container_width=True, 
            key="edit_plastics",
            column_config={
                "Tên nhựa": st.column_config.TextColumn("Tên nhựa (VD: Nhựa PET, Nhựa PA)"),
                "Tỉ trọng (g/cm3)": st.column_config.NumberColumn("Tỉ trọng (g/cm3)", min_value=0.0, format="%.3f")
            }
        )
        
        if st.button("💾 Cập nhật & Lưu Danh Sách Nhựa"):
            with st.spinner("Đang cập nhật lên máy chủ..."):
                save_data(edited_plastics, "wanchi_plastics")
            st.success("✅ Cập nhật thành công! Danh sách xổ xuống ở Tab 1 đã được đồng bộ.")
            st.rerun()

    with c_add_nhua.container(border=True):
        st.subheader("Bảng Tham Khảo Nhanh")
        st.markdown("""
        * **ABS:** ~ 1.04 g/cm3
        * **PP:** ~ 0.90 - 0.92 g/cm3
        * **PC:** ~ 1.20 g/cm3
        * **POM:** ~ 1.41 - 1.42 g/cm3
        * **PA6:** ~ 1.14 g/cm3
        * **PVC:** ~ 1.38 g/cm3
        * **PE:** ~ 0.95 g/cm3
        * **Acrylic:** ~ 1.18 g/cm3
        """)
