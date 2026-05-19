import streamlit as st
import pandas as pd
from datetime import datetime
from sqlalchemy import text

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
# QUẢN LÝ DỮ LIỆU ĐÁM MÂY (NEON)
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
    {"Tên nhựa": "Nhựa PVC", "Tỉ trọng (g/cm3)": 1.38},
    {"Tên nhựa": "Nhựa PA6", "Tỉ trọng (g/cm3)": 1.14},
    {"Tên nhựa": "Nhựa Acrylic / Mica", "Tỉ trọng (g/cm3)": 1.18}
]

df_plastics = load_data("wanchi_plastics", ["Tên nhựa", "Tỉ trọng (g/cm3)"])
if df_plastics.empty:
    df_plastics = pd.DataFrame(DEFAULT_PLASTICS)
    save_data(df_plastics, "wanchi_plastics")

df_plastics = df_plastics.loc[:, ~df_plastics.columns.duplicated()]

# ==========================================
# KHỞI TẠO BẢNG LỊCH SỬ TÍNH TRỌNG LƯỢNG
# ==========================================
cols_Weights = ["Ngày", "Khách hàng", "Tên sản phẩm", "Loại nhựa", "Tỉ trọng", "Tổng trọng lượng (gram)", "Chi tiết khối"]
df_Weights = load_data("wanchi_weights", cols_Weights)
df_Weights = df_Weights.loc[:, ~df_Weights.columns.duplicated()]

# ---> CẤU TRÚC CỘT: KHÔNG CÓ CỘT TÊN, CÓ CỘT SỐ LƯỢNG <---
expected_cols = ["Dài (mm)", "Rộng (mm)", "Dày (mm)", "Số lượng", "Thể tích (cm3)", "Trọng lượng (gram)"]
if "weight_items" not in st.session_state or list(st.session_state.weight_items.columns) != expected_cols:
    st.session_state.weight_items = pd.DataFrame(columns=expected_cols)

# ==========================================
# GIAO DIỆN CHÍNH
# ==========================================
st.title("⚖️ Công Cụ Tính Trọng Lượng Nhựa (Công Thức Chuẩn)")
st.markdown("Áp dụng công thức: **Thể tích (cm³)** = (Dài × Rộng × Dày × Số lượng) / 1000. **Trọng lượng (g)** = Thể tích × Tỉ trọng.")
st.markdown("---")

tab_TinhToan, tab_LichSu, tab_CauHinh = st.tabs(["🧩 NHẬP KÍCH THƯỚC & TÍNH TOÁN", "🗂️ LỊCH SỬ ĐÃ TÍNH", "⚙️ CẤU HÌNH TỈ TRỌNG NHỰA"])

