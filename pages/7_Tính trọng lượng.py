import streamlit as st
import pandas as pd
import time
import io
from datetime import datetime
from sqlalchemy import text

st.set_page_config(page_title="WANCHI - Tính Trọng Lượng Sản Phẩm", layout="wide")

# --- KHÓA BẢO MẬT TỪ TRANG CHỦ ---
if not st.session_state.get("logged_in", False):
    st.warning("🔒 Bạn chưa đăng nhập! Vui lòng quay lại Trang Chủ (Home) để gõ mật khẩu.")
    st.stop()

# ==========================================
# CSS TỐI ƯU GIAO DIỆN HIỆN ĐẠI, GỌN ĐẸP
# ==========================================
st.markdown("""
<style>
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
        padding-left: 1.5rem;
        padding-right: 1.5rem;
        max-width: 98%;
    }
    div[data-testid="stMetric"] {
        background-color: rgba(128, 128, 128, 0.08);
        border: 1px solid rgba(128, 128, 128, 0.2);
        padding: 12px 16px;
        border-radius: 10px;
    }
    div[data-testid="stMetricLabel"] p {
        font-size: 0.9rem !important;
        white-space: normal !important;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.4rem !important;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# CẤU HÌNH & KẾT NỐI DB + LÍNH GÁC
# ==========================================
try:
    conn = st.connection("postgresql", type="sql")
except Exception:
    st.error("Chưa thể kết nối đến cơ sở dữ liệu.")
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
    st.warning("👉 Vui lòng ấn F5 (Tải lại trang) cho đến khi thông báo này biến mất.")
    st.stop()

# ==========================================
# QUẢN LÝ DỮ LIỆU ĐÁM MÂY (NEON)
# ==========================================
@st.cache_data(show_spinner=False, ttl=86400)
def fetch_data_from_db(table_name):
    try:
        return conn.query(f'SELECT * FROM "{table_name}"', ttl=0)
    except Exception:
        return None

def force_reload_cache():
    fetch_data_from_db.clear()

def load_data(table_name, columns):
    df = fetch_data_from_db(table_name)
    if df is None:
        st.session_state["db_load_success"] = False
        st.error(f"⏳ Máy chủ Neon chưa sẵn sàng. Mất kết nối khi tải bảng '{table_name}'.")
        return pd.DataFrame(columns=columns)
    if df.empty:
        return pd.DataFrame(columns=columns)
    for col in columns:
        if col not in df.columns:
            df[col] = None
    return df

def append_data(new_row_dict, table_name, df_current):
    if not st.session_state.get("db_load_success", False):
        st.error("🚨 LỆNH BỊ CHẶN: Database đang mất kết nối. Vui lòng ấn F5.")
        st.stop()
    try:
        pd.DataFrame([new_row_dict]).to_sql(table_name, con=conn.engine, if_exists='append', index=False)
        force_reload_cache()
    except Exception:
        try:
            df_combined = pd.concat([df_current, pd.DataFrame([new_row_dict])], ignore_index=True)
            df_combined.to_sql(table_name, con=conn.engine, if_exists='replace', index=False)
            force_reload_cache()
        except Exception as e2:
            st.error(f"⚠️ Lỗi cấu trúc: {str(e2)}")

def save_data(df, table_name):
    if not st.session_state.get("db_load_success", False):
        st.error("🚨 LỆNH BỊ CHẶN: Dữ liệu gốc chưa tải xong. Vui lòng ấn F5.")
        st.stop()
    try:
        df.to_sql(table_name, con=conn.engine, if_exists='replace', index=False)
        force_reload_cache()
    except Exception as e:
        st.error(f"⚠️ Lỗi khi lưu dữ liệu ({table_name}): {str(e)}")

def recalc_items_df(df_in, ti_trong):
    """Tính lại thể tích & trọng lượng cho bảng chi tiết dựa trên tỉ trọng hiện tại"""
    expected_cols = [
        "Khu vực / Tên chi tiết", "Dài (mm)", "Rộng (mm)", "Dày (mm)",
        "Số lượng", "Thể tích (cm3)", "Trọng lượng (gram)"
    ]
    if df_in.empty:
        return pd.DataFrame(columns=expected_cols)
    df_out = df_in.copy()
    for c in expected_cols:
        if c not in df_out.columns:
            df_out[c] = "" if c == "Khu vực / Tên chi tiết" else 0.0
    df_out["Dài (mm)"] = pd.to_numeric(df_out["Dài (mm)"], errors="coerce").fillna(0.0)
    df_out["Rộng (mm)"] = pd.to_numeric(df_out["Rộng (mm)"], errors="coerce").fillna(0.0)
    df_out["Dày (mm)"] = pd.to_numeric(df_out["Dày (mm)"], errors="coerce").fillna(0.0)
    df_out["Số lượng"] = pd.to_numeric(df_out["Số lượng"], errors="coerce").fillna(1).astype(int)
    df_out["Thể tích (cm3)"] = (df_out["Dài (mm)"] * df_out["Rộng (mm)"] * df_out["Dày (mm)"]) / 1000.0
    df_out["Trọng lượng (gram)"] = df_out["Thể tích (cm3)"] * float(ti_trong) * df_out["Số lượng"]
    return df_out[expected_cols]

# ==========================================
# KHỞI TẠO DỮ LIỆU TỪ DATABASE
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
if df_plastics.empty and st.session_state.get("db_load_success", False):
    df_plastics = pd.DataFrame(DEFAULT_PLASTICS)
    save_data(df_plastics, "wanchi_plastics")
df_plastics = df_plastics.loc[:, ~df_plastics.columns.duplicated()]

cols_Weights = ["Ngày", "Khách hàng", "Tên sản phẩm", "Loại nhựa", "Tỉ trọng", "Tổng trọng lượng (gram)", "Chi tiết khối"]
df_Weights = load_data("wanchi_weights", cols_Weights)
df_Weights = df_Weights.loc[:, ~df_Weights.columns.duplicated()]

expected_cols = [
    "Khu vực / Tên chi tiết", "Dài (mm)", "Rộng (mm)", "Dày (mm)",
    "Số lượng", "Thể tích (cm3)", "Trọng lượng (gram)"
]
if "weight_items" not in st.session_state or list(st.session_state.weight_items.columns) != expected_cols:
    st.session_state.weight_items = pd.DataFrame(columns=expected_cols)

if "calc_kh" not in st.session_state:
    st.session_state.calc_kh = ""
if "calc_sp" not in st.session_state:
    st.session_state.calc_sp = ""

# ==========================================
# GIAO DIỆN CHÍNH & ĐIỀU HƯỚNG
# ==========================================
st.title("⚖️ Tính Trọng Lượng Sản Phẩm Nhựa")
st.caption("Công thức chuẩn: Thể tích (cm³) = (Dài × Rộng × Dày) / 1000  |  Trọng lượng (g) = Thể tích × Tỉ trọng × Số lượng")

nav_tabs = ["🧮 Tính Trọng Lượng", "🗂️ Lịch Sử Đã Tính", "⚙️ Tỉ Trọng Nhựa"]
if "weight_nav" not in st.session_state or st.session_state.weight_nav not in nav_tabs:
    st.session_state.weight_nav = nav_tabs[0]

nc = st.columns(3)
for idx, label in enumerate(nav_tabs):
    b_type = "primary" if st.session_state.weight_nav == label else "secondary"
    if nc[idx].button(label, use_container_width=True, type=b_type):
        st.session_state.weight_nav = label
        st.rerun()

st.markdown("---")

# ==============================================================================
# TRANG 1: TÍNH TRỌNG LƯỢNG
# ==============================================================================
if st.session_state.weight_nav == nav_tabs[0]:
    # --- Khối 1: Thông tin sản phẩm & loại nhựa ---
    with st.container(border=True):
        st.subheader("1. Thông Tin Sản Phẩm & Vật Liệu")
        c1, c2, c3 = st.columns([1.4, 1.4, 1.6])
        ten_sp = c1.text_input("Tên sản phẩm (*)", key="calc_sp", placeholder="VD: Nắp hộp nhựa 500ml")
        khach_hang = c2.text_input("Khách hàng", key="calc_kh", placeholder="VD: Công ty ABC")

        danh_sach_nhua = []
        dict_ti_trong = {}
        for _, row in df_plastics.iterrows():
            ten = str(row["Tên nhựa"])
            try:
                tt = float(row["Tỉ trọng (g/cm3)"])
            except Exception:
                tt = 1.0
            label = f"{ten} ({tt:.2f} g/cm³)"
            danh_sach_nhua.append(label)
            dict_ti_trong[label] = tt

        chon_nhua = c3.selectbox("Loại nhựa áp dụng:", danh_sach_nhua, key="calc_plastic")
        ti_trong_hien_tai = dict_ti_trong.get(chon_nhua, 1.0)

    # --- Khối 2: Nhập nhanh kích thước (không cần gõ ô tên trước) ---
    with st.container(border=True):
        st.subheader("2. Nhập Nhanh Kích Thước Chi Tiết")
        with st.form("form_add_part", clear_on_submit=True):
            r1c1, r1c2, r1c3, r1c4 = st.columns(4)
            in_dai = r1c1.number_input("Dài (mm) *", min_value=0.0, step=1.0, format="%.2f")
            in_rong = r1c2.number_input("Rộng (mm) *", min_value=0.0, step=1.0, format="%.2f")
            in_day = r1c3.number_input("Dày (mm) *", min_value=0.0, step=0.1, format="%.2f")
            in_sl = r1c4.number_input("Số lượng", min_value=1, step=1, value=1)

            r2c1, r2c2 = st.columns([2.5, 1.5])
            in_ten = r2c1.text_input(
                "Tên chi tiết / Khu vực (Tùy chọn - bỏ trống sẽ tự đánh số)",
                placeholder="VD: Mặt trên, Thành bên, Gân tăng cứng..."
            )
            r2c2.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            submitted_part = r2c2.form_submit_button("➕ Thêm vào bảng tính", type="primary", use_container_width=True)

            if submitted_part:
                if in_dai <= 0 or in_rong <= 0 or in_day <= 0:
                    st.error("⚠️ Vui lòng nhập Dài, Rộng, Dày lớn hơn 0.")
                else:
                    next_idx = len(st.session_state.weight_items) + 1
                    ten_final = in_ten.strip() if in_ten.strip() else f"Chi tiết {next_idx}"
                    the_tich = (in_dai * in_rong * in_day) / 1000.0
                    trong_luong = the_tich * ti_trong_hien_tai * in_sl

                    new_part = {
                        "Khu vực / Tên chi tiết": ten_final,
                        "Dài (mm)": in_dai,
                        "Rộng (mm)": in_rong,
                        "Dày (mm)": in_day,
                        "Số lượng": int(in_sl),
                        "Thể tích (cm3)": the_tich,
                        "Trọng lượng (gram)": trong_luong
                    }
                    st.session_state.weight_items = pd.concat(
                        [st.session_state.weight_items, pd.DataFrame([new_part])],
                        ignore_index=True
                    )
                    st.rerun()

    # --- Khối 3: Bảng chi tiết đã nhập (tự quy đổi lại nếu đổi loại nhựa) ---
    df_current_calc = recalc_items_df(st.session_state.weight_items, ti_trong_hien_tai)

    st.subheader("3. Danh Sách Chi Tiết & Kết Quả Tổng")

    if df_current_calc.empty:
        st.info("Chưa có chi tiết nào. Hãy nhập Dài, Rộng, Dày ở khung phía trên rồi bấm **➕ Thêm vào bảng tính**.")
    else:
        df_disp = df_current_calc.copy()
        df_disp.insert(0, "Chọn", False)

        edited_parts = st.data_editor(
            df_disp,
            use_container_width=True,
            hide_index=True,
            column_order=[
                "Chọn", "Khu vực / Tên chi tiết", "Trọng lượng (gram)",
                "Dài (mm)", "Rộng (mm)", "Dày (mm)", "Số lượng", "Thể tích (cm3)"
            ],
            column_config={
                "Chọn": st.column_config.CheckboxColumn("Chọn", help="Tick để xóa dòng", width="small"),
                "Khu vực / Tên chi tiết": st.column_config.TextColumn("Tên chi tiết", width="medium"),
                "Trọng lượng (gram)": st.column_config.NumberColumn("⚖️ Trọng lượng (g)", disabled=True, format="%.2f", width="small"),
                "Dài (mm)": st.column_config.NumberColumn("Dài (mm)", min_value=0.0, format="%.2f", width="small"),
                "Rộng (mm)": st.column_config.NumberColumn("Rộng (mm)", min_value=0.0, format="%.2f", width="small"),
                "Dày (mm)": st.column_config.NumberColumn("Dày (mm)", min_value=0.0, format="%.2f", width="small"),
                "Số lượng": st.column_config.NumberColumn("SL", min_value=1, format="%d", width="small"),
                "Thể tích (cm3)": st.column_config.NumberColumn("Thể tích (cm³)", disabled=True, format="%.3f", width="small"),
            },
            key="parts_editor"
        )
        edited_parts["Chọn"] = edited_parts["Chọn"].fillna(False).astype(bool)

        # Tính tổng tức thì dựa trên giá trị mới nhất trong bảng
        df_live = recalc_items_df(edited_parts.drop(columns=["Chọn"]), ti_trong_hien_tai)
        tong_gram = float(df_live["Trọng lượng (gram)"].sum())
        tong_kg = tong_gram / 1000.0
        tong_cm3 = float(df_live["Thể tích (cm3)"].sum())
        tong_so_ct = int(df_live["Số lượng"].sum())

        # Thanh nút thao tác bảng
        ac1, ac2, ac3 = st.columns(3)
        with ac1:
            if st.button("🔄 Cập nhật số liệu vừa sửa trong bảng", use_container_width=True):
                st.session_state.weight_items = df_live.copy()
                st.rerun()
        with ac2:
            if st.button("🗑️ Xóa dòng đã chọn", use_container_width=True):
                if not edited_parts["Chọn"].any():
                    st.warning("⚠️ Vui lòng tick vào cột 'Chọn' ở dòng cần xóa.")
                else:
                    keep_df = edited_parts[edited_parts["Chọn"] == False].drop(columns=["Chọn"])
                    st.session_state.weight_items = recalc_items_df(keep_df, ti_trong_hien_tai)
                    st.rerun()
        with ac3:
            if st.button("🧹 Xóa trắng bảng", use_container_width=True):
                st.session_state.weight_items = pd.DataFrame(columns=expected_cols)
                st.rerun()

        st.markdown("---")

        # Thẻ KPI kết quả nổi bật
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("⚖️ Tổng Trọng Lượng (gram)", f"{tong_gram:,.2f} g")
        m2.metric("📦 Quy Đổi (kg)", f"{tong_kg:,.3f} kg")
        m3.metric("🧊 Tổng Thể Tích", f"{tong_cm3:,.2f} cm³")
        m4.metric("🔢 Tổng Số Chi Tiết", f"{tong_so_ct} chi tiết")

        st.write("")
        if st.button("💾 LƯU KẾT QUẢ VÀO LỊCH SỬ", type="primary", use_container_width=True):
            if not ten_sp.strip():
                st.error("⚠️ Vui lòng nhập Tên sản phẩm ở mục 1 trước khi lưu!")
            elif tong_gram <= 0:
                st.error("⚠️ Tổng trọng lượng đang bằng 0, chưa thể lưu!")
            else:
                with st.spinner("Đang lưu lên cơ sở dữ liệu..."):
                    new_record = {
                        "Ngày": datetime.today().strftime('%d/%m/%Y'),
                        "Khách hàng": khach_hang.strip(),
                        "Tên sản phẩm": ten_sp.strip(),
                        "Loại nhựa": chon_nhua.split(" (")[0],
                        "Tỉ trọng": ti_trong_hien_tai,
                        "Tổng trọng lượng (gram)": round(tong_gram, 2),
                        "Chi tiết khối": df_live.to_json(orient='records', force_ascii=False)
                    }
                    append_data(new_record, "wanchi_weights", df_Weights)
                st.session_state.weight_items = pd.DataFrame(columns=expected_cols)
                st.success("✅ Đã lưu thành công vào Lịch Sử!")
                time.sleep(1)
                st.rerun()

# ==============================================================================
# TRANG 2: LỊCH SỬ ĐÃ TÍNH
# ==============================================================================
elif st.session_state.weight_nav == nav_tabs[1]:
    st.subheader("🗂️ Danh Sách Sản Phẩm Đã Tính Trọng Lượng")

    search_txt = st.text_input("🔍 Tìm kiếm nhanh theo Tên sản phẩm hoặc Khách hàng:", placeholder="Gõ từ khóa để lọc...")

    df_w_view = df_Weights.copy()
    if search_txt.strip() and not df_w_view.empty:
        q = search_txt.strip().lower()
        mask = (
            df_w_view["Tên sản phẩm"].astype(str).str.lower().str.contains(q, na=False) |
            df_w_view["Khách hàng"].astype(str).str.lower().str.contains(q, na=False)
        )
        df_w_view = df_w_view[mask].copy()

    if not df_w_view.empty:
        df_w_view["Tỉ trọng"] = pd.to_numeric(df_w_view["Tỉ trọng"], errors="coerce").fillna(0.0)
        df_w_view["Tổng trọng lượng (gram)"] = pd.to_numeric(df_w_view["Tổng trọng lượng (gram)"], errors="coerce").fillna(0.0)

    df_w_view.insert(0, "Chọn", False)

    edited_hist = st.data_editor(
        df_w_view,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        column_order=[
            "Chọn", "Tên sản phẩm", "Tổng trọng lượng (gram)",
            "Loại nhựa", "Tỉ trọng", "Khách hàng", "Ngày"
        ],
        column_config={
            "Chọn": st.column_config.CheckboxColumn("Chọn", help="Tick để xóa", width="small"),
            "Chi tiết khối": None,
            "Tên sản phẩm": st.column_config.TextColumn("Tên sản phẩm", width="large"),
            "Tổng trọng lượng (gram)": st.column_config.NumberColumn("⚖️ Tổng (gram)", format="%.2f", width="small"),
            "Loại nhựa": st.column_config.TextColumn("Loại nhựa", width="medium"),
            "Tỉ trọng": st.column_config.NumberColumn("Tỉ trọng", format="%.2f", width="small"),
            "Khách hàng": st.column_config.TextColumn("Khách hàng", width="medium"),
            "Ngày": st.column_config.TextColumn("Ngày", width="small"),
        },
        key="edit_weights_history"
    )
    edited_hist["Chọn"] = edited_hist["Chọn"].fillna(False).astype(bool)

    is_searching = bool(search_txt.strip())
    if is_searching:
        st.caption("💡 Đang bật tìm kiếm: xóa ô tìm kiếm để lưu chỉnh sửa trực tiếp (nút Xóa vẫn dùng được bình thường).")

    bh1, bh2 = st.columns(2)
    with bh1:
        if st.button("💾 Lưu Thay Đổi Lịch Sử", type="primary", use_container_width=True, disabled=is_searching):
            with st.spinner("Đang cập nhật..."):
                save_data(edited_hist.drop(columns=["Chọn"]), "wanchi_weights")
            st.success("✅ Đã lưu thay đổi lịch sử!")
            time.sleep(1)
            st.rerun()
    with bh2:
        if st.button("🗑️ Xóa Dòng Đã Chọn", use_container_width=True, key="del_hist"):
            if not edited_hist["Chọn"].any():
                st.warning("⚠️ Vui lòng tick vào cột 'Chọn' ở dòng cần xóa.")
            else:
                with st.spinner("Đang xóa..."):
                    if not is_searching:
                        df_rem = edited_hist[edited_hist["Chọn"] == False].drop(columns=["Chọn"])
                    else:
                        idx_drop = [i for i in edited_hist[edited_hist["Chọn"] == True].index if i in df_Weights.index]
                        df_rem = df_Weights.drop(index=idx_drop)
                    save_data(df_rem, "wanchi_weights")
                st.success("✅ Đã xóa các dòng đã chọn!")
                time.sleep(1)
                st.rerun()

    st.markdown("---")
    st.subheader("🔍 Bóc Tách Chi Tiết Kích Thước Đã Lưu")

    if not df_Weights.empty:
        options_map = {}
        for idx, r in df_Weights.iterrows():
            sp_name = str(r.get("Tên sản phẩm", ""))
            kh_name = str(r.get("Khách hàng", ""))
            ngay_luu = str(r.get("Ngày", ""))
            gram_val = pd.to_numeric(r.get("Tổng trọng lượng (gram)", 0), errors="coerce")
            label = f"{sp_name} — {kh_name} ({ngay_luu} | {gram_val:,.2f} g)"
            options_map[label] = idx

        chon_label = st.selectbox("Chọn bản ghi cần xem chi tiết:", ["-- Chọn sản phẩm --"] + list(options_map.keys()))
        if chon_label != "-- Chọn sản phẩm --":
            row_info = df_Weights.loc[options_map[chon_label]]
            k1, k2, k3 = st.columns(3)
            k1.metric("Khách hàng", str(row_info.get("Khách hàng") or "—"))
            k2.metric("Vật liệu", f"{row_info.get('Loại nhựa', '')} ({row_info.get('Tỉ trọng', '')})")
            k3.metric("Tổng khối lượng", f"{float(row_info['Tổng trọng lượng (gram)']):,.2f} g")

            try:
                raw_json = str(row_info["Chi tiết khối"])
                df_ct = pd.read_json(io.StringIO(raw_json))
                st.dataframe(
                    df_ct,
                    use_container_width=True,
                    hide_index=True,
                    column_order=[
                        c for c in [
                            "Khu vực / Tên chi tiết", "Trọng lượng (gram)",
                            "Dài (mm)", "Rộng (mm)", "Dày (mm)", "Số lượng", "Thể tích (cm3)"
                        ] if c in df_ct.columns
                    ]
                )
                if st.button("📋 Nạp lại bộ kích thước này vào Máy Tính để chỉnh sửa", use_container_width=True):
                    st.session_state.weight_items = recalc_items_df(df_ct, float(row_info.get("Tỉ trọng", 1.0)))
                    st.session_state.calc_sp = str(row_info.get("Tên sản phẩm", ""))
                    st.session_state.calc_kh = str(row_info.get("Khách hàng", ""))
                    st.session_state.weight_nav = nav_tabs[0]
                    st.rerun()
            except Exception:
                st.error("Không thể đọc dữ liệu chi tiết của sản phẩm này.")
    else:
        st.info("Chưa có lịch sử tính toán nào.")

# ==============================================================================
# TRANG 3: CẤU HÌNH TỈ TRỌNG NHỰA
# ==============================================================================
elif st.session_state.weight_nav == nav_tabs[2]:
    col_left, col_right = st.columns([1.8, 1])

    with col_left:
        with st.container(border=True):
            st.subheader("➕ Thêm Loại Nhựa Mới")
            with st.form("form_add_plastic", clear_on_submit=True):
                p1, p2 = st.columns([2, 1])
                ten_nhua_moi = p1.text_input("Tên nhựa (*)", placeholder="VD: Nhựa PET, Nhựa HDPE...")
                ti_trong_moi = p2.number_input("Tỉ trọng (g/cm³)", min_value=0.01, step=0.01, value=1.00, format="%.3f")
                if st.form_submit_button("➕ Thêm vào danh sách", type="primary", use_container_width=True):
                    if not ten_nhua_moi.strip():
                        st.warning("⚠️ Vui lòng nhập Tên nhựa.")
                    else:
                        with st.spinner("Đang lưu..."):
                            append_data(
                                {"Tên nhựa": ten_nhua_moi.strip(), "Tỉ trọng (g/cm3)": ti_trong_moi},
                                "wanchi_plastics",
                                df_plastics
                            )
                        st.success("✅ Đã thêm loại nhựa mới!")
                        time.sleep(1)
                        st.rerun()

        st.subheader("📋 Danh Sách Tỉ Trọng Tại Xưởng")
        df_p_view = df_plastics.copy()
        df_p_view["Tỉ trọng (g/cm3)"] = pd.to_numeric(df_p_view["Tỉ trọng (g/cm3)"], errors="coerce").fillna(1.0)
        df_p_view.insert(0, "Chọn", False)

        edited_plastics = st.data_editor(
            df_p_view,
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            column_config={
                "Chọn": st.column_config.CheckboxColumn("Chọn", help="Tick để xóa", width="small"),
                "Tên nhựa": st.column_config.TextColumn("Tên nhựa", width="large"),
                "Tỉ trọng (g/cm3)": st.column_config.NumberColumn("Tỉ trọng (g/cm³)", min_value=0.0, format="%.3f", width="medium"),
            },
            key="edit_plastics"
        )
        edited_plastics["Chọn"] = edited_plastics["Chọn"].fillna(False).astype(bool)

        bp1, bp2 = st.columns(2)
        with bp1:
            if st.button("💾 Lưu Danh Sách Nhựa", type="primary", use_container_width=True):
                with st.spinner("Đang cập nhật..."):
                    df_p_save = edited_plastics.drop(columns=["Chọn"]).dropna(subset=["Tên nhựa"])
                    save_data(df_p_save, "wanchi_plastics")
                st.success("✅ Đã cập nhật danh sách nhựa!")
                time.sleep(1)
                st.rerun()
        with bp2:
            if st.button("🗑️ Xóa Dòng Đã Chọn", use_container_width=True, key="del_plastics"):
                if not edited_plastics["Chọn"].any():
                    st.warning("⚠️ Vui lòng tick vào cột 'Chọn' ở loại nhựa cần xóa.")
                else:
                    with st.spinner("Đang xóa..."):
                        df_p_rem = edited_plastics[edited_plastics["Chọn"] == False].drop(columns=["Chọn"]).dropna(subset=["Tên nhựa"])
                        save_data(df_p_rem, "wanchi_plastics")
                    st.success("✅ Đã xóa các loại nhựa đã chọn!")
                    time.sleep(1)
                    st.rerun()

    with col_right:
        with st.container(border=True):
            st.subheader("📘 Bảng Tham Khảo Tỉ Trọng")
            ref_df = pd.DataFrame([
                {"Loại nhựa": "ABS", "Tỉ trọng (g/cm³)": "1.04"},
                {"Loại nhựa": "PP", "Tỉ trọng (g/cm³)": "0.90 - 0.92"},
                {"Loại nhựa": "PC", "Tỉ trọng (g/cm³)": "1.20"},
                {"Loại nhựa": "POM", "Tỉ trọng (g/cm³)": "1.41 - 1.42"},
                {"Loại nhựa": "PA6", "Tỉ trọng (g/cm³)": "1.14"},
                {"Loại nhựa": "PVC", "Tỉ trọng (g/cm³)": "1.38"},
                {"Loại nhựa": "PE", "Tỉ trọng (g/cm³)": "0.95"},
                {"Loại nhựa": "Mica (Acrylic)", "Tỉ trọng (g/cm³)": "1.18"},
                {"Loại nhựa": "Silicon / TPE", "Tỉ trọng (g/cm³)": "~1.15"},
            ])
            st.dataframe(ref_df, use_container_width=True, hide_index=True)
