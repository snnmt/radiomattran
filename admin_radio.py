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
import requests 
import threading 

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="Quản Trị Radio Mặt Trận", page_icon="☭", layout="wide")

if "render_woken" not in st.session_state:
    def ping_render():
        try:
            api_url = "https://radiomt.onrender.com/"
            requests.get(api_url, timeout=3)
        except:
            pass 
    threading.Thread(target=ping_render, daemon=True).start()
    st.session_state.render_woken = True

# --- CẤU HÌNH KHO DỮ LIỆU (REPOSITORY) ---
REPO_NAME = "snnmt/radiomattran" 

CATEGORY_MAP = {
    "Tin Hoạt Động": "tinhoatdong/",
    "Đại Đoàn Kết": "daidoanket/",
    "Nông Thôn Mới": "nongthonmoi/",
    "An Sinh Xã Hội": "ansinhxahoi/",
    "Bầu Cử": "baucu/",
    "Tin Khác": "tinkhac/"
}

FOLDER_AUDIO = "amthanh/"
FOLDER_IMAGE = "hinhanh/" 
FILE_JSON_DATA = "danh_sach_tai_lieu.json"

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

st.title("☭ Hệ Thống Quản Trị Radio Mặt Trận")
st.caption(f"Đang kết nối tới kho dữ liệu: {REPO_NAME}")

try:
    GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
except:
    st.error("⚠️ Thiếu GITHUB_TOKEN.")
    st.stop()

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
        updated_json = json.dumps(data_list, ensure_ascii=False, indent=4)
        repo.create_file(FILE_JSON_DATA, message, updated_json)

def delete_file_from_github(repo, file_url):
    if not file_url or "logo_mac_dinh" in file_url:
        return
    try:
        path = file_url.split("main/")[-1]
        contents = repo.get_contents(path)
        repo.delete_file(contents.path, f"Delete {path}", contents.sha)
    except Exception as e:
        pass 

# =====================================================================
# CHIA GIAO DIỆN THÀNH 3 TAB
# =====================================================================
tab1, tab2, tab3 = st.tabs(["➕ ĐĂNG BẢN TIN MỚI", "🛠️ QUẢN LÝ & CHỈNH SỬA", "📊 THỐNG KÊ CHI TIẾT"])