# ------------------------------------------
# TAB 1: BẢNG TÍNH TRỌNG LƯỢNG
# ------------------------------------------
with tab_TinhToan:
    with st.container(border=True):
        st.subheader("1. Thông tin Sản phẩm & Tỉ trọng")
        c1, c2, c3 = st.columns([1.5, 1.5, 2])
        khach_hang = c1.text_input("Tên Khách hàng:")
        ten_sp = c2.text_input("Tên Sản phẩm:")
        
        danh_sach_nhua = []
        dict_ti_trong = {}
        for _, row in df_plastics.iterrows():
            ten = row["Tên nhựa"]
            ti_trong = row["Tỉ trọng (g/cm3)"]
            label = f"{ten} (Tỉ trọng: {ti_trong})"
            danh_sach_nhua.append(label)
            dict_ti_trong[label] = float(ti_trong)
            
        chon_nhua = c3.selectbox("Chọn Nguyên Vật Liệu:", danh_sach_nhua)
        ti_trong_hien_tai = dict_ti_trong.get(chon_nhua, 1.0)
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("2. Khai báo Kích thước (Máy tự tính Dấu +)")
    st.info("💡 Hướng dẫn: Gõ Dài, Rộng, Dày và Số lượng rồi bấm Enter. Hệ thống sẽ tự nảy số. Ấn biểu tượng '+' cuối bảng để thêm nhiều khối.")
    
    edited_weight_df = st.data_editor(
        st.session_state.weight_items,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True, # ---> ĐÃ ẨN CỘT SỐ THỨ TỰ BÊN TRÁI <---
        column_config={
            "Dài (mm)": st.column_config.NumberColumn("Dài (mm)", min_value=0.0, format="%.2f"),
            "Rộng (mm)": st.column_config.NumberColumn("Rộng (mm)", min_value=0.0, format="%.2f"),
            "Dày (mm)": st.column_config.NumberColumn("Dày (mm)", min_value=0.0, format="%.2f"),
            "Số lượng": st.column_config.NumberColumn("Số lượng", min_value=1, format="%d"),
            "Thể tích (cm3)": st.column_config.NumberColumn("Thể tích (cm3)", disabled=True, format="%.3f"),
            "Trọng lượng (gram)": st.column_config.NumberColumn("Trọng lượng (gram)", disabled=True, format="%.2f")
        },
        key="weight_editor"
    )

    tong_trong_luong = 0
    if not edited_weight_df.empty:
        # Ép kiểu dữ liệu về dạng số để tính toán
        edited_weight_df["Dài (mm)"] = pd.to_numeric(edited_weight_df["Dài (mm)"], errors="coerce").fillna(0.0)
        edited_weight_df["Rộng (mm)"] = pd.to_numeric(edited_weight_df["Rộng (mm)"], errors="coerce").fillna(0.0)
        edited_weight_df["Dày (mm)"] = pd.to_numeric(edited_weight_df["Dày (mm)"], errors="coerce").fillna(0.0)
        
        # Mặc định Số lượng là 1 nếu bỏ trống
        edited_weight_df["Số lượng"] = pd.to_numeric(edited_weight_df["Số lượng"], errors="coerce").fillna(1)
        edited_weight_df.loc[edited_weight_df["Số lượng"] <= 0, "Số lượng"] = 1
        
        # ÁP DỤNG CÔNG THỨC CHUẨN CÓ SỐ LƯỢNG
        edited_weight_df["Thể tích (cm3)"] = (edited_weight_df["Dài (mm)"] * edited_weight_df["Rộng (mm)"] * edited_weight_df["Dày (mm)"] * edited_weight_df["Số lượng"]) / 1000.0
        edited_weight_df["Trọng lượng (gram)"] = edited_weight_df["Thể tích (cm3)"] * ti_trong_hien_tai
        
        tong_trong_luong = edited_weight_df["Trọng lượng (gram)"].sum()
        
        # LỚP BẢO VỆ CHỐNG LỖI KHI AUTO-RERUN
        input_cols = ["Dài (mm)", "Rộng (mm)", "Dày (mm)", "Số lượng"]
        if all(c in edited_weight_df.columns for c in input_cols) and all(c in st.session_state.weight_items.columns for c in input_cols):
            if not edited_weight_df[input_cols].equals(st.session_state.weight_items[input_cols]):
                st.session_state.weight_items = edited_weight_df.copy()
                st.rerun()

    st.markdown("---")
    c_kq1, c_kq2 = st.columns([2, 1])
    
    with c_kq1:
        st.markdown("### KẾT QUẢ TÍNH TOÁN TỔNG")
        st.write(f"- Vật liệu quy đổi: **{chon_nhua}**")
        st.markdown(f"<h2 style='color: #E63946;'>Tổng Trọng Lượng: {tong_trong_luong:,.2f} gram</h2>", unsafe_allow_html=True)
        if tong_trong_luong > 0:
            kg = tong_trong_luong / 1000
            st.markdown(f"<h4 style='color: #2A9D8F;'>(Tương đương: {kg:,.3f} kg)</h4>", unsafe_allow_html=True)

    with c_kq2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("💾 Lưu Vào Lịch Sử Tính Toán", use_container_width=True):
            if not ten_sp:
                st.error("⚠️ Vui lòng nhập ít nhất Tên sản phẩm!")
            elif tong_trong_luong == 0:
                st.error("⚠️ Bảng kích thước chưa có số liệu!")
            else:
                with st.spinner("Đang cất dữ liệu vào máy chủ..."):
                    chi_tiet_json = edited_weight_df.to_json(orient='records')
                    new_record = {
                        "Ngày": datetime.today().strftime('%d/%m/%Y'),
                        "Khách hàng": khach_hang,
                        "Tên sản phẩm": ten_sp,
                        "Loại nhựa": chon_nhua.split(" (")[0], 
                        "Tỉ trọng": ti_trong_hien_tai,
                        "Tổng trọng lượng (gram)": tong_trong_luong,
                        "Chi tiết khối": chi_tiet_json 
                    }
                    append_data(new_record, "wanchi_weights", df_Weights)
                
                # Làm sạch bảng sau khi lưu
                st.session_state.weight_items = pd.DataFrame(columns=expected_cols)
                st.success("✅ Đã lưu kết quả thành công! (Chuyển sang Tab Lịch Sử để xem)")
                st.rerun()
                
        if st.button("✨ Xóa Trắng Bảng Để Tính Lại", use_container_width=True):
            st.session_state.weight_items = pd.DataFrame(columns=expected_cols)
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
        hide_index=True, # ---> ĐÃ ẨN CỘT SỐ THỨ TỰ BÊN TRÁI <---
        column_config={
            "Chi tiết khối": None, 
            "Tỉ trọng": st.column_config.NumberColumn(format="%.2f"),
            "Tổng trọng lượng (gram)": st.column_config.NumberColumn(format="%.2f")
        },
        key="edit_weights_history"
    )

    if st.button("💾 Cập nhật thay đổi Lịch Sử"):
        with st.spinner("Đang cập nhật..."):
            save_data(edited_LichSu, "wanchi_weights")
        st.success("✅ Đã lưu thay đổi thành công!")
        st.rerun()

    st.markdown("---")
    st.subheader("🔍 Xem Lại Khối Lượng Từng Phần")
    
    list_sp = df_Weights["Tên sản phẩm"].dropna().unique().tolist() if not df_Weights.empty else []
    chon_sp = st.selectbox("Chọn Sản phẩm để bóc tách lại kích thước:", ["(Vui lòng chọn)"] + list_sp)
    
    if chon_sp != "(Vui lòng chọn)":
        row_info = df_Weights[df_Weights["Tên sản phẩm"] == chon_sp].iloc[0]
        st.markdown(f"**Khách hàng:** {row_info.get('Khách hàng', '')} | **Vật liệu:** {row_info.get('Loại nhựa', '')} | **Tổng Khối lượng:** {float(row_info['Tổng trọng lượng (gram)']):,.2f} gram")
        
        try:
            df_chitiet = pd.read_json(row_info["Chi tiết khối"])
            st.dataframe(df_chitiet, use_container_width=True, hide_index=True) # ---> ĐÃ ẨN CỘT SỐ THỨ TỰ BÊN TRÁI <---
        except Exception as e:
            st.error("Lỗi khi đọc dữ liệu chi tiết của sản phẩm này.")

