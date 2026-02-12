import streamlit as st
import edge_tts
import asyncio
from github import Github
import json
import base64
import time
from datetime import datetime
import os
import pandas as pd

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="Quản Trị Radio Mặt Trận", page_icon="☭", layout="wide")

# --- CẤU HÌNH KHO DỮ LIỆU (REPOSITORY) ---
# Thay đổi tên kho dữ liệu mới tại đây
REPO_NAME = "snnmt/radiomattran" 

# CẤU HÌNH MAPPING: Chuyên mục -> Thư mục trên GitHub
# (Dựa theo ảnh chụp màn hình GitHub của anh)
CATEGORY_MAP = {
    "Tin Hoạt Động": "tinhoatdong/",
    "Đại Đoàn Kết": "daidoanket/",
    "Nông Thôn Mới": "nongthonmoi/",
    "An Sinh Xã Hội": "ansinhxahoi/",
    "Bầu Cử": "baucu/",
    "Tin Khác": "tinkhac/"
}

FOLDER_AUDIO = "amthanh/"
FOLDER_IMAGE = "hinhanh/" # Ảnh sẽ gom chung vào đây cho gọn
FILE_JSON_DATA = "danh_sach_tai_lieu.json"

# --- KIỂM TRA MẬT KHẨU ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

def check_password():
    try:
        if st.session_state.password_input == st.secrets["APP_PASSWORD"]:
            st.session_state.authenticated = True
        else:
            st.error("❌ Sai mật khẩu!")
    except:
        st.error("⚠️ Chưa cấu hình APP_PASSWORD trong Settings.")