# --- TAB 1: ĐĂNG BÀI MỚI ---
with tab1:
    st.subheader("Soạn Thảo Bản Tin Mặt Trận")
    
    c1, c2 = st.columns(2)
    with c1:
        title = st.text_input("Tiêu đề bản tin")
        category = st.selectbox("Chuyên mục", list(CATEGORY_MAP.keys()))
    with c2:
        description = st.text_input("Mô tả ngắn / Trích yếu")
        pdf_file = st.file_uploader("Văn bản đính kèm (PDF)", type=["pdf"])

    st.markdown("---")
    
    st.write("🎙️ **Cấu hình Âm thanh & Hình ảnh / Video**")
    
    audio_source_options = ["🎙️ Tạo từ văn bản (AI)", "📁 Tải file có sẵn", "🚫 Không cần âm thanh (Dành cho Video)"]
    audio_source = st.radio("Chọn nguồn âm thanh:", audio_source_options, horizontal=True)
    
    content_text = ""
    uploaded_audio = None
    voice_code = "vi-VN-NamMinhNeural"
    speed_rate = "+0%"
    
    col_audio, col_image = st.columns([2, 1])
    
    with col_audio:
        if audio_source == audio_source_options[0]: 
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
            
            content_text = st.text_area("Nội dung bản tin (AI sẽ đọc):", height=200, placeholder="Dán văn bản vào đây...")
        
        elif audio_source == audio_source_options[1]:
            st.info("📂 Upload file âm thanh (MP3/WAV) đã thu âm sẵn")
            uploaded_audio = st.file_uploader("Chọn file âm thanh:", type=["mp3", "wav", "m4a"])
            
        else: 
            st.success("🔇 Đã chọn bỏ qua âm thanh. Thường dùng khi bạn đăng tải Video.")

    with col_image:
        image_file = st.file_uploader("Ảnh bìa / Video (JPG/PNG/MP4)", type=["jpg", "png", "jpeg", "mp4"])
        if image_file and image_file.name.endswith(".mp4"):
            st.info("🎥 Hệ thống sẽ nhận diện đây là Video.")

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
            elif audio_source == audio_source_options[1]:
                if not uploaded_audio:
                    st.warning("⚠️ Chưa chọn file!")
                else:
                    st.audio(uploaded_audio)
            else:
                st.warning("🔇 Bạn đã chọn không dùng âm thanh nên không thể nghe thử.")

    with col_btn2:
        if st.button("🚀 PHÁT SÓNG NGAY", type="primary"):
            valid = True
            if not title:
                st.warning("⚠️ Thiếu tiêu đề!")
                valid = False
            if audio_source == audio_source_options[0] and not content_text:
                st.warning("⚠️ Thiếu nội dung AI!")
                valid = False
            if audio_source == audio_source_options[1] and not uploaded_audio:
                st.warning("⚠️ Chưa upload file âm thanh!")
                valid = False

            if valid:
                status = st.status("Đang xử lý phát sóng...", expanded=True)
                repo = get_github_repo()
                
                status.write("Upload file đính kèm...")
                target_pdf_folder = CATEGORY_MAP.get(category, "tinkhac/")
                final_pdf = upload_file_to_github(pdf_file, target_pdf_folder, repo) if pdf_file else ""
                final_img = upload_file_to_github(image_file, FOLDER_IMAGE, repo) if image_file else f"https://raw.githubusercontent.com/{REPO_NAME}/main/hinhanh/logo_mac_dinh.png"
                
                final_audio = ""
                if audio_source != audio_source_options[2]:
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

                try:
                    api_url = "https://radiomt.onrender.com/admin/sendNotification"
                    headers = {
                        "Authorization": "Bearer RadioMatTran2026_Secret", 
                        "Content-Type": "application/json"
                    }
                    payload = {
                        "title": "📻 Bản tin Mặt Trận mới",
                        "body": title
                    }
                    
                    resp = requests.post(api_url, headers=headers, json=payload, timeout=60)
                    if resp.status_code == 200:
                        st.toast("🔔 Đã đẩy thông báo tới toàn bộ điện thoại!", icon="🚀")
                    else:
                        st.warning(f"Đã đăng bài nhưng lỗi đẩy thông báo: {resp.text}")
                except Exception as e:
                    st.error(f"Lỗi kết nối API thông báo: {e}")

