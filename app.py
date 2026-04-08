
import streamlit as st
import time
from PIL import Image
import math
import services.detector as detector
import services.ocr as ocr
import services.storage as storage

st.set_page_config(
    page_title="Arabic Plate Gate (YOLO+Gemini)",
    page_icon="🚗",
    layout="wide"
)

# --- CSS Styling ---
st.markdown("""
<style>
    .stButton>button { width: 100%; font-weight: bold; }
    .access-card { padding: 20px; border-radius: 15px; color: white; text-align: center; margin-bottom: 20px; }
    .granted { background: linear-gradient(135deg, #10B981 0%, #059669 100%); box-shadow: 0 4px 14px rgba(16, 185, 129, 0.4); }
    .denied { background: linear-gradient(135deg, #EF4444 0%, #DC2626 100%); box-shadow: 0 4px 14px rgba(239, 68, 68, 0.4); }
    .big-text { font-size: 3rem; font-weight: 800; margin: 0; }
    .sub-text { font-size: 1.5rem; opacity: 0.9; }
    .plate-display { font-family: 'Noto Sans Arabic', sans-serif; font-size: 2rem; font-weight: bold; background: white; color: #333; padding: 10px; border-radius: 8px; display: inline-block; margin-top: 10px;}
    
    /* Pagination style */
    div[data-testid="stMetricValue"] { font-size: 1.5rem; }
</style>
""", unsafe_allow_html=True)

# --- Sidebar ---
st.sidebar.title("🚘 智能门岗系统")
st.sidebar.caption("Core: YOLOv8 (Locate) + Gemini (Recognize)")
tab = st.sidebar.radio("导航", ["门岗监控", "车辆数据库"])

if tab == "门岗监控":
    st.title("📹 实时识别监控")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("图像采集")
        input_method = st.radio("选择输入源", ["上传图片", "拍照"], horizontal=True)
        
        img_file = None
        if input_method == "上传图片":
            img_file = st.file_uploader("选择车牌图片", type=['jpg', 'png', 'jpeg'])
        else:
            img_file = st.camera_input("拍摄车牌")

        if img_file:
            # Load and display raw image
            image = Image.open(img_file)
            st.image(image, caption="原始图像", use_container_width=True)
            
            process_btn = st.button("⚡ 立即识别", type="primary")
            
            if process_btn:
                with st.spinner("🤖 正在处理 (YOLO定位 -> 裁剪 -> Gemini识别)..."):
                    # 1. Detection & Crop
                    processed_img, detect_info = detector.optimize_and_crop(image)
                    st.toast(detect_info, icon="📐")
                    
                    # Show cropped view in sidebar or below
                    with st.expander("查看 AI 裁剪区域 (文本框)", expanded=True):
                        st.image(processed_img, width=300)

                    # 2. OCR
                    result = ocr.recognize_plate(processed_img)
                    
                    if "error" in result:
                        st.error(result["error"])
                    else:
                        st.session_state['last_result'] = result
                        # 3. Access Check
                        auth_record = storage.check_access(result.get("plateNumber", ""))
                        st.session_state['auth_record'] = auth_record

    with col2:
        st.subheader("通行状态")
        if 'last_result' in st.session_state:
            res = st.session_state['last_result']
            auth = st.session_state.get('auth_record')
            
            is_granted = auth is not None
            status_class = "granted" if is_granted else "denied"
            status_text = "允许通行" if is_granted else "禁止入内"
            status_sub = "ACCESS GRANTED" if is_granted else "ACCESS DENIED"
            icon = "✅" if is_granted else "🚫"

            # Render Status Card
            st.markdown(f"""
            <div class="access-card {status_class}">
                <div style="font-size: 4rem; margin-bottom: 10px;">{icon}</div>
                <h1 class="big-text">{status_text}</h1>
                <h2 class="sub-text">{status_sub}</h2>
                <div class="plate-display">{res.get('plateNumber', 'Unknown')}</div>
            </div>
            """, unsafe_allow_html=True)

            # Details
            st.markdown("### 📋 详细信息")
            d_col1, d_col2 = st.columns(2)
            with d_col1:
                st.info(f"**转写:** {res.get('transliteration')}")
                st.info(f"**中文:** {res.get('plateNumberZh')}")
            with d_col2:
                st.success(f"**国家/地区:** {res.get('countryZh')}")
                st.warning(f"**置信度:** {int(res.get('confidence', 0)*100)}%")

            if auth:
                # FIX: Use snake_case 'owner_name' to match SQLite column
                st.success(f"👤 **已登记车主:** {auth['owner_name']}")
            else:
                st.error("⚠️ 车辆未在数据库中登记")
                
            st.markdown(f"> **AI 说明:** {res.get('explanationZh')}")

        else:
            st.info("👈 请在左侧上传图片并点击识别")
            st.image("https://placehold.co/600x400?text=Waiting+for+Scan", use_container_width=True)

