import streamlit as st
import pandas as pd
from sqlalchemy import inspect
import io
from fpdf import FPDF

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="Tính Giá Sản Xuất", layout="wide")

# Kiểm tra đăng nhập từ trang Home
if not st.session_state.get("logged_in", False):
    st.warning("🔒 Bạn chưa đăng nhập! Vui lòng quay lại Trang Chủ (Home) để gõ mật khẩu.")
    st.stop()

# ==========================================
# CSS TỐI ƯU GIAO DIỆN GỌN ĐẸP, DỄ NHÌN
# ==========================================
st.markdown("""
<style>
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
        max-width: 1250px;
    }
    div[data-testid="stMetric"] {
        background-color: rgba(128, 128, 128, 0.07);
        border: 1px solid rgba(128, 128, 128, 0.2);
        padding: 12px 16px;
        border-radius: 10px;
    }
    div[data-testid="stMetricLabel"] p {
        font-size: 0.88rem !important;
        white-space: normal !important;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.35rem !important;
        font-weight: 700 !important;
    }
    .sub-pill {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 6px;
        background-color: rgba(128, 128, 128, 0.1);
        font-size: 0.88rem;
        margin-top: 4px;
    }
    .cost-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.91rem;
        margin-top: 6px;
    }
    .cost-table th, .cost-table td {
        padding: 8px 10px;
        border-bottom: 1px solid rgba(128, 128, 128, 0.22);
    }
    .cost-table th {
        background-color: rgba(128, 128, 128, 0.12);
        font-weight: 600;
        font-size: 0.85rem;
    }
    .cost-table tr.total-row td {
        background-color: rgba(128, 128, 128, 0.10);
        font-weight: 700;
        border-top: 2px solid rgba(128, 128, 128, 0.35);
        border-bottom: none;
    }
    .cost-table .num {
        text-align: right;
        white-space: nowrap;
        font-variant-numeric: tabular-nums;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# KẾT NỐI NEON (POSTGRESQL)
# ==========================================
try:
    conn = st.connection("postgresql", type="sql")
except Exception as e:
    st.error("Chưa thể kết nối Database Neon. Vui lòng kiểm tra lại file cấu hình Secrets.")
    st.stop()

def load_data():
    try:
        inspector = inspect(conn.engine)
        if not inspector.has_table("wanchi_sanpham"):
            return []
        df = pd.read_sql("SELECT * FROM wanchi_sanpham", con=conn.engine)
        if not df.empty:
            if "Giá Tiêu Chuẩn" in df.columns:
                df.rename(columns={"Giá Tiêu Chuẩn": "Giá Công ty"}, inplace=True)
            return df.to_dict('records')
        return []
    except Exception as e:
        st.warning("⏳ Máy chủ dữ liệu đang khởi động. Vui lòng đợi 3 giây rồi tải lại.")
        return None

def save_data(data_list):
    try:
        df = pd.DataFrame(data_list)
        if df.empty:
            df = pd.DataFrame(columns=["Mã SP", "Tên Sản Phẩm", "Trọng lượng", "Đơn giá nhựa", "Giá máy", "Chu kỳ", "SP Khuôn", "Bao bì", "Phụ kiện", "Chi phí đóng gói", "Đơn giá phụ gia", "Tỉ lệ phụ gia", "Giá trị khuôn", "SL khuôn", "Hệ số ĐL", "Giá Vốn", "Giá Đại Lý", "Giá Công ty"])
        df.to_sql("wanchi_sanpham", con=conn.engine, if_exists='replace', index=False)
    except Exception as e:
        pass

# ==========================================
# QUẢN LÝ TRẠNG THÁI (SESSION STATE)
# ==========================================
if "danh_sach_sp" not in st.session_state or st.session_state["danh_sach_sp"] is None:
    st.session_state["danh_sach_sp"] = load_data()

if st.session_state["danh_sach_sp"] is None:
    st.session_state["danh_sach_sp"] = []

if "is_editing_sx" not in st.session_state:
    st.session_state["is_editing_sx"] = False
    st.session_state["edit_index_sx"] = None

# Thêm biến nhớ dữ liệu gốc để kiểm tra khi lưu
if "original_ma_sp" not in st.session_state:
    st.session_state["original_ma_sp"] = ""
if "original_ten_sp" not in st.session_state:
    st.session_state["original_ten_sp"] = ""

if "confirm_delete_idx_sx" not in st.session_state:
    st.session_state["confirm_delete_idx_sx"] = None

danh_sach_tabs = [
    "🧮 1. TÍNH TOÁN & NHẬP LIỆU",
    "📋 2. DANH SÁCH SẢN PHẨM",
    "🧩 3. GHÉP BỘ",
    "⚖️ 4. ĐỊNH LƯỢNG SẢN PHẨM"
]

if "current_tab_sx" not in st.session_state or st.session_state["current_tab_sx"] not in danh_sach_tabs:
    st.session_state["current_tab_sx"] = danh_sach_tabs[0]

# ==========================================
# GIAO DIỆN ĐIỀU HƯỚNG DẠNG NÚT
# ==========================================
st.title("💰 Tính Giá Sản Xuất Sản Phẩm")

nav_cols = st.columns(4)
for idx, tab_label in enumerate(danh_sach_tabs):
    btn_type = "primary" if st.session_state["current_tab_sx"] == tab_label else "secondary"
    if nav_cols[idx].button(tab_label, use_container_width=True, type=btn_type, key=f"nav_sx_{idx}"):
        st.session_state["current_tab_sx"] = tab_label
        st.rerun()

st.markdown("---")

# ==========================================
# TAB 1: TÍNH TOÁN VÀ NHẬP LIỆU
# ==========================================
if st.session_state["current_tab_sx"] == "🧮 1. TÍNH TOÁN & NHẬP LIỆU":
    if st.session_state.get("sx_success_msg"):
        st.success(st.session_state["sx_success_msg"])
        st.session_state["sx_success_msg"] = ""

    if st.session_state["is_editing_sx"]:
        with st.container(border=True):
            c_ed1, c_ed2 = st.columns([3.5, 1.5])
            c_ed1.info("✨ **ĐANG TRONG CHẾ ĐỘ CHỈNH SỬA SẢN PHẨM** (Đổi Mã hoặc Tên sẽ tự động tạo sản phẩm mới)")
            if c_ed2.button("❌ Hủy chỉnh sửa / Thêm mới", use_container_width=True):
                st.session_state["is_editing_sx"] = False
                st.session_state["original_ma_sp"] = ""
                st.session_state["original_ten_sp"] = ""
                st.rerun()

    # --- KHỐI 1: THÔNG TIN SẢN PHẨM ---
    with st.container(border=True):
        st.markdown("#### 📝 Thông Tin Sản Phẩm")
        col_info1, col_info2 = st.columns([1, 2])
        ma_sp = col_info1.text_input("1. Mã Sản Phẩm", placeholder="VD: SP-001", key="sx_ma_in")
        ten_sp = col_info2.text_input("2. Tên Sản Phẩm", placeholder="Nhập tên sản phẩm sản xuất...", key="sx_ten_in")

    # --- KHỐI 2: CHIA 2 CỘT (TRÁI: THÔNG SỐ | PHẢI: PHÂN TÍCH & ĐỊNH GIÁ) ---
    col_input, col_result = st.columns([1.15, 1], gap="medium")

    with col_input:
        st.markdown("#### 📥 Thông Số Đầu Vào")

        with st.expander("🍀 Nhánh 1: Nguyên Vật Liệu", expanded=True):
            c1, c2 = st.columns(2)
            trong_luong = c1.number_input("Trọng lượng (gram)", value=st.session_state.get("sx_tl_in", 34.0), step=0.1, key="sx_tl_in_ui")
            gia_nhua = c2.number_input("Đơn giá nhựa (VNĐ/kg)", value=st.session_state.get("sx_gia_nhua_in", 23000), step=500, key="sx_gia_nhua_in_ui")
            cp_nvl_1sp = (trong_luong / 1000) * gia_nhua
            st.markdown(f"<div class='sub-pill'>💡 Chi phí NVL: <b>{cp_nvl_1sp:,.0f} đ/SP</b></div>", unsafe_allow_html=True)

        with st.expander("⚙️ Nhánh 2: Máy Sản Xuất", expanded=True):
            c3, c4 = st.columns(2)
            gia_may_ca = c3.number_input("Giá máy / Ca 8h (VNĐ)", value=st.session_state.get("sx_gia_may_in", 1700000), step=50000, key="sx_gia_may_in_ui")
            chu_ky = c4.number_input("Chu kỳ (giây)", value=st.session_state.get("sx_chu_ky_in", 40.0), step=1.0, key="sx_chu_ky_in_ui")
            sp_khuon = st.number_input("Số SP / Khuôn", value=st.session_state.get("sx_sp_khuon_in", 2), min_value=1, key="sx_sp_khuon_in_ui")
            sl_ca = (8 * 3600 / chu_ky) * sp_khuon if chu_ky > 0 else 0
            cp_may_1sp = gia_may_ca / sl_ca if sl_ca > 0 else 0
            st.markdown(
                f"<div class='sub-pill'>⚡ Sản lượng: <b>{sl_ca:,.0f} SP/ca</b> &nbsp;|&nbsp; Chi phí máy: <b>{cp_may_1sp:,.0f} đ/SP</b></div>",
                unsafe_allow_html=True
            )

        with st.expander("📦 Nhánh 3: Chi Phí Khác & Khấu Hao", expanded=True):
            c_o1, c_o2, c_o3 = st.columns(3)
            bao_bi = c_o1.number_input("Bao bì (đ/SP)", value=st.session_state.get("sx_bao_bi_in", 10), key="sx_bao_bi_in_ui")
            phu_kien = c_o2.number_input("Phụ kiện (đ/SP)", value=st.session_state.get("sx_phu_kien_in", 100), key="sx_phu_kien_in_ui")
            chi_phi_dong_goi = c_o3.number_input("Đóng gói (đ/SP)", value=st.session_state.get("sx_cp_dong_goi_in", 0), key="sx_cp_dong_goi_in_ui")

            st.markdown("**Tính Phụ gia:**")
            c_pg1, c_pg2 = st.columns(2)
            don_gia_phu_gia = c_pg1.number_input("Đơn giá phụ gia (VNĐ/kg)", value=st.session_state.get("sx_dg_pg_in", 0), step=500, key="sx_dg_pg_in_ui")
            ti_le_phu_gia = c_pg2.number_input("Tỉ lệ phụ gia (%)", value=st.session_state.get("sx_tl_pg_in", 0.0), step=0.1, key="sx_tl_pg_in_ui")
            phu_gia = don_gia_phu_gia * (ti_le_phu_gia * trong_luong / 100) / 1000

            st.markdown("**Tính Khấu hao khuôn:**")
            ck1, ck2 = st.columns(2)
            gia_tri_khuon = ck1.number_input("Giá trị khuôn (VNĐ)", value=st.session_state.get("sx_gia_khuon_in", 0), step=1000000, key="sx_gia_khuon_in_ui")
            sl_khuon_sx = ck2.number_input("SL khuôn sản xuất (Cái)", value=st.session_state.get("sx_sl_khuon_in", 10000), min_value=1, key="sx_sl_khuon_in_ui")
            khau_hao = gia_tri_khuon / sl_khuon_sx if sl_khuon_sx > 0 else 0

            cp_khac_no_kh = bao_bi + phu_kien + chi_phi_dong_goi + phu_gia
            cp_khac = cp_khac_no_kh + khau_hao
            st.markdown(
                f"<div class='sub-pill'>🧪 Phụ gia: <b>{phu_gia:,.2f} đ</b> &nbsp;|&nbsp; Khấu hao: <b>{khau_hao:,.0f} đ/SP</b></div>",
                unsafe_allow_html=True
            )

    gvhb = cp_nvl_1sp + cp_may_1sp + cp_khac

    with col_result:
        st.markdown("#### 📊 Phân Tích Giá Thành & Định Giá")

        # Bảng cơ cấu giá thành thu gọn (tự co giãn, không che giá, không kéo ngang)
        with st.container(border=True):
            st.markdown("**Cơ cấu Giá vốn (1 sản phẩm)**")

            def fmt_pct(val):
                return f"{(val / gvhb * 100):.1f}%" if gvhb > 0 else "0.0%"

            tong_pct = "100.0%" if gvhb > 0 else "0.0%"
            st.markdown(f"""
            <table class="cost-table">
                <thead>
                    <tr>
                        <th style="text-align:left;">Thành phần</th>
                        <th class="num">Thành tiền</th>
                        <th class="num">Tỷ trọng</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>1. Nguyên vật liệu</td>
                        <td class="num">{cp_nvl_1sp:,.0f} đ</td>
                        <td class="num">{fmt_pct(cp_nvl_1sp)}</td>
                    </tr>
                    <tr>
                        <td>2. Máy sản xuất</td>
                        <td class="num">{cp_may_1sp:,.0f} đ</td>
                        <td class="num">{fmt_pct(cp_may_1sp)}</td>
                    </tr>
                    <tr>
                        <td>3. Chi phí khác</td>
                        <td class="num">{cp_khac_no_kh:,.0f} đ</td>
                        <td class="num">{fmt_pct(cp_khac_no_kh)}</td>
                    </tr>
                    <tr>
                        <td>4. Khấu hao khuôn</td>
                        <td class="num">{khau_hao:,.0f} đ</td>
                        <td class="num">{fmt_pct(khau_hao)}</td>
                    </tr>
                    <tr class="total-row">
                        <td>TỔNG GIÁ VỐN</td>
                        <td class="num">{gvhb:,.0f} đ</td>
                        <td class="num">{tong_pct}</td>
                    </tr>
                </tbody>
            </table>
            """, unsafe_allow_html=True)

        # Khối hệ số & giá bán
        with st.container(border=True):
            st.markdown("**Bảng Giá Bán Đề Xuất**")
            hs_dl = st.number_input("Hệ số LN ĐL", value=st.session_state.get("sx_hs_dl_in", 0.6), min_value=0.01, step=0.01, key="sx_hs_dl_in_ui")
            gia_dai_ly = gvhb / hs_dl
            gia_cong_ty = gia_dai_ly / 0.55

            m1, m2 = st.columns(2)
            m1.metric(label="🏪 Giá Đại Lý", value=f"{round(gia_dai_ly):,} đ")
            m2.metric(label="🏢 Giá Công Ty (/ 0.55)", value=f"{round(gia_cong_ty):,} đ")

            st.write("")
            btn_label = "💾 CẬP NHẬT SẢN PHẨM" if st.session_state["is_editing_sx"] else "💾 LƯU / CẬP NHẬT SẢN PHẨM"
            if st.button(btn_label, type="primary", use_container_width=True):
                if ma_sp == "" or ten_sp == "":
                    st.warning("⚠️ Vui lòng nhập Mã và Tên sản phẩm!")
                else:
                    new_data = {
                        "Mã SP": ma_sp,
                        "Tên Sản Phẩm": ten_sp,
                        "Trọng lượng": trong_luong,
                        "Đơn giá nhựa": gia_nhua,
                        "Giá máy": gia_may_ca,
                        "Chu kỳ": chu_ky,
                        "SP Khuôn": sp_khuon,
                        "Bao bì": bao_bi,
                        "Phụ kiện": phu_kien,
                        "Chi phí đóng gói": chi_phi_dong_goi,
                        "Đơn giá phụ gia": don_gia_phu_gia,
                        "Tỉ lệ phụ gia": ti_le_phu_gia,
                        "Giá trị khuôn": gia_tri_khuon,
                        "SL khuôn": sl_khuon_sx,
                        "Hệ số ĐL": hs_dl,
                        "Giá Vốn": round(gvhb),
                        "Giá Đại Lý": round(gia_dai_ly),
                        "Giá Công ty": round(gia_cong_ty)
                    }

                    # --- LOGIC XỬ LÝ LƯU THÔNG MINH ---
                    if st.session_state["is_editing_sx"]:
                        old_ma = st.session_state.get("original_ma_sp", "")
                        old_ten = st.session_state.get("original_ten_sp", "")

                        if ma_sp == old_ma and ten_sp == old_ten:
                            st.session_state["danh_sach_sp"][st.session_state["edit_index_sx"]] = new_data
                            st.session_state["sx_success_msg"] = f"✅ Đã CẬP NHẬT thông số cho sản phẩm '{ten_sp}'! Dữ liệu vẫn giữ nguyên, bạn có thể tạo mã mới."
                        else:
                            st.session_state["danh_sach_sp"].append(new_data)
                            st.session_state["sx_success_msg"] = f"✅ Đã TẠO MỚI sản phẩm '{ten_sp}' thành công từ bản sao gốc!"

                        st.session_state["is_editing_sx"] = False
                        st.session_state["original_ma_sp"] = ""
                        st.session_state["original_ten_sp"] = ""
                    else:
                        st.session_state["danh_sach_sp"].append(new_data)
                        st.session_state["sx_success_msg"] = f"✅ Đã lưu sản phẩm mới '{ten_sp}' thành công! Dữ liệu vẫn giữ nguyên, bạn có thể nhập tiếp."

                    save_data(st.session_state["danh_sach_sp"])
                    st.rerun()

# ==========================================
# TAB 2: DANH SÁCH SẢN PHẨM
# ==========================================
elif st.session_state["current_tab_sx"] == "📋 2. DANH SÁCH SẢN PHẨM":
    h_col1, h_col2 = st.columns([4, 1.2])
    h_col1.subheader("📋 Danh Sách Sản Phẩm Đã Lưu")
    if h_col2.button("🔄 Tải lại dữ liệu", use_container_width=True):
        st.session_state["danh_sach_sp"] = load_data()
        if st.session_state["danh_sach_sp"] is None:
            st.session_state["danh_sach_sp"] = []
        st.rerun()

    if st.session_state["danh_sach_sp"]:
        df = pd.DataFrame(st.session_state["danh_sach_sp"])

        cols_to_show = ["Mã SP", "Tên Sản Phẩm", "Giá Vốn", "Giá Đại Lý", "Giá Công ty"]
        if "Giá Tiêu Chuẩn" in df.columns and "Giá Công ty" not in df.columns:
            df.rename(columns={"Giá Tiêu Chuẩn": "Giá Công ty"}, inplace=True)

        # Thẻ thống kê nhanh
        so_bo = sum(1 for s in st.session_state["danh_sach_sp"] if str(s.get("Tên Sản Phẩm", "")).startswith("[BỘ]"))
        so_don = len(df) - so_bo
        k1, k2, k3 = st.columns(3)
        k1.metric("📦 Tổng sản phẩm", f"{len(df)} mục")
        k2.metric("🔹 Sản phẩm lẻ", f"{so_don} SP")
        k3.metric("🧩 Bộ ghép", f"{so_bo} bộ")

        df_display = df[[c for c in cols_to_show if c in df.columns]].copy()
        for num_c in ["Giá Vốn", "Giá Đại Lý", "Giá Công ty"]:
            if num_c in df_display.columns:
                df_display[num_c] = pd.to_numeric(df_display[num_c], errors="coerce").fillna(0)

        df_display.insert(0, "Chọn", False)

        st.caption("👉 Đánh dấu tích (✓) vào cột **Chọn** trong bảng dưới đây để Chỉnh sửa hoặc Xóa:")
        edited_df = st.data_editor(
            df_display,
            hide_index=True,
            use_container_width=True,
            disabled=cols_to_show,
            column_config={
                "Chọn": st.column_config.CheckboxColumn("Chọn", width="small"),
                "Mã SP": st.column_config.TextColumn("Mã SP", width="small"),
                "Tên Sản Phẩm": st.column_config.TextColumn("Tên Sản Phẩm", width="large"),
                "Giá Vốn": st.column_config.NumberColumn("Giá Vốn", format="%,.0f đ", width="medium"),
                "Giá Đại Lý": st.column_config.NumberColumn("Giá Đại Lý", format="%,.0f đ", width="medium"),
                "Giá Công ty": st.column_config.NumberColumn("Giá Công ty", format="%,.0f đ", width="medium"),
            }
        )

        selected_indices = edited_df[edited_df["Chọn"] == True].index.tolist()

        with st.container(border=True):
            if len(selected_indices) == 0:
                st.info("💡 Vui lòng tích chọn sản phẩm trên bảng để Chỉnh sửa hoặc Xóa.")

            elif len(selected_indices) == 1:
                idx = selected_indices[0]
                sp = st.session_state["danh_sach_sp"][idx]

                st.markdown(f"🎯 Đang chọn: **{sp.get('Mã SP', '')} — {sp.get('Tên Sản Phẩm', 'Sản phẩm')}**")

                c_btn1, c_btn2 = st.columns(2)
                if c_btn1.button("✏️ Chỉnh sửa sản phẩm này", type="primary", use_container_width=True):
                    st.session_state["original_ma_sp"] = sp.get("Mã SP", "")
                    st.session_state["original_ten_sp"] = sp.get("Tên Sản Phẩm", "")

                    st.session_state["sx_ma_in"] = sp.get("Mã SP", "")
                    st.session_state["sx_ten_in"] = sp.get("Tên Sản Phẩm", "")
                    st.session_state["sx_tl_in"] = float(sp.get("Trọng lượng", 34.0)) if isinstance(sp.get("Trọng lượng", 34.0), (int, float)) else 34.0
                    st.session_state["sx_gia_nhua_in"] = int(sp.get("Đơn giá nhựa", 23000))
                    st.session_state["sx_gia_may_in"] = int(sp.get("Giá máy", 1700000))
                    st.session_state["sx_chu_ky_in"] = float(sp.get("Chu kỳ", 40.0))
                    st.session_state["sx_sp_khuon_in"] = int(sp.get("SP Khuôn", 2))
                    st.session_state["sx_bao_bi_in"] = int(sp.get("Bao bì", 10))
                    st.session_state["sx_phu_kien_in"] = int(sp.get("Phụ kiện", 100))
                    st.session_state["sx_cp_dong_goi_in"] = int(sp.get("Chi phí đóng gói", 0))
                    st.session_state["sx_dg_pg_in"] = int(sp.get("Đơn giá phụ gia", 0))
                    st.session_state["sx_tl_pg_in"] = float(sp.get("Tỉ lệ phụ gia", 0.0))
                    st.session_state["sx_gia_khuon_in"] = int(sp.get("Giá trị khuôn", 0))
                    st.session_state["sx_sl_khuon_in"] = int(sp.get("SL khuôn", 10000))
                    st.session_state["sx_hs_dl_in"] = float(sp.get("Hệ số ĐL", 0.6))

                    st.session_state["is_editing_sx"] = True
                    st.session_state["edit_index_sx"] = idx
                    st.session_state["current_tab_sx"] = danh_sach_tabs[0]
                    st.rerun()

                if c_btn2.button("🗑️ Xóa sản phẩm này", use_container_width=True):
                    st.session_state["confirm_delete_idx_sx"] = idx

                if st.session_state.get("confirm_delete_idx_sx") == idx:
                    st.warning(f"⚠️ Bạn có chắc chắn muốn xóa sản phẩm **{sp.get('Tên Sản Phẩm', '')}** không?")
                    col_yes, col_no = st.columns(2)
                    if col_yes.button("✔️ Đồng ý xóa", type="primary", use_container_width=True, key="yes_del_sx"):
                        st.session_state["danh_sach_sp"].pop(idx)
                        save_data(st.session_state["danh_sach_sp"])
                        st.session_state["confirm_delete_idx_sx"] = None
                        st.rerun()
                    if col_no.button("❌ Hủy", use_container_width=True, key="no_del_sx"):
                        st.session_state["confirm_delete_idx_sx"] = None
                        st.rerun()

            else:
                st.markdown(f"🎯 Đang chọn **{len(selected_indices)}** sản phẩm.")
                if st.button("🗑️ Xóa TẤT CẢ sản phẩm đã chọn", use_container_width=True):
                    st.session_state["confirm_delete_multi_sx"] = selected_indices

                if st.session_state.get("confirm_delete_multi_sx") == selected_indices:
                    st.error("⚠️ Bạn có chắc chắn muốn xóa TẤT CẢ các sản phẩm đã chọn không?")
                    col_yes, col_no = st.columns(2)
                    if col_yes.button("✔️ Đồng ý xóa tất cả", type="primary", use_container_width=True, key="yes_del_multi"):
                        for i in sorted(selected_indices, reverse=True):
                            st.session_state["danh_sach_sp"].pop(i)
                        save_data(st.session_state["danh_sach_sp"])
                        st.session_state["confirm_delete_multi_sx"] = None
                        st.rerun()
                    if col_no.button("❌ Hủy", use_container_width=True, key="no_del_multi"):
                        st.session_state["confirm_delete_multi_sx"] = None
                        st.rerun()
    else:
        st.info("Chưa có dữ liệu.")

# ==========================================
# TAB 3: GHÉP BỘ
# ==========================================
elif st.session_state["current_tab_sx"] == "🧩 3. GHÉP BỘ":
    with st.container(border=True):
        st.markdown("#### 🧩 Thông Tin Bộ Sản Phẩm")
        col_info1_bo, col_info2_bo = st.columns([1, 2])
        ma_bo = col_info1_bo.text_input("1. Mã Bộ sản phẩm", placeholder="VD: BO001", key="ma_bo")
        ten_bo = col_info2_bo.text_input("2. Tên Bộ sản phẩm", placeholder="VD: Bộ hộp nắp gài", key="ten_bo")

    col_input_bo, col_result_bo = st.columns([1.15, 1], gap="medium")

    with col_input_bo:
        st.markdown("#### 📥 Thông Số Đầu Vào (Bộ)")

        with st.expander("⚙️ Ghép Bộ Phận (Thân & Nắp)", expanded=True):
            ds_ten_sp = [sp["Tên Sản Phẩm"] for sp in st.session_state["danh_sach_sp"] if not str(sp["Tên Sản Phẩm"]).startswith("[BỘ]")]

            chon_than = st.selectbox("Mục 1: Bộ phận thân", ds_ten_sp, key="sb_than_bo") if ds_ten_sp else None
            chon_nap = st.selectbox("Mục 2: Bộ phận nắp", ds_ten_sp, key="sb_nap_bo") if ds_ten_sp else None

            von_than = 0
            von_nap = 0
            if chon_than:
                von_than = next((s["Giá Vốn"] for s in st.session_state["danh_sach_sp"] if s["Tên Sản Phẩm"] == chon_than), 0)
            if chon_nap:
                von_nap = next((s["Giá Vốn"] for s in st.session_state["danh_sach_sp"] if s["Tên Sản Phẩm"] == chon_nap), 0)

            st.markdown(
                f"<div class='sub-pill'>💰 Vốn thân: <b>{von_than:,} đ</b> &nbsp;|&nbsp; Vốn nắp: <b>{von_nap:,} đ</b></div>",
                unsafe_allow_html=True
            )

        with st.expander("📦 Chi Phí Khác & Khấu Hao Bộ", expanded=True):
            cb1, cb2, cb3 = st.columns(3)
            bb_bo = cb1.number_input("Bao bì bộ (đ)", value=10, key="bb_bo")
            pk_bo = cb2.number_input("Phụ kiện bộ (đ)", value=100, key="pk_bo")
            cp_dong_goi_bo = cb3.number_input("Đóng gói bộ (đ)", value=0, key="cp_dong_goi_bo")

            st.markdown("**Tính Khấu hao khuôn bộ:**")
            ck1_bo, ck2_bo = st.columns(2)
            gt_khuon_bo = ck1_bo.number_input("Giá trị khuôn bộ (VNĐ)", min_value=0, value=0, step=1000000, key="gt_bo")
            sl_sx_bo = ck2_bo.number_input("SL sản xuất bộ (Cái)", min_value=1, value=10000, key="sl_bo")

            kh_bo = gt_khuon_bo / sl_sx_bo if sl_sx_bo > 0 else 0
            cp_khac_bo = bb_bo + pk_bo + cp_dong_goi_bo + kh_bo
            st.markdown(
                f"<div class='sub-pill'>📦 Chi phí khác: <b>{bb_bo + pk_bo + cp_dong_goi_bo:,.0f} đ</b> &nbsp;|&nbsp; Khấu hao: <b>{kh_bo:,.0f} đ/bộ</b></div>",
                unsafe_allow_html=True
            )

    gvhb_bo = von_than + von_nap + cp_khac_bo

    with col_result_bo:
        st.markdown("#### 📊 Kết Quả Tính Giá Bộ")

        with st.container(border=True):
            st.markdown("**Phân tích giá thành bộ**")

            def fmt_pct_bo(val):
                return f"{(val / gvhb_bo * 100):.1f}%" if gvhb_bo > 0 else "0.0%"

            tong_pct_bo = "100.0%" if gvhb_bo > 0 else "0.0%"
            st.markdown(f"""
            <table class="cost-table">
                <thead>
                    <tr>
                        <th style="text-align:left;">Hạng mục</th>
                        <th class="num">Số tiền</th>
                        <th class="num">Tỷ trọng</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>1. Bộ phận thân</td>
                        <td class="num">{von_than:,.0f} đ</td>
                        <td class="num">{fmt_pct_bo(von_than)}</td>
                    </tr>
                    <tr>
                        <td>2. Bộ phận nắp</td>
                        <td class="num">{von_nap:,.0f} đ</td>
                        <td class="num">{fmt_pct_bo(von_nap)}</td>
                    </tr>
                    <tr>
                        <td>3. Bao bì, PK & Đóng gói</td>
                        <td class="num">{bb_bo + pk_bo + cp_dong_goi_bo:,.0f} đ</td>
                        <td class="num">{fmt_pct_bo(bb_bo + pk_bo + cp_dong_goi_bo)}</td>
                    </tr>
                    <tr>
                        <td>4. Khấu hao khuôn</td>
                        <td class="num">{kh_bo:,.0f} đ</td>
                        <td class="num">{fmt_pct_bo(kh_bo)}</td>
                    </tr>
                    <tr class="total-row">
                        <td>GIÁ VỐN (BỘ)</td>
                        <td class="num">{gvhb_bo:,.0f} đ</td>
                        <td class="num">{tong_pct_bo}</td>
                    </tr>
                </tbody>
            </table>
            """, unsafe_allow_html=True)

        with st.container(border=True):
            st.markdown("**Định giá bán Bộ**")
            hs_dl_bo = st.number_input("Hệ số LN ĐL (Bộ)", min_value=0.01, max_value=1.0, value=0.6, step=0.01, key="hs_dl_bo")
            gia_dl_bo = gvhb_bo / hs_dl_bo
            gia_tc_bo = gia_dl_bo / 0.55

            mb1, mb2 = st.columns(2)
            mb1.metric(label="🏪 Giá Đại Lý Bộ", value=f"{round(gia_dl_bo):,} đ")
            mb2.metric(label="🏢 Giá Công Ty Bộ (/ 0.55)", value=f"{round(gia_tc_bo):,} đ")

            st.write("")
            if st.button("💾 LƯU BỘ SẢN PHẨM NÀY", type="primary", use_container_width=True, key="btn_bo"):
                if ma_bo == "" or ten_bo == "":
                    st.warning("⚠️ Vui lòng nhập Mã và Tên bộ sản phẩm!")
                else:
                    tl_than = next((s.get("Trọng lượng", 0) for s in st.session_state["danh_sach_sp"] if s["Tên Sản Phẩm"] == chon_than), 0)
                    tl_nap = next((s.get("Trọng lượng", 0) for s in st.session_state["danh_sach_sp"] if s["Tên Sản Phẩm"] == chon_nap), 0)

                    san_pham_moi_bo = {
                        "Mã SP": ma_bo,
                        "Tên Sản Phẩm": f"[BỘ] {ten_bo}",
                        "Trọng lượng": f"Thân: {tl_than}g | Nắp: {tl_nap}g",
                        "Bao bì": bb_bo,
                        "Phụ kiện": pk_bo,
                        "Chi phí đóng gói": cp_dong_goi_bo,
                        "Giá Vốn": round(gvhb_bo),
                        "Giá Đại Lý": round(gia_dl_bo),
                        "Giá Công ty": round(gia_tc_bo)
                    }
                    st.session_state["danh_sach_sp"].append(san_pham_moi_bo)
                    save_data(st.session_state["danh_sach_sp"])
                    st.success(f"✅ Đã lưu bộ ghép lên đám mây: {ten_bo}")

# ==========================================
# TAB 4: ĐỊNH LƯỢNG SẢN PHẨM
# ==========================================
elif st.session_state["current_tab_sx"] == "⚖️ 4. ĐỊNH LƯỢNG SẢN PHẨM":
    h_col3, h_col4 = st.columns([4, 1.2])
    h_col3.subheader("⚖️ Bảng Định Lượng Sản Phẩm")
    if h_col4.button("🔄 Tải lại dữ liệu", use_container_width=True):
        st.session_state["danh_sach_sp"] = load_data()
        st.rerun()

    if st.session_state["danh_sach_sp"]:
        du_lieu_hien_thi = []

        for sp in st.session_state["danh_sach_sp"]:
            ma_sp = sp.get("Mã SP", "")
            ten_sp = sp.get("Tên Sản Phẩm", "")
            gia_may = sp.get("Giá máy", "")
            chu_ky = sp.get("Chu kỳ", "")
            sp_khuon = sp.get("SP Khuôn", "")
            trong_luong = sp.get("Trọng lượng", "")

            gia_may_hien_thi = f"{gia_may:,.0f}" if isinstance(gia_may, (int, float)) and pd.notna(gia_may) else "N/A"
            chu_ky_hien_thi = f"{chu_ky}" if isinstance(chu_ky, (int, float)) and pd.notna(chu_ky) else "N/A"
            sp_khuon_hien_thi = f"{int(sp_khuon)}" if isinstance(sp_khuon, (int, float)) and pd.notna(sp_khuon) else "N/A"

            if isinstance(trong_luong, (int, float)) and pd.notna(trong_luong):
                tl_hien_thi = f"{trong_luong} g"
            elif isinstance(trong_luong, str):
                tl_hien_thi = trong_luong
            else:
                tl_hien_thi = "N/A"

            du_lieu_hien_thi.append({
                "Mã SP": ma_sp,
                "Tên Sản Phẩm": ten_sp,
                "Giá máy": gia_may_hien_thi,
                "Chu kỳ": chu_ky_hien_thi,
                "SP/Khuôn": sp_khuon_hien_thi,
                "Trọng lượng": tl_hien_thi
            })

        df_dinh_luong = pd.DataFrame(du_lieu_hien_thi)
        st.dataframe(
            df_dinh_luong,
            hide_index=True,
            use_container_width=True,
            column_config={
                "Mã SP": st.column_config.TextColumn("Mã SP", width="small"),
                "Tên Sản Phẩm": st.column_config.TextColumn("Tên Sản Phẩm", width="large"),
                "Giá máy": st.column_config.TextColumn("Giá máy (đ/ca)", width="medium"),
                "Chu kỳ": st.column_config.TextColumn("Chu kỳ (giây)", width="small"),
                "SP/Khuôn": st.column_config.TextColumn("SP/Khuôn", width="small"),
                "Trọng lượng": st.column_config.TextColumn("Trọng lượng", width="medium"),
            }
        )

        # --- XUẤT DỮ LIỆU ---
        st.write("")
        with st.container(border=True):
            st.markdown("#### 📥 Xuất Dữ Liệu Báo Cáo")
            col_export1, col_export2 = st.columns(2)

            with col_export1:
                csv_data = df_dinh_luong.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label="📊 Tải xuống file Excel (CSV)",
                    data=csv_data,
                    file_name='Bang_Dinh_Luong_San_Pham.csv',
                    mime='text/csv',
                    use_container_width=True
                )

            with col_export2:
                def tao_file_pdf(dataframe):
                    pdf = FPDF()
                    pdf.add_page()

                    try:
                        pdf.add_font("CustomFont", "", "arial.ttf", uni=True)
                        pdf.set_font("CustomFont", size=16)
                    except Exception as e:
                        st.error(f"Lỗi nạp font: Đảm bảo bạn đã chép file 'arial.ttf' vào cùng thư mục. Chi tiết lỗi: {e}")
                        pdf.set_font("Arial", size=16)

                    pdf.cell(0, 10, txt="BẢNG ĐỊNH LƯỢNG SẢN PHẨM (WANCHI)", ln=True, align='C')
                    pdf.ln(5)

                    try:
                        pdf.set_font("CustomFont", size=10)
                    except Exception:
                        pdf.set_font("Arial", size=10)

                    pdf.cell(25, 10, "Mã SP", border=1, align='C')
                    pdf.cell(65, 10, "Tên Sản Phẩm", border=1, align='C')
                    pdf.cell(30, 10, "Giá máy", border=1, align='C')
                    pdf.cell(20, 10, "Chu kỳ", border=1, align='C')
                    pdf.cell(20, 10, "SP/Khuôn", border=1, align='C')
                    pdf.cell(30, 10, "Trọng lượng", border=1, align='C')
                    pdf.ln()

                    for i, row in dataframe.iterrows():
                        ma = str(row['Mã SP'])
                        ten = str(row['Tên Sản Phẩm'])
                        gm = str(row['Giá máy'])
                        ck = str(row['Chu kỳ'])
                        spk = str(row['SP/Khuôn'])
                        tl = str(row['Trọng lượng'])

                        pdf.cell(25, 10, ma, border=1, align='C')
                        pdf.cell(65, 10, ten, border=1, align='L')
                        pdf.cell(30, 10, gm, border=1, align='C')
                        pdf.cell(20, 10, ck, border=1, align='C')
                        pdf.cell(20, 10, spk, border=1, align='C')
                        pdf.cell(30, 10, tl, border=1, align='C')
                        pdf.ln()

                    return bytes(pdf.output())

                pdf_bytes = tao_file_pdf(df_dinh_luong)
                st.download_button(
                    label="📄 Tải xuống file PDF",
                    data=pdf_bytes,
                    file_name='Bang_Dinh_Luong_San_Pham.pdf',
                    mime='application/pdf',
                    type="primary",
                    use_container_width=True
                )

    else:
        st.info("Chưa có dữ liệu sản phẩm.")