# --- TAB 2: QUẢN LÝ ---
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
                new_title = st.text_input("Tiêu đề:", value=selected_item.get("title", ""))
                new_desc = st.text_input("Mô tả:", value=selected_item.get("description", ""))
                
                cat_ops = list(CATEGORY_MAP.keys())
                curr_cat = selected_item.get("category", "Tin Khác")
                c_idx = cat_ops.index(curr_cat) if curr_cat in cat_ops else 0
                new_cat = st.selectbox("Chuyên mục:", cat_ops, index=c_idx)

                st.markdown("---")
                col_edit_img, col_edit_pdf = st.columns(2)
                with col_edit_img:
                    st.write("**Ảnh đại diện / Video:**")
                    if selected_item.get("image_url"):
                        media_url = selected_item["image_url"]
                        if media_url.lower().endswith(".mp4"):
                            st.video(media_url)
                        else:
                            st.image(media_url, width=150)
                            
                    new_image = st.file_uploader("Thay Ảnh/Video mới:", type=["jpg", "png", "jpeg", "mp4"])
                
                with col_edit_pdf:
                    st.write("**Tài liệu văn bản:**")
                    if selected_item.get("pdf_url"):
                        st.markdown(f"[Xem PDF hiện tại]({selected_item['pdf_url']})")
                    new_pdf = st.file_uploader("Thay PDF mới:", type=["pdf"])

                st.markdown("---")
                st.write("🔊 **Âm thanh phát sóng**")
                if selected_item.get("audio_url"):
                    st.audio(selected_item["audio_url"])
                else:
                    st.info("🔇 Bản tin này hiện không có âm thanh.")
                
                need_replace_audio = st.checkbox("Thay đổi / Xóa âm thanh?")
                
                edit_audio_source = "AI"
                edit_content_text = ""
                edit_uploaded_audio = None
                edit_voice_code = "vi-VN-NamMinhNeural"
                edit_speed_rate = "+0%"

                if need_replace_audio:
                    edit_audio_opts = ["🎙️ Tạo lại bằng AI", "📁 Upload file mới", "🗑️ Xóa âm thanh (Dành cho Video)"]
                    edit_audio_source = st.radio("Tùy chọn âm thanh:", edit_audio_opts, horizontal=True)
                    
                    if edit_audio_source == edit_audio_opts[0]: 
                        ec1, ec2 = st.columns(2)
                        with ec1:
                            e_voice_label = st.selectbox("Giọng đọc mới:", list(voice_opts.keys()), key="edit_voice")
                            edit_voice_code = voice_opts[e_voice_label]
                        with ec2:
                            e_speed_label = st.selectbox("Tốc độ mới:", list(speed_opts.keys()), key="edit_speed")
                            edit_speed_rate = speed_opts[e_speed_label]
                        
                        edit_content_text = st.text_area("Nội dung mới để đọc:", height=150)
                    elif edit_audio_source == edit_audio_opts[1]: 
                        edit_uploaded_audio = st.file_uploader("Chọn file âm thanh thay thế:", type=["mp3", "wav", "m4a"], key="edit_upload")
                    else:
                        st.warning("⚠️ Nếu lưu, file âm thanh cũ sẽ bị gỡ bỏ khỏi bản tin này.")

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
                        target_folder = CATEGORY_MAP.get(new_cat, "tinkhac/")
                        selected_item["pdf_url"] = upload_file_to_github(new_pdf, target_folder, repo)
                    
                    if need_replace_audio:
                        delete_file_from_github(repo, selected_item.get("audio_url"))
                        
                        if edit_audio_source == "🗑️ Xóa âm thanh (Dành cho Video)":
                            selected_item["audio_url"] = ""
                        else:
                            status.write("Đang xử lý âm thanh mới...")
                            timestamp = int(time.time())
                            fname_mp3 = f"radio_{timestamp}.mp3"
                            
                            if edit_audio_source.startswith("🎙️"): 
                                asyncio.run(generate_audio(edit_content_text, fname_mp3, edit_voice_code, edit_speed_rate))
                                with open(fname_mp3, "rb") as f:
                                    content = f.read()
                                os.remove(fname_mp3)
                            else: 
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
                    with st.spinner("Đang xóa bản tin và dọn dẹp file..."):
                        repo = get_github_repo()
                        
                        delete_file_from_github(repo, selected_item.get("audio_url"))
                        delete_file_from_github(repo, selected_item.get("image_url"))
                        delete_file_from_github(repo, selected_item.get("pdf_url"))

                        full_data, sha = get_data_from_github()
                        filtered_data = [x for x in full_data if x.get("id") != selected_item.get("id")]
                        push_json_to_github(filtered_data, sha, f"Delete ID {selected_item.get('id')}")
                        
                        st.session_state.db_data = filtered_data
                        st.success("Đã xóa vĩnh viễn!")
                        time.sleep(1)
                        st.rerun()