elif tab == "车辆数据库":
    st.title("🗄️ 车辆白名单管理")

    # Initialize session state for form inputs
    if 'form_plate' not in st.session_state:
        st.session_state['form_plate'] = ""
    if 'form_trans' not in st.session_state:
        st.session_state['form_trans'] = ""
    if 'form_owner' not in st.session_state:
        st.session_state['form_owner'] = ""
    if 'db_crop_preview' not in st.session_state:
        st.session_state['db_crop_preview'] = None
    
    # 1. ADD NEW PLATE SECTION
    with st.expander("➕ 添加新车辆", expanded=False):
        # ... (Auto-fill Logic Same as Before) ...
        st.markdown("##### 📸 快速录入助手")
        c_up, c_act = st.columns([3, 1])
        with c_up:
            db_img_file = st.file_uploader("上传车牌图片", type=['jpg', 'png', 'jpeg'], key="db_upload", label_visibility="collapsed")
        
        if db_img_file:
            with c_act:
                 if st.button("✨ 识别并填写", type="secondary"):
                    image = Image.open(db_img_file)
                    with st.spinner("Processing..."):
                        processed, info = detector.optimize_and_crop(image)
                        st.session_state['db_crop_preview'] = processed
                        res = ocr.recognize_plate(processed)
                        if "error" not in res:
                            st.session_state['form_plate'] = res.get('plateNumber', '')
                            st.session_state['form_trans'] = res.get('plateNumberZh') or res.get('transliteration', '')
                            st.session_state['temp_msg'] = {"type": "success", "text": f"识别成功！{info}"}
                            st.rerun()
                        else:
                            st.error(res["error"])
        
        if st.session_state['db_crop_preview']:
            st.image(st.session_state['db_crop_preview'], caption="AI 自动裁剪区域", width=300)

        st.divider()

        # Form
        def add_vehicle_callback():
            if st.session_state.form_plate and st.session_state.form_owner:
                storage.add_authorized_plate(
                    st.session_state.form_plate, 
                    st.session_state.form_owner, 
                    st.session_state.form_trans
                )
                st.session_state.temp_msg = {"type": "success", "text": "车辆添加成功！"}
                st.session_state.form_plate = ""
                st.session_state.form_trans = ""
                st.session_state.form_owner = ""
                st.session_state.db_crop_preview = None
            else:
                 st.session_state.temp_msg = {"type": "error", "text": "请填写车牌号和车主姓名"}

        col_form1, col_form2 = st.columns(2)
        with col_form1:
            st.text_input("车牌号码 (阿拉伯文)", placeholder="例如: دبي ١٢٣٤٥", key="form_plate")
            st.text_input("中文/译文 (选填)", placeholder="例如: 迪拜 12345", key="form_trans")
        with col_form2:
            st.text_input("车主姓名", placeholder="例如: 张经理", key="form_owner")
            st.write("") 
            st.write("") 
            st.button("添加车辆", type="primary", on_click=add_vehicle_callback)
        
        if 'temp_msg' in st.session_state:
            msg = st.session_state.temp_msg
            if msg['type'] == 'success':
                st.success(msg['text'])
            else:
                st.warning(msg['text'])
            del st.session_state.temp_msg

    st.divider()

    # 2. VIEW & MANAGE SECTION (Updated)
    
    # Header & Metrics
    total_count = storage.get_total_count()
    m1, m2, m3 = st.columns([1, 2, 1])
    with m1:
        st.metric("总车辆数", total_count)
    with m2:
        search_query = st.text_input("🔍 搜索车辆", placeholder="输入车牌号或车主姓名...")
    with m3:
        view_mode = st.radio("视图模式", ["列表", "表格"], horizontal=True, label_visibility="collapsed")

    # Pagination Logic
    ITEMS_PER_PAGE = 10
    
    if search_query:
        # If searching, we fetch all matches (assuming reasonable result set) 
        # or implement search pagination if needed. For simplicity, we list matches.
        st.caption(f"搜索结果: '{search_query}'")
        plates = storage.get_authorized_plates(limit=100, offset=0, search_query=search_query)
        total_pages = 1
        current_page = 1
    else:
        # Standard Pagination
        total_pages = math.ceil(total_count / ITEMS_PER_PAGE) if total_count > 0 else 1
        current_page = st.number_input("页码", min_value=1, max_value=total_pages, value=1)
        offset = (current_page - 1) * ITEMS_PER_PAGE
        plates = storage.get_authorized_plates(limit=ITEMS_PER_PAGE, offset=offset)

    if not plates:
        st.info("暂无数据")
    else:
        # Table View (Compact)
        if view_mode == "表格":
            # Prepare data for dataframe
            data_for_df = []
            for p in plates:
                data_for_df.append({
                    "车牌号码": p['plate_number'],
                    "译文/中文": p['plate_translation'],
                    "车主姓名": p['owner_name'],
                    "登记时间": time.strftime('%Y-%m-%d %H:%M', time.localtime(p['added_at']/1000)),
                    "ID": p['id']
                })
            
            st.dataframe(
                data_for_df, 
                use_container_width=True,
                hide_index=True,
                column_config={
                    "ID": st.column_config.TextColumn("System ID", width="small")
                }
            )
            st.caption("💡 提示: 表格视图仅供浏览。如需删除，请切换至“列表”视图。")

        # List View (Card Style with Actions)
        else:
            for p in plates:
                with st.container():
                    c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
                    with c1:
                        st.markdown(f"**{p['plate_number']}**")
                        if p['plate_translation']:
                            st.caption(p['plate_translation'])
                    with c2:
                        st.write(p['owner_name'])
                    with c3:
                        st.caption(time.strftime('%Y-%m-%d', time.localtime(p['added_at']/1000)))
                    with c4:
                        if st.button("删除", key=f"del_{p['id']}"):
                            storage.remove_authorized_plate(p['id'])
                            st.rerun()
                    st.markdown("---")
            
            if not search_query and total_pages > 1:
                st.caption(f"显示第 {current_page} 页，共 {total_pages} 页")
