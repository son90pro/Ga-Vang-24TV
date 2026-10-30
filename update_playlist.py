import json
import urllib.request
from datetime import datetime

# API chính lấy danh sách match_id đang diễn ra
LIVE_API_URL = "https://seo.alpro-api-service.com/v1/bb-live-data"
OUTPUT_M3U = "playlist.m3u"

def fetch_json(url):
    try:
        req = urllib.request.Request(
            url, 
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as e:
        return None

def format_time(timestamp):
    """Chuyển đổi timestamp sang định dạng Giờ Ngày/Tháng (Ví dụ: 19:30 30/10)"""
    try:
        if timestamp:
            dt = datetime.fromtimestamp(int(timestamp))
            return dt.strftime("%H:%M %d/%m")
    except:
        pass
    return "16:00 30/10"

def generate_m3u():
    data = fetch_json(LIVE_API_URL)
    if not data or "bb_live_data" not in data:
        print("Không thể lấy dữ liệu từ API chính.")
        return

    matches = data.get("bb_live_data", [])
    m3u_content = "#EXTM3U\n\n"
    
    count = 0
    for match in matches:
        match_id = match.get("match_id", "")
        status = match.get("status_name", "NS")
        
        # Bỏ qua các trận đã kết thúc hoàn toàn (FT) để danh sách gọn gàng
        if status == "FT":
            continue
            
        # Mặc định fallback nếu chưa quét được chi tiết
        home_team = match.get("home_name", "Đội Nhà")
        away_team = match.get("away_name", "Đội Khách")
        home_logo = match.get("home_logo", "")
        commentator = match.get("caster", "Cris")
        time_str = format_time(match.get("start_time", match.get("time")))
        channel_name = "Gà Vàng 24h TV"
        sport_icon = "⚽"
        
        # Thử gọi API chi tiết trận đấu (nếu hệ thống của cakhia có endpoint match detail tương ứng)
        # Hoặc trích xuất thông tin trực tiếp nếu API trả về đầy đủ
        detail_url = f"https://seo.alpro-api-service.com/v1/match/{match_id}"
        detail_data = fetch_json(detail_url)
        
        if detail_data and isinstance(detail_data, dict):
            # Cập nhật thông tin thật từ API chi tiết trận đấu nếu có
            home_team = detail_data.get("home_team_name", detail_data.get("home_name", home_team))
            away_team = detail_data.get("away_team_name", detail_data.get("away_name", away_team))
            home_logo = detail_data.get("home_team_logo", detail_data.get("home_logo", home_logo))
            commentator = detail_data.get("caster_name", detail_data.get("commentator", commentator))
            
            raw_time = detail_data.get("start_time", detail_data.get("match_time"))
            if raw_time:
                time_str = format_time(raw_time)
                
            sport_type = detail_data.get("sport_type", "football")
            if "basket" in sport_type.lower():
                sport_icon = "🏀"

        # Biểu tượng trạng thái Live (🟢 nếu đang đá, để trống nếu sắp diễn ra)
        status_icon = "🟢" if status not in ["NS", "TBD"] else ""
        
        # Định dạng tiêu đề hiển thị chuẩn khớp mẫu yêu cầu
        blv_str = f" ({commentator})" if commentator else ""
        title_parts = [
            status_icon,
            time_str,
            sport_icon,
            f"{home_team} vs {away_team}{blv_str}"
        ]
        title = " ".join([p for p in title_parts if p])
        
        # Tạo 2 luồng phát [hls] và [flv] cho mỗi trận đấu
        streams = [
            {"type": "hls", "url": f"https://playback.livetl002.com/live/{match_id}.m3u8"},
            {"type": "flv", "url": f"https://playback.livetl002.com/live/{match_id}.flv"}
        ]
        
        for stream in streams:
            stype = stream["type"]
            surl = stream["url"]
            stream_title = f"{title} [{stype}]"
            
            m3u_item = f'#EXTINF:-1 tvg-logo="{home_logo}" group-title="{channel_name}" , {stream_title}\n{surl}\n\n'
            m3u_content += m3u_item
            count += 1

    # Ghi file playlist.m3u
    with open(OUTPUT_M3U, "w", encoding="utf-8") as f:
        f.write(m3u_content.strip() + "\n")
    print(f"Đã cập nhật thành công file {OUTPUT_M3U} với {count} luồng phát từ các trận đấu!")

if __name__ == "__main__":
    generate_m3u()
    