# =================================================================================
# TAB 3: THỐNG KÊ CHI TIẾT
# =================================================================================
with tab3:
    st.subheader("Báo Cáo Tương Tác & Lượt Xem (Đã lọc IP trùng)")
    
    if st.button("🔄 Cập nhật số liệu"):
        with st.spinner("Đang tải và xử lý dữ liệu từ máy chủ..."):
            try:
                # Gọi API Render để lấy data
                api_url = "https://radiomt.onrender.com/admin/stats"
                headers = {"Authorization": "Bearer RadioMatTran2026_Secret"}
                resp = requests.get(api_url, headers=headers, timeout=15)
                
                if resp.status_code == 200:
                    raw_data = resp.json()
                    valid_data = [item for item in raw_data if item.get('postTitle') and item.get('postTitle') != "Không rõ"]

                    if not valid_data:
                        st.info("Chưa có lượt xem hợp lệ nào được ghi nhận.")
                    else:
                        df = pd.DataFrame(valid_data)
                        
                        # --- BƯỚC 1: XỬ LÝ DỮ LIỆU (TÁCH HÀNH ĐỘNG & TÊN BÀI) ---
                        def parse_title(raw_title):
                            raw_str = str(raw_title)
                            if raw_str.startswith("[Audio] "):
                                return "Nghe Radio", raw_str.replace("[Audio] ", "")
                            elif raw_str.startswith("[PDF] "):
                                return "Đọc PDF", raw_str.replace("[PDF] ", "")
                            elif raw_str.startswith("[Media] "):
                                return "Xem Hình/Video", raw_str.replace("[Media] ", "")
                            elif raw_str == "Xem Media đính kèm":
                                return "Xem Hình/Video", "Media (Chưa rõ bài)"
                            else:
                                return "Tương tác khác", raw_str

                        # Tạo 2 cột mới từ dữ liệu thô
                        df[['Loại tương tác', 'Tiêu đề bài viết']] = df['postTitle'].apply(lambda x: pd.Series(parse_title(x)))
                        
                        # --- BƯỚC 2: LỌC TRÙNG IP (QUAN TRỌNG NHẤT) ---
                        # Mỗi IP chỉ được tính 1 lần cho 1 Hành động trên 1 Bài viết
                        df_unique = df.drop_duplicates(subset=['ipAddress', 'Tiêu đề bài viết', 'Loại tương tác'])
                        
                        # --- HIỂN THỊ 1. TỔNG QUAN ---
                        st.markdown("### 1. Tổng quan (Chỉ tính Unique IP)")
                        c1, c2, c3 = st.columns(3)
                        c1.metric("Tổng lượt xem hợp lệ", f"{len(df_unique)} lượt")
                        
                        # Đếm số IP độc lập tổng thể (không tính trùng lặp qua các bài)
                        unique_ips = df['ipAddress'].nunique()
                        c2.metric("Số thiết bị thực tế", f"{unique_ips} máy")
                        
                        try:
                            hot_post = df_unique['Tiêu đề bài viết'].mode()[0]
                        except:
                            hot_post = "Chưa có"
                        c3.metric("Bản tin Hot nhất", hot_post)
                        
                        st.markdown("---")
                        
                        # --- HIỂN THỊ 2. BẢNG XẾP HẠNG CHI TIẾT ---
                        st.markdown("### 2. Chi tiết lượt xem theo từng bản tin")
                        st.caption("Bảng tự động phân loại số người đã Nghe Audio, Đọc PDF, Xem Ảnh của từng bài. Mỗi người (IP) chỉ tính 1 lần/bài.")
                        
                        # Tạo bảng chéo Pivot Table
                        pivot_df = df_unique.pivot_table(
                            index='Tiêu đề bài viết', 
                            columns='Loại tương tác', 
                            values='ipAddress', 
                            aggfunc='count', 
                            fill_value=0
                        )
                        
                        # Thêm cột tính Tổng số lượt cho bài đó
                        pivot_df['Tổng Lượt (Unique IP)'] = pivot_df.sum(axis=1)
                        pivot_df = pivot_df.sort_values(by='Tổng Lượt (Unique IP)', ascending=False).reset_index()
                        
                        st.dataframe(pivot_df, use_container_width=True)
                        
                        st.markdown("---")
                        
                        # --- HIỂN THỊ 3. THỐNG KÊ THIẾT BỊ ---
                        c_os, c_device = st.columns(2)
                        # Để thống kê thiết bị chuẩn, ta lọc IP trên toàn bộ dữ liệu (Mỗi IP đại diện 1 máy)
                        df_device = df.drop_duplicates(subset=['ipAddress'])
                        
                        with c_os:
                            st.markdown("### Phiên bản Android")
                            st.bar_chart(df_device['osVersion'].value_counts())
                        with c_device:
                            st.markdown("### Dòng máy (Model)")
                            st.dataframe(df_device['deviceModel'].value_counts(), use_container_width=True)

                        # --- HIỂN THỊ 4. DỮ LIỆU THÔ ---
                        st.markdown("---")
                        with st.expander("Bảng dữ liệu thô (Lịch sử truy cập chi tiết)"):
                            st.dataframe(df[['timeStr', 'ipAddress', 'Loại tương tác', 'Tiêu đề bài viết', 'deviceModel', 'osVersion']], use_container_width=True)
                            
                else:
                    st.error(f"Lỗi tải dữ liệu: {resp.text}")
            except Exception as e:
                st.error(f"Không thể kết nối máy chủ thống kê. Vui lòng thử lại sau: {e}")
