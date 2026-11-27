import streamlit as st
import pandas as pd
import time
from fpdf import FPDF
import unicodedata
from datetime import datetime
from sqlalchemy import text, inspect
import os
import io

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="Tính Giá Gia Công", layout="wide")

# --- KHÓA BẢO MẬT TỪ TRANG CHỦ ---
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
</style>
""", unsafe_allow_html=True)

# ==========================================
# KẾT NỐI NEON (POSTGRESQL)
# ==========================================
try:
    conn = st.connection("postgresql", type="sql")
except Exception as e:
    st.error("Chưa thể kết nối Database Neon. Vui lòng kiểm tra lại cấu hình.")
    st.stop()

# ==========================================
# 🛡️ LÍNH GÁC (GATEKEEPER) BẢO VỆ DỮ LIỆU
# ==========================================
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
    st.warning("👉 Hệ thống tự động vô hiệu hóa mọi chức năng để bảo vệ dữ liệu. Vui lòng ấn F5 (Tải lại trang) cho đến khi thông báo này biến mất.")
    st.stop()

# ==========================================
# HÀM XỬ LÝ DỮ LIỆU (CÓ KHÓA BẢO VỆ)
# ==========================================
def load_data_gc():
    try:
        inspector = inspect(conn.engine)
        if not inspector.has_table("wanchi_giacong"):
            st.session_state["db_load_success"] = True
            return []
        df = pd.read_sql("SELECT * FROM wanchi_giacong", con=conn.engine)
        st.session_state["db_load_success"] = True
        if not df.empty:
            if "Hệ số ĐL" in df.columns:
                df.rename(columns={"Hệ số ĐL": "Hệ số Báo giá"}, inplace=True)
            if "Giá Đại Lý" in df.columns:
                df.rename(columns={"Giá Đại Lý": "Báo giá khách"}, inplace=True)
            if "Giá Công ty" in df.columns:
                df.drop(columns=["Giá Công ty"], inplace=True)
            if "Giá Tiêu Chuẩn" in df.columns:
                df.drop(columns=["Giá Tiêu Chuẩn"], inplace=True)
            return df.to_dict('records')
        return []
    except Exception as e:
        st.session_state["db_load_success"] = False
        st.warning("⏳ Máy chủ dữ liệu đang mất kết nối. Chưa thể tải dữ liệu.")
        return None

def save_data_gc(data_list):
    if not st.session_state.get("db_load_success", False):
        st.error("🚨 LỆNH BỊ CHẶN: Không thể lưu! Dữ liệu gốc từ máy chủ chưa được tải xuống hoàn tất. Nếu lưu bây giờ sẽ xóa mất dữ liệu cũ. Vui lòng bấm F5 (Tải lại trang).")
        st.stop()
        return

    try:
        df = pd.DataFrame(data_list)
        if df.empty:
            df = pd.DataFrame(columns=["Mã SP", "Tên Sản Phẩm", "Trọng lượng", "Đơn giá nhựa", "Giá máy", "Chu kỳ", "SP Khuôn", "Bao bì", "Phụ kiện", "Đơn giá phụ gia", "Tỉ lệ phụ gia", "Hệ số Báo giá", "Giá Vốn", "Báo giá khách"])
        df.to_sql("wanchi_giacong", con=conn.engine, if_exists='replace', index=False)
    except Exception:
        pass

# ==========================================
# KHỞI TẠO BỘ NHỚ LƯU TRỮ
# ==========================================
if "danh_sach_gc" not in st.session_state or st.session_state["danh_sach_gc"] is None:
    loaded = load_data_gc()
    st.session_state["danh_sach_gc"] = loaded if loaded is not None else []

if st.session_state["danh_sach_gc"] is None:
    st.session_state["danh_sach_gc"] = []

if "confirm_delete_idx_gc" not in st.session_state:
    st.session_state["confirm_delete_idx_gc"] = None

if "is_editing_gc" not in st.session_state:
    st.session_state["is_editing_gc"] = False
    st.session_state["edit_index_gc"] = None

if "original_ma_sp_gc" not in st.session_state:
    st.session_state["original_ma_sp_gc"] = ""
if "original_ten_sp_gc" not in st.session_state:
    st.session_state["original_ten_sp_gc"] = ""

danh_sach_tabs = ["🧮 1. TÍNH TOÁN & NHẬP LIỆU", "📋 2. DANH SÁCH GIA CÔNG", "⚖️ 3. ĐỊNH LƯỢNG SẢN PHẨM"]

if "current_tab_gc" not in st.session_state or st.session_state["current_tab_gc"] not in danh_sach_tabs:
    st.session_state["current_tab_gc"] = danh_sach_tabs[0]

# ==========================================
# TIÊU ĐỀ & THANH ĐIỀU HƯỚNG DẠNG NÚT
# ==========================================
st.title("⚙️ Tính Giá Gia Công Sản Phẩm")

nav_cols = st.columns(3)
for idx, tab_label in enumerate(danh_sach_tabs):
    btn_type = "primary" if st.session_state["current_tab_gc"] == tab_label else "secondary"
    if nav_cols[idx].button(tab_label, use_container_width=True, type=btn_type, key=f"nav_gc_{idx}"):
        st.session_state["current_tab_gc"] = tab_label
        st.rerun()

st.markdown("---")

# ==========================================
# TAB 1: TÍNH TOÁN VÀ NHẬP LIỆU
# ==========================================
if st.session_state["current_tab_gc"] == "🧮 1. TÍNH TOÁN & NHẬP LIỆU":
    if st.session_state.get("gc_success_msg"):
        st.success(st.session_state["gc_success_msg"])
        st.session_state["gc_success_msg"] = ""

    if st.session_state["is_editing_gc"]:
        with st.container(border=True):
            c_ed1, c_ed2 = st.columns([3.5, 1.5])
            c_ed1.info("✨ **ĐANG TRONG CHẾ ĐỘ CHỈNH SỬA SẢN PHẨM GIA CÔNG** (Đổi Mã hoặc Tên sẽ tự tạo bản sao mới)")
            if c_ed2.button("❌ Hủy chỉnh sửa / Thêm mới", use_container_width=True):
                st.session_state["is_editing_gc"] = False
                st.session_state["original_ma_sp_gc"] = ""
                st.session_state["original_ten_sp_gc"] = ""
                st.rerun()

    # --- KHỐI 1: THÔNG TIN ĐỊNH DANH SẢN PHẨM ---
    with st.container(border=True):
        st.markdown("#### 📝 Thông Tin Sản Phẩm Gia Công")
        col_info1, col_info2 = st.columns([1, 2])
        ma_sp = col_info1.text_input("1. Mã Sản Phẩm", placeholder="VD: GC-001", key="gc_ma_in")
        ten_sp = col_info2.text_input("2. Tên Sản Phẩm", placeholder="Nhập tên sản phẩm gia công...", key="gc_ten_in")

    # --- KHỐI 2: CHIA 2 CỘT (TRÁI: NHẬP THÔNG SỐ | PHẢI: PHÂN TÍCH & BÁO GIÁ) ---
    col_input, col_result = st.columns([1.25, 1], gap="medium")

    with col_input:
        st.markdown("#### 📥 Thông Số Đầu Vào")

        with st.expander("🍀 Nhánh 1: Nguyên Vật Liệu", expanded=True):
            c1, c2 = st.columns(2)
            trong_luong = c1.number_input("Trọng lượng (gram)", value=st.session_state.get("gc_tl_in", 34.0), step=0.1, key="gc_tl_in_ui")
            gia_nhua = c2.number_input("Đơn giá nhựa (VNĐ/kg)", value=st.session_state.get("gc_gia_nhua_in", 23000), step=500, key="gc_gia_nhua_in_ui")
            cp_nvl_1sp = (trong_luong / 1000) * gia_nhua
            st.markdown(f"<div class='sub-pill'>💡 Chi phí NVL: <b>{cp_nvl_1sp:,.0f} đ/SP</b></div>", unsafe_allow_html=True)

        with st.expander("⚙️ Nhánh 2: Máy Sản Xuất", expanded=True):
            c3, c4 = st.columns(2)
            gia_may_ca = c3.number_input("Giá máy / Ca 8h (VNĐ)", value=st.session_state.get("gc_gia_may_in", 1700000), step=50000, key="gc_gia_may_in_ui")
            chu_ky = c4.number_input("Chu kỳ (giây)", value=st.session_state.get("gc_chu_ky_in", 40.0), step=1.0, key="gc_chu_ky_in_ui")
            sp_khuon = st.number_input("Số SP / Khuôn", value=st.session_state.get("gc_sp_khuon_in", 2), min_value=1, key="gc_sp_khuon_in_ui")
            sl_ca = (8 * 3600 / chu_ky) * sp_khuon if chu_ky > 0 else 0
            cp_may_1sp = gia_may_ca / sl_ca if sl_ca > 0 else 0
            st.markdown(
                f"<div class='sub-pill'>⚡ Sản lượng: <b>{sl_ca:,.0f} SP/ca</b> &nbsp;|&nbsp; Chi phí máy: <b>{cp_may_1sp:,.0f} đ/SP</b></div>",
                unsafe_allow_html=True
            )

        with st.expander("📦 Nhánh 3: Chi Phí Khác (Bao bì, Phụ kiện, Phụ gia)", expanded=True):
            c_bb, c_pk = st.columns(2)
            bao_bi = c_bb.number_input("Bao bì (VNĐ/SP)", value=st.session_state.get("gc_bao_bi_in", 10), key="gc_bao_bi_in_ui")
            phu_kien = c_pk.number_input("Phụ kiện (VNĐ/SP)", value=st.session_state.get("gc_phu_kien_in", 100), key="gc_phu_kien_in_ui")

            st.markdown("**Tính Phụ gia:**")
            c_pg1, c_pg2 = st.columns(2)
            don_gia_phu_gia = c_pg1.number_input("Đơn giá phụ gia (VNĐ/kg)", value=st.session_state.get("gc_dg_pg_in", 0), step=500, key="gc_dg_pg_in_ui")
            ti_le_phu_gia = c_pg2.number_input("Tỉ lệ phụ gia (%)", value=st.session_state.get("gc_tl_pg_in", 0.0), step=0.1, key="gc_tl_pg_in_ui")
            phu_gia = don_gia_phu_gia * (ti_le_phu_gia * trong_luong / 100) / 1000
            cp_khac = bao_bi + phu_kien + phu_gia
            st.markdown(
                f"<div class='sub-pill'>🧪 Phụ gia: <b>{phu_gia:,.2f} đ/SP</b> &nbsp;|&nbsp; Tổng chi phí khác: <b>{cp_khac:,.0f} đ/SP</b></div>",
                unsafe_allow_html=True
            )

    gvhb = cp_nvl_1sp + cp_may_1sp + cp_khac

    with col_result:
        st.markdown("#### 📊 Phân Tích Giá Thành & Báo Giá")

        # Bảng cơ cấu giá thành (có tỷ trọng %)
        with st.container(border=True):
            st.markdown("**Cơ cấu Giá vốn (1 sản phẩm)**")

            def fmt_pct(val):
                return f"{(val / gvhb * 100):.1f}%" if gvhb > 0 else "0.0%"

            df_summary = pd.DataFrame({
                "Thành phần": [
                    "1. Nguyên vật liệu",
                    "2. Máy sản xuất",
                    "3. Chi phí khác (Bao bì, PK, Phụ gia)",
                    "TỔNG GIÁ VỐN"
                ],
                "Thành tiền (VNĐ)": [cp_nvl_1sp, cp_may_1sp, cp_khac, gvhb],
                "Tỷ trọng": [fmt_pct(cp_nvl_1sp), fmt_pct(cp_may_1sp), fmt_pct(cp_khac), "100.0%" if gvhb > 0 else "0.0%"]
            })
            st.dataframe(
                df_summary,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "Thành phần": st.column_config.TextColumn("Thành phần chi phí", width="large"),
                    "Thành tiền (VNĐ)": st.column_config.NumberColumn("Thành tiền (đ)", format="%,.0f", width="medium"),
                    "Tỷ trọng": st.column_config.TextColumn("Tỷ trọng", width="small"),
                }
            )

        # Khối hệ số & kết quả báo giá
        with st.container(border=True):
            st.markdown("**Định giá bán cho khách**")
            hs_bg = st.number_input(
                "Hệ số LN Báo giá",
                value=st.session_state.get("gc_hs_bg_in", 0.6),
                min_value=0.01,
                step=0.01,
                key="gc_hs_bg_in_ui"
            )
            bao_gia_khach = gvhb / hs_bg
            loi_nhuan_sp = round(bao_gia_khach) - round(gvhb)

            m1, m2 = st.columns(2)
            m1.metric(label="💵 Tổng Giá Vốn", value=f"{round(gvhb):,} đ")
            m2.metric(label="📈 Lợi Nhuận / SP", value=f"{loi_nhuan_sp:,} đ")

            st.metric(label="🏷️ BÁO GIÁ KHÁCH ĐỀ XUẤT", value=f"{round(bao_gia_khach):,} VNĐ")

            st.write("")
            btn_save_label = "💾 CẬP NHẬT SẢN PHẨM" if st.session_state["is_editing_gc"] else "💾 LƯU / CẬP NHẬT SẢN PHẨM"
            if st.button(btn_save_label, type="primary", use_container_width=True):
                if ma_sp == "" or ten_sp == "":
                    st.warning("⚠️ Vui lòng nhập Mã và Tên sản phẩm!")
                else:
                    new_data = {
                        "Mã SP": ma_sp, "Tên Sản Phẩm": ten_sp, "Trọng lượng": trong_luong, "Đơn giá nhựa": gia_nhua,
                        "Giá máy": gia_may_ca, "Chu kỳ": chu_ky, "SP Khuôn": sp_khuon, "Bao bì": bao_bi, "Phụ kiện": phu_kien,
                        "Đơn giá phụ gia": don_gia_phu_gia, "Tỉ lệ phụ gia": ti_le_phu_gia, "Hệ số Báo giá": hs_bg,
                        "Giá Vốn": round(gvhb), "Báo giá khách": round(bao_gia_khach)
                    }

                    if st.session_state["is_editing_gc"]:
                        old_ma = st.session_state.get("original_ma_sp_gc", "")
                        old_ten = st.session_state.get("original_ten_sp_gc", "")

                        if ma_sp == old_ma and ten_sp == old_ten:
                            st.session_state["danh_sach_gc"][st.session_state["edit_index_gc"]] = new_data
                            st.session_state["gc_success_msg"] = f"✅ Đã CẬP NHẬT thông số cho sản phẩm gia công '{ten_sp}'! Dữ liệu vẫn giữ nguyên, bạn có thể tạo mã mới."
                        else:
                            st.session_state["danh_sach_gc"].append(new_data)
                            st.session_state["gc_success_msg"] = f"✅ Đã TẠO MỚI sản phẩm gia công '{ten_sp}' thành công từ bản sao gốc!"

                        st.session_state["is_editing_gc"] = False
                        st.session_state["original_ma_sp_gc"] = ""
                        st.session_state["original_ten_sp_gc"] = ""
                    else:
                        st.session_state["danh_sach_gc"].append(new_data)
                        st.session_state["gc_success_msg"] = f"✅ Đã lưu sản phẩm gia công mới '{ten_sp}' thành công! Dữ liệu vẫn giữ nguyên, bạn có thể nhập tiếp."

                    save_data_gc(st.session_state["danh_sach_gc"])
                    st.rerun()

# ==========================================
# TAB 2: DANH SÁCH SẢN PHẨM GIA CÔNG
# ==========================================
elif st.session_state["current_tab_gc"] == "📋 2. DANH SÁCH GIA CÔNG":
    h_col1, h_col2 = st.columns([4, 1.2])
    h_col1.subheader("📋 Danh Sách Sản Phẩm Gia Công Đã Lưu")
    if h_col2.button("🔄 Tải lại dữ liệu", use_container_width=True):
        st.session_state["danh_sach_gc"] = load_data_gc()
        if st.session_state["danh_sach_gc"] is None:
            st.session_state["danh_sach_gc"] = []
        st.rerun()

    if st.session_state["danh_sach_gc"]:
        df = pd.DataFrame(st.session_state["danh_sach_gc"])

        # Thanh tóm tắt nhanh
        k1, k2 = st.columns(2)
        k1.metric("📦 Tổng số sản phẩm đã lưu", f"{len(df)} sản phẩm")
        avg_bg = pd.to_numeric(df["Báo giá khách"], errors="coerce").fillna(0).mean() if "Báo giá khách" in df.columns else 0
        k2.metric("🏷️ Báo giá khách trung bình", f"{avg_bg:,.0f} đ")

        cols_to_show = ["Mã SP", "Tên Sản Phẩm", "Giá Vốn", "Báo giá khách"]
        df_display = df[[c for c in cols_to_show if c in df.columns]].copy()
        for num_c in ["Giá Vốn", "Báo giá khách"]:
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
                "Mã SP": st.column_config.TextColumn("Mã SP", width="medium"),
                "Tên Sản Phẩm": st.column_config.TextColumn("Tên Sản Phẩm", width="large"),
                "Giá Vốn": st.column_config.NumberColumn("Giá Vốn (VNĐ)", format="%,.0f đ", width="medium"),
                "Báo giá khách": st.column_config.NumberColumn("Báo giá khách (VNĐ)", format="%,.0f đ", width="medium"),
            }
        )

        selected_indices = edited_df[edited_df["Chọn"] == True].index.tolist()

        with st.container(border=True):
            if len(selected_indices) == 0:
                st.info("💡 Vui lòng tích chọn sản phẩm trên bảng để Chỉnh sửa hoặc Xóa.")

            elif len(selected_indices) == 1:
                idx = selected_indices[0]
                sp = st.session_state["danh_sach_gc"][idx]

                st.markdown(f"🎯 Đang chọn: **{sp.get('Mã SP', '')} — {sp.get('Tên Sản Phẩm', 'Sản phẩm')}**")

                c_btn1, c_btn2 = st.columns(2)
                if c_btn1.button("✏️ Chỉnh sửa sản phẩm này", type="primary", use_container_width=True):
                    st.session_state["original_ma_sp_gc"] = sp.get("Mã SP", "")
                    st.session_state["original_ten_sp_gc"] = sp.get("Tên Sản Phẩm", "")

                    st.session_state["gc_ma_in"] = sp.get("Mã SP", "")
                    st.session_state["gc_ten_in"] = sp.get("Tên Sản Phẩm", "")

                    def safe_parse(val, default, is_int=True):
                        try:
                            if pd.isna(val) or val == "":
                                return default
                            return int(float(val)) if is_int else float(val)
                        except Exception:
                            return default

                    st.session_state["gc_tl_in"] = safe_parse(sp.get("Trọng lượng"), 34.0, False)
                    st.session_state["gc_gia_nhua_in"] = safe_parse(sp.get("Đơn giá nhựa"), 23000)
                    st.session_state["gc_gia_may_in"] = safe_parse(sp.get("Giá máy"), 1700000)
                    st.session_state["gc_chu_ky_in"] = safe_parse(sp.get("Chu kỳ"), 40.0, False)
                    st.session_state["gc_sp_khuon_in"] = safe_parse(sp.get("SP Khuôn"), 2)
                    st.session_state["gc_bao_bi_in"] = safe_parse(sp.get("Bao bì"), 10)
                    st.session_state["gc_phu_kien_in"] = safe_parse(sp.get("Phụ kiện"), 100)
                    st.session_state["gc_dg_pg_in"] = safe_parse(sp.get("Đơn giá phụ gia"), 0)
                    st.session_state["gc_tl_pg_in"] = safe_parse(sp.get("Tỉ lệ phụ gia"), 0.0, False)
                    st.session_state["gc_hs_bg_in"] = safe_parse(sp.get("Hệ số Báo giá"), 0.6, False)

                    st.session_state["is_editing_gc"] = True
                    st.session_state["edit_index_gc"] = idx
                    st.session_state["current_tab_gc"] = danh_sach_tabs[0]
                    st.rerun()

                if c_btn2.button("🗑️ Xóa sản phẩm này", use_container_width=True):
                    st.session_state["confirm_delete_idx_gc"] = idx

                if st.session_state.get("confirm_delete_idx_gc") == idx:
                    st.warning(f"⚠️ Bạn có chắc chắn muốn xóa sản phẩm **{sp.get('Tên Sản Phẩm', '')}** không?")
                    col_yes, col_no = st.columns(2)
                    if col_yes.button("✔️ Đồng ý xóa", type="primary", use_container_width=True, key="yes_del_gc"):
                        st.session_state["danh_sach_gc"].pop(idx)
                        save_data_gc(st.session_state["danh_sach_gc"])
                        st.session_state["confirm_delete_idx_gc"] = None
                        st.rerun()
                    if col_no.button("❌ Hủy", use_container_width=True, key="no_del_gc"):
                        st.session_state["confirm_delete_idx_gc"] = None
                        st.rerun()

            else:
                st.markdown(f"🎯 Đang chọn **{len(selected_indices)}** sản phẩm.")
                if st.button("🗑️ Xóa TẤT CẢ sản phẩm đã chọn", use_container_width=True):
                    st.session_state["confirm_delete_multi_gc"] = selected_indices

                if st.session_state.get("confirm_delete_multi_gc") == selected_indices:
                    st.error("⚠️ Bạn có chắc chắn muốn xóa TẤT CẢ các sản phẩm đã chọn không?")
                    col_yes, col_no = st.columns(2)
                    if col_yes.button("✔️ Đồng ý xóa tất cả", type="primary", use_container_width=True, key="yes_del_multi_gc"):
                        for i in sorted(selected_indices, reverse=True):
                            st.session_state["danh_sach_gc"].pop(i)
                        save_data_gc(st.session_state["danh_sach_gc"])
                        st.session_state["confirm_delete_multi_gc"] = None
                        st.rerun()
                    if col_no.button("❌ Hủy", use_container_width=True, key="no_del_multi_gc"):
                        st.session_state["confirm_delete_multi_gc"] = None
                        st.rerun()
    else:
        st.info("Chưa có dữ liệu.")

# ==========================================
# TAB 3: ĐỊNH LƯỢNG SẢN PHẨM (GIA CÔNG)
# ==========================================
elif st.session_state["current_tab_gc"] == "⚖️ 3. ĐỊNH LƯỢNG SẢN PHẨM":
    h_col3, h_col4 = st.columns([4, 1.2])
    h_col3.subheader("⚖️ Bảng Định Lượng Sản Phẩm Gia Công")
    if h_col4.button("🔄 Tải lại dữ liệu", use_container_width=True, key="refresh_dl_gc"):
        st.session_state["danh_sach_gc"] = load_data_gc()
        st.rerun()

    if st.session_state["danh_sach_gc"]:
        du_lieu_hien_thi = []

        for sp in st.session_state["danh_sach_gc"]:
            ma_sp = sp.get("Mã SP", "")
            ten_sp = sp.get("Tên Sản Phẩm", "")
            trong_luong = sp.get("Trọng lượng", 0)

            gia_may = sp.get("Giá máy", 0)
            chu_ky = sp.get("Chu kỳ", 0)
            sp_khuon = sp.get("SP Khuôn", 0)

            if pd.isna(trong_luong):
                tl_hien_thi = "0 g"
            elif isinstance(trong_luong, (int, float)):
                tl_hien_thi = f"{trong_luong} g"
            else:
                tl_hien_thi = str(trong_luong)

            try:
                gia_may_str = f"{float(gia_may):,.0f}"
            except Exception:
                gia_may_str = str(gia_may)

            du_lieu_hien_thi.append({
                "Mã SP": ma_sp,
                "Tên Sản Phẩm": ten_sp,
                "Giá máy": gia_may_str,
                "Chu kỳ": str(chu_ky),
                "SP/Khuôn": str(sp_khuon),
                "Định Lượng (Trọng lượng)": tl_hien_thi
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
                "Định Lượng (Trọng lượng)": st.column_config.TextColumn("Định Lượng", width="medium"),
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
                    file_name='Bang_Dinh_Luong_Gia_Cong.csv',
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
                        st.error("Lỗi nạp font: Đảm bảo bạn đã chép file 'arial.ttf' vào cùng thư mục.")
                        pdf.set_font("Arial", size=16)

                    pdf.cell(0, 10, txt="BẢNG ĐỊNH LƯỢNG SẢN PHẨM GIA CÔNG (WANCHI)", ln=True, align='C')
                    pdf.ln(5)

                    try:
                        pdf.set_font("CustomFont", size=10)
                    except Exception:
                        pdf.set_font("Arial", size=10)

                    pdf.cell(20, 10, "Mã SP", border=1, align='C')
                    pdf.cell(50, 10, "Tên Sản Phẩm", border=1, align='C')
                    pdf.cell(30, 10, "Giá máy", border=1, align='C')
                    pdf.cell(20, 10, "Chu kỳ", border=1, align='C')
                    pdf.cell(25, 10, "SP/Khuôn", border=1, align='C')
                    pdf.cell(45, 10, "Trọng Lượng", border=1, align='C')
                    pdf.ln()

                    for i, row in dataframe.iterrows():
                        ma = str(row['Mã SP'])
                        ten = str(row['Tên Sản Phẩm'])
                        gm = str(row['Giá máy'])
                        ck = str(row['Chu kỳ'])
                        spk = str(row['SP/Khuôn'])
                        tl = str(row['Định Lượng (Trọng lượng)'])

                        pdf.cell(20, 10, ma, border=1, align='C')
                        pdf.cell(50, 10, ten, border=1, align='L')
                        pdf.cell(30, 10, gm, border=1, align='C')
                        pdf.cell(20, 10, ck, border=1, align='C')
                        pdf.cell(25, 10, spk, border=1, align='C')
                        pdf.cell(45, 10, tl, border=1, align='C')
                        pdf.ln()

                    return bytes(pdf.output())

                pdf_bytes = tao_file_pdf(df_dinh_luong)
                st.download_button(
                    label="📄 Tải xuống file PDF",
                    data=pdf_bytes,
                    file_name='Bang_Dinh_Luong_Gia_Cong.pdf',
                    mime='application/pdf',
                    type="primary",
                    use_container_width=True
                )

    else:
        st.info("Chưa có dữ liệu sản phẩm gia công.")