# ------------------------------------------
# TAB 3: QUẢN LÝ / CẬP NHẬT TỈ TRỌNG NHỰA
# ------------------------------------------
with tab_CauHinh:
    st.header("⚙️ Cấu Hình Tỉ Trọng Nguyên Vật Liệu")
    st.markdown("Các loại nhựa khác nhau sẽ có tỉ trọng khác nhau (Nhựa pha, nhựa tái sinh, nhựa zin...). Tại đây bạn có thể chủ động **Thêm, Sửa, Xóa** danh sách nhựa của xưởng.")
    
    c_edit_nhua, c_add_nhua = st.columns([2, 1])
    
    with c_edit_nhua.container(border=True):
        st.subheader("Danh Sách Tỉ Trọng Tại Xưởng")
        st.info("💡 Bạn có thể sửa tên, sửa tỉ trọng, xóa dòng hoặc thêm loại nhựa mới bằng nút '+' ở cuối bảng.")
        
        edited_plastics = st.data_editor(
            df_plastics, 
            num_rows="dynamic", 
            use_container_width=True, 
            hide_index=True, # ---> ĐÃ ẨN CỘT SỐ THỨ TỰ BÊN TRÁI <---
            key="edit_plastics",
            column_config={
                "Tên nhựa": st.column_config.TextColumn("Tên nhựa (VD: Nhựa PET, Nhựa PA)"),
                "Tỉ trọng (g/cm3)": st.column_config.NumberColumn("Tỉ trọng (g/cm3)", min_value=0.0, format="%.3f")
            }
        )
        
        if st.button("💾 Cập nhật & Lưu Danh Sách Nhựa"):
            with st.spinner("Đang cập nhật lên máy chủ..."):
                save_data(edited_plastics, "wanchi_plastics")
            st.success("✅ Cập nhật thành công! Danh sách xổ xuống ở Tab 1 đã tự động nhận dữ liệu mới.")
            st.rerun()

    with c_add_nhua.container(border=True):
        st.subheader("Bảng Tham Khảo Kỹ Thuật")
        st.markdown("""
        * **ABS:** 1.04 g/cm³
        * **PP:** 0.90 - 0.92 g/cm³
        * **PC:** 1.20 g/cm³
        * **POM:** 1.41 - 1.42 g/cm³
        * **PA6:** 1.14 g/cm³
        * **PVC:** 1.38 g/cm³
        * **PE:** 0.95 g/cm³
        * **Mica (Acrylic):** 1.18 g/cm³
        * **Silicon/TPE:** ~1.15 g/cm³
        """)
