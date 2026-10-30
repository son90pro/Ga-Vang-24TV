import json
import urllib.request
from datetime import datetime

API_URL = "https://seo.alpro-api-service.com/v1/bb-live-data"
OUTPUT_M3U = "playlist.m3u"

def fetch_data():
    req = urllib.request.Request(
        API_URL, 
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    )
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode("utf-8"))

def format_time(timestamp_or_str):
    """Chuyển đổi hoặc định dạng thời gian hiển thị Giờ Ngày Tháng"""
    try:
        if isinstance(timestamp_or_str, (int, float)):
            dt = datetime.fromtimestamp(timestamp_or_str)
            return dt.strftime("%H:%M %d/%m")
        elif isinstance(timestamp_or_str, str) and timestamp_or_str.isdigit():
            dt = datetime.fromtimestamp(int(timestamp_or_str))
            return dt.strftime("%H:%M %d/%m")
        # Trả về chuỗi gốc nếu đã được format sẵn từ API
        return str(timestamp_or_str) if timestamp_or_str else "16:00 30/10"
    except:
        return "16:00 30/10"

def generate_m3u():
    try:
        data = fetch_data()
        matches = data.get("bb_live_data", [])
    except Exception as e:
        print(f"Lỗi khi gọi API: {e}")
        matches = []

    # Khởi tạo file M3U chuẩn
    m3u_content = "#EXTM3U\n\n"
    
    for match in matches:
        match_id = match.get("match_id", "")
        status = match.get("status_name", "NS")
        
        # Bỏ qua các trận đã kết thúc hoàn toàn (FT) nếu muốn danh sách gọn gàng
        if status == "FT":
            continue
            
        # Trích xuất thông tin đội bóng và logo
        home_team = match.get("home_name", match.get("home_team", "Đội Nhà"))
        away_team = match.get("away_name", match.get("away_team", "Đội Khách"))
        home_logo = match.get("home_logo", match.get("home_image", ""))
        
        # Trích xuất tên Bình Luận Viên (BLV)
        commentator = match.get("caster", match.get("commentator", match.get("blv", "Cris")))
        blv_str = f" ({commentator})" if commentator else ""
        
        # Nhà đài / Phân nhóm kênh
        channel_name = match.get("channel_name", match.get("group_name", "Gà Vàng 24h TV"))
        
        # Thời gian trận đấu
        raw_time = match.get("match_time", match.get("start_time", "16:00 30/10"))
        time_str = format_time(raw_time)
        
        # Biểu tượng môn thể thao và trạng thái Live
        sport_type = match.get("sport_type", match.get("sport", "football"))
        sport_icon = "🏀" if "basket" in sport_type.lower() else "⚽"
        status_icon = "🟢" if status not in ["NS", "TBD"] else ""
        
        # Xử lý các luồng phát (HLS, FLV, FHD, HD...) theo đúng mẫu chuẩn của web
        # Nếu API trả về danh sách streams riêng, duyệt qua; nếu không, tạo sẵn các định dạng hls/flv tương ứng
        streams = match.get("streams", [
            {"type": "hls", "url": f"https://playback.livetl002.com/live/{match_id}.m3u8"},
            {"type": "flv", "url": f"https://playback.livetl002.com/live/{match_id}.flv"}
        ])
        
        for stream in streams:
            stype = stream.get("type", "hls")
            surl = stream.get("url", f"https://playback.livetl002.com/live/{match_id}.{stype}")
            
            # Định dạng tiêu đề hiển thị chuẩn: [Trạng thái] [Giờ Ngày] [Icon môn] [Đội nhà] vs [Đội khách] ([BLV]) [Luồng]
            title_parts = [
                status_icon,
                time_str,
                sport_icon,
                f"{home_team} vs {away_team}{blv_str}",
                f"[{stype}]"
            ]
            title = " ".join([p for p in title_parts if p])
            
            # Ghi dòng EXTINF và Link stream
            m3u_item = f'#EXTINF:-1 tvg-logo="{home_logo}" group-title="{channel_name}" , {title}\n{surl}\n\n'
            m3u_content += m3u_item

    # Lưu file playlist.m3u
    with open(OUTPUT_M3U, "w", encoding="utf-8") as f:
        f.write(m3u_content.strip() + "\n")
    print(f"Đã cập nhật file {OUTPUT_M3U} thành công theo đúng định dạng yêu cầu!")

if __name__ == "__main__":
    generate_m3u()
    