if not st.session_state.authenticated:
    st.markdown("<h2 style='text-align: center;'>☭ Đăng Nhập Hệ Thống Mặt Trận</h2>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        st.text_input("Mật khẩu quản trị:", type="password", key="password_input", on_change=check_password)
    st.stop()

# =================================================================================
# KHI ĐÃ ĐĂNG NHẬP
# =================================================================================

st.title("☭ Hệ Thống Quản Trị Radio Mặt Trận")
st.caption(f"Đang kết nối tới kho dữ liệu: {REPO_NAME}")

# --- KẾT NỐI GITHUB ---
try:
    GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
except:
    st.error("⚠️ Thiếu GITHUB_TOKEN.")
    st.stop()

# --- CÁC HÀM HỖ TRỢ ---

def get_github_repo():
    g = Github(GITHUB_TOKEN)
    return g.get_repo(REPO_NAME)

async def generate_audio(text, filename, voice, rate):
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await communicate.save(filename)

def upload_file_to_github(file_obj, folder_path, repo, custom_name=None):
    if custom_name:
        new_filename = custom_name
    else:
        file_ext = file_obj.name.split(".")[-1]
        new_filename = f"up_{int(time.time())}.{file_ext}"
        
    git_path = f"{folder_path}{new_filename}"
    
    # GitHub tự động tạo folder nếu chưa có
    repo.create_file(git_path, f"Up: {new_filename}", file_obj.getvalue())
    return f"https://raw.githubusercontent.com/{REPO_NAME}/main/{git_path}"

def get_data_from_github():
    repo = get_github_repo()
    try:
        contents = repo.get_contents(FILE_JSON_DATA)
        json_str = base64.b64decode(contents.content).decode("utf-8")
        return json.loads(json_str), contents.sha
    except:
        return [], None

def push_json_to_github(data_list, sha, message):
    repo = get_github_repo()
    try:
        contents = repo.get_contents(FILE_JSON_DATA)
        updated_json = json.dumps(data_list, ensure_ascii=False, indent=4)
        repo.update_file(contents.path, message, updated_json, contents.sha)
    except:
        # Trường hợp file chưa tồn tại (lần đầu tiên)
        updated_json = json.dumps(data_list, ensure_ascii=False, indent=4)
        repo.create_file(FILE_JSON_DATA, message, updated_json)

# --- CHIA GIAO DIỆN THÀNH 2 TAB ---
tab1, tab2 = st.tabs(["➕ ĐĂNG BẢN TIN MỚI", "🛠️ QUẢN LÝ & CHỈNH SỬA"])

# =================================================================================
# TAB 1: ĐĂNG BÀI MỚI
# =================================================================================
with tab1:
    st.subheader("Soạn Thảo Bản Tin Mặt Trận")
    
    # 1. THÔNG TIN CƠ BẢN
    c1, c2 = st.columns(2)
    with c1:
        title = st.text_input("Tiêu đề bản tin")
        # Sử dụng danh sách chuyên mục mới
        category = st.selectbox("Chuyên mục", list(CATEGORY_MAP.keys()))
    with c2:
        description = st.text_input("Mô tả ngắn / Trích yếu")
        pdf_file = st.file_uploader("Văn bản đính kèm (PDF)", type=["pdf"])
        if pdf_file:
            st.info(f"File này sẽ được lưu vào thư mục: /{CATEGORY_MAP[category]}")

    st.markdown("---")
    
    # 2. CHỌN NGUỒN ÂM THANH
    st.write("🎙️ **Cấu hình Âm thanh & Hình ảnh**")
    
    audio_source_options = ["🎙️ Tạo từ văn bản (AI)", "📁 Tải file có sẵn từ máy"]
    audio_source = st.radio("Chọn nguồn âm thanh:", audio_source_options, horizontal=True)
    
    content_text = ""
    uploaded_audio = None
    voice_code = "vi-VN-NamMinhNeural"
    speed_rate = "+0%"
    
    col_audio, col_image = st.columns([2, 1])
    
    with col_audio:
        if audio_source == audio_source_options[0]: # AI
            c_voice, c_speed = st.columns(2)
            with c_voice:
                voice_opts = {"Nam (Miền Nam)": "vi-VN-NamMinhNeural", "Nữ (Miền Bắc)": "vi-VN-HoaiMyNeural"}
                voice_label = st.selectbox("Giọng đọc:", list(voice_opts.keys()))
                voice_code = voice_opts[voice_label]
            with c_speed:
                speed_opts = {
                    "Bình thường (+0%)": "+0%",
                    "Hơi nhanh - Tin tức (+10%)": "+10%", 
                    "Nhanh - Khẩn cấp (+20%)": "+20%",
                    "Chậm - Kể chuyện (-10%)": "-10%"
                }
                speed_label = st.selectbox("Tốc độ đọc:", list(speed_opts.keys()), index=0)
                speed_rate = speed_opts[speed_label]
            
            content_text = st.text_area("Nội dung bản tin (AI sẽ đọc):", height=200, placeholder="Dán văn bản tuyên truyền vào đây...")
        
        else: # Upload
            st.info("📂 Upload file âm thanh (MP3/WAV) đã thu âm sẵn")
            uploaded_audio = st.file_uploader("Chọn file âm thanh:", type=["mp3", "wav", "m4a"])

    with col_image:
        image_file = st.file_uploader("Ảnh bìa (JPG/PNG)", type=["jpg", "png", "jpeg"])

    # --- NÚT BẤM ---
    st.markdown("---")
    col_btn1, col_btn2 = st.columns(2)
    
    with col_btn1:
        if st.button("🎧 NGHE THỬ / KIỂM TRA"):
            if audio_source == audio_source_options[0]: 
                if not content_text:
                    st.warning("⚠️ Chưa có nội dung!")
                else:
                    st.info(f"🎙️ Đang tạo bản nghe thử ({voice_label})...")
                    preview_filename = "preview_temp.mp3"
                    asyncio.run(generate_audio(content_text, preview_filename, voice_code, speed_rate))
                    with open(preview_filename, "rb") as f:
                        st.audio(f.read(), format="audio/mp3")
                    os.remove(preview_filename)
            else:
                if not uploaded_audio:
                    st.warning("⚠️ Chưa chọn file!")
                else:
                    st.audio(uploaded_audio)

    with col_btn2:
        if st.button("🚀 PHÁT SÓNG NGAY", type="primary"):
            valid = True
            if not title:
                st.warning("⚠️ Thiếu tiêu đề!")
                valid = False
            if audio_source == audio_source_options[0] and not content_text:
                st.warning("⚠️ Thiếu nội dung!")
                valid = False
            if audio_source == audio_source_options[1] and not uploaded_audio:
                st.warning("⚠️ Chưa upload file!")
                valid = False

            if valid:
                status = st.status("Đang xử lý phát sóng...", expanded=True)
                repo = get_github_repo()
                
                # 1. Upload Ảnh & PDF (Vào đúng thư mục chuyên mục)
                status.write("Upload file đính kèm...")
                
                # Xác định thư mục PDF dựa trên chuyên mục
                target_pdf_folder = CATEGORY_MAP.get(category, "tinkhac/")
                final_pdf = upload_file_to_github(pdf_file, target_pdf_folder, repo) if pdf_file else ""
                
                # Ảnh vẫn vào folder chung hinhanh
                final_img = upload_file_to_github(image_file, FOLDER_IMAGE, repo) if image_file else f"https://raw.githubusercontent.com/{REPO_NAME}/main/hinhanh/logo_mac_dinh.png"
                
                # 2. Xử lý Âm thanh
                status.write("Xử lý âm thanh...")
                timestamp = int(time.time())
                
                if audio_source == audio_source_options[0]: 
                    fname_mp3 = f"radio_{timestamp}.mp3"
                    asyncio.run(generate_audio(content_text, fname_mp3, voice_code, speed_rate))
                    with open(fname_mp3, "rb") as f:
                        audio_content = f.read()
                    os.remove(fname_mp3)
                else:
                    audio_content = uploaded_audio.getvalue()
                    ext = uploaded_audio.name.split(".")[-1]
                    fname_mp3 = f"radio_{timestamp}.{ext}"

                repo.create_file(f"{FOLDER_AUDIO}{fname_mp3}", f"Audio: {title}", audio_content)
                final_audio = f"https://raw.githubusercontent.com/{REPO_NAME}/main/{FOLDER_AUDIO}{fname_mp3}"

                # 3. Cập nhật JSON
                status.write("Cập nhật cơ sở dữ liệu...")
                data, sha = get_data_from_github()
                
                if data:
                    ids = [x.get('id', 0) for x in data] 
                    new_id = max(ids) + 1 if ids else 1
                else:
                    new_id = 1
                
                new_item = {
                    "id": new_id, "title": title, "category": category, "description": description,
                    "pdf_url": final_pdf, "audio_url": final_audio, "image_url": final_img,
                    "last_updated": datetime.now().strftime("%d/%m/%Y")
                }
                data.insert(0, new_item)
                push_json_to_github(data, sha, f"Add post: {title}")
                
                status.update(label="✅ Thành công!", state="complete")
                st.success(f"Đã phát sóng bản tin ID: {new_id}")

# =================================================================================
# TAB 2: QUẢN LÝ
# =================================================================================
with tab2:
    st.subheader("Danh Sách Bản Tin Đang Có")
    
    if st.button("🔄 Tải danh sách mới nhất từ GitHub"):
        data, _ = get_data_from_github()
        st.session_state.db_data = data
        st.rerun()

    current_data = st.session_state.get("db_data", [])

    if not current_data:
        st.info("Chưa có dữ liệu. Vui lòng bấm nút 'Tải danh sách' ở trên.")
    else:
        safe_data = []
        for item in current_data:
            safe_data.append({
                "id": item.get("id", "N/A"),
                "title": item.get("title", "Không tiêu đề"),
                "category": item.get("category", "Chưa phân loại"),
                "last_updated": item.get("last_updated", "")
            })
        st.dataframe(pd.DataFrame(safe_data), use_container_width=True)

        st.markdown("---")
        st.subheader("🛠️ Chỉnh Sửa / Xóa")

        list_ids = [f"{item.get('id')} - {item.get('title')}" for item in current_data]
        selected_option = st.selectbox("Chọn bản tin cần xử lý:", list_ids)
        
        selected_item = None
        if selected_option:
            try:
                sel_id = int(selected_option.split(" - ")[0])
                selected_item = next((item for item in current_data if item.get("id") == sel_id), None)
            except: pass

        if selected_item:
            with st.expander("📝 CHỈNH SỬA CHI TIẾT", expanded=True):
                # 1. Text Info
                new_title = st.text_input("Tiêu đề:", value=selected_item.get("title", ""))
                new_desc = st.text_input("Mô tả:", value=selected_item.get("description", ""))
                
                # Dropdown chuyên mục mới
                cat_ops = list(CATEGORY_MAP.keys())
                curr_cat = selected_item.get("category", "Tin Khác")
                c_idx = cat_ops.index(curr_cat) if curr_cat in cat_ops else 0
                new_cat = st.selectbox("Chuyên mục:", cat_ops, index=c_idx)

                st.markdown("---")
                # 2. Files
                col_edit_img, col_edit_pdf = st.columns(2)
                with col_edit_img:
                    st.write("**Ảnh đại diện:**")
                    if selected_item.get("image_url"):
                        st.image(selected_item["image_url"], width=150)
                    new_image = st.file_uploader("Thay ảnh mới:", type=["jpg", "png"])
                
                with col_edit_pdf:
                    st.write("**Tài liệu văn bản:**")
                    if selected_item.get("pdf_url"):
                        st.markdown(f"[Xem PDF hiện tại]({selected_item['pdf_url']})")
                    new_pdf = st.file_uploader("Thay PDF mới:", type=["pdf"])

                st.markdown("---")
                # 3. Audio
                st.write("🔊 **Âm thanh phát sóng**")
                if selected_item.get("audio_url"):
                    st.audio(selected_item["audio_url"])
                
                need_replace_audio = st.checkbox("Thay thế file âm thanh mới?")
                
                edit_audio_source = "AI"
                edit_content_text = ""
                edit_uploaded_audio = None
                edit_voice_code = "vi-VN-NamMinhNeural"
                edit_speed_rate = "+0%"

                if need_replace_audio:
                    edit_audio_opts = ["🎙️ Tạo lại bằng AI", "📁 Upload file mới"]
                    edit_audio_source = st.radio("Nguồn âm thanh mới:", edit_audio_opts, horizontal=True)
                    
                    if edit_audio_source == edit_audio_opts[0]: # AI
                        ec1, ec2 = st.columns(2)
                        with ec1:
                            e_voice_label = st.selectbox("Giọng đọc mới:", list(voice_opts.keys()), key="edit_voice")
                            edit_voice_code = voice_opts[e_voice_label]
                        with ec2:
                            e_speed_label = st.selectbox("Tốc độ mới:", list(speed_opts.keys()), key="edit_speed")
                            edit_speed_rate = speed_opts[e_speed_label]
                        
                        edit_content_text = st.text_area("Nội dung mới để đọc:", height=150)
                    else: # Upload
                        edit_uploaded_audio = st.file_uploader("Chọn file âm thanh thay thế:", type=["mp3", "wav", "m4a"], key="edit_upload")

                st.markdown("---")
                if st.button("💾 LƯU TẤT CẢ THAY ĐỔI", type="primary"):
                    if need_replace_audio:
                        if edit_audio_source == "🎙️ Tạo lại bằng AI" and not edit_content_text:
                            st.error("⚠️ Thiếu nội dung AI!")
                            st.stop()
                        if edit_audio_source == "📁 Upload file mới" and not edit_uploaded_audio:
                            st.error("⚠️ Thiếu file upload!")
                            st.stop()

                    status = st.status("Đang cập nhật...", expanded=True)
                    repo = get_github_repo()
                    
                    if new_image:
                        selected_item["image_url"] = upload_file_to_github(new_image, FOLDER_IMAGE, repo)
                    if new_pdf:
                        # Lưu PDF vào đúng folder của chuyên mục mới chọn
                        target_folder = CATEGORY_MAP.get(new_cat, "tinkhac/")
                        selected_item["pdf_url"] = upload_file_to_github(new_pdf, target_folder, repo)
                    
                    if need_replace_audio:
                        status.write("Đang xử lý âm thanh mới...")
                        timestamp = int(time.time())
                        fname_mp3 = f"radio_{timestamp}.mp3"
                        
                        if edit_audio_source.startswith("🎙️"): # AI
                            asyncio.run(generate_audio(edit_content_text, fname_mp3, edit_voice_code, edit_speed_rate))
                            with open(fname_mp3, "rb") as f:
                                content = f.read()
                            os.remove(fname_mp3)
                        else: # Upload
                            content = edit_uploaded_audio.getvalue()
                            ext = edit_uploaded_audio.name.split(".")[-1]
                            fname_mp3 = f"radio_{timestamp}.{ext}"
                            
                        repo.create_file(f"{FOLDER_AUDIO}{fname_mp3}", f"Update Audio ID {selected_item['id']}", content)
                        selected_item["audio_url"] = f"https://raw.githubusercontent.com/{REPO_NAME}/main/{FOLDER_AUDIO}{fname_mp3}"

                    selected_item["title"] = new_title
                    selected_item["description"] = new_desc
                    selected_item["category"] = new_cat
                    selected_item["last_updated"] = datetime.now().strftime("%d/%m/%Y")

                    full_data, sha = get_data_from_github()
                    for idx, item in enumerate(full_data):
                        if item.get("id") == selected_item["id"]:
                            full_data[idx] = selected_item
                            break
                    
                    push_json_to_github(full_data, sha, f"Edit post ID {selected_item['id']}")
                    st.session_state.db_data = full_data
                    
                    status.update(label="✅ Đã cập nhật thành công!", state="complete")
                    st.success("Dữ liệu đã được lưu!")
                    time.sleep(1)
                    st.rerun()

            st.markdown("---")
            col_del1, col_del2 = st.columns([3, 1])
            with col_del2:
                if st.button("🗑️ XÓA BẢN TIN NÀY", type="primary"):
                    with st.spinner("Đang xóa..."):
                        full_data, sha = get_data_from_github()
                        filtered_data = [x for x in full_data if x.get("id") != selected_item.get("id")]
                        push_json_to_github(filtered_data, sha, f"Delete ID {selected_item.get('id')}")
                        st.session_state.db_data = filtered_data
                        st.success("Đã xóa!")
                        time.sleep(1)
                        st.rerun()
