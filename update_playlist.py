import json
import urllib.request
from datetime import datetime

# Các API endpoint đã được phát hiện từ Network tab của cakhia.gold
LIVE_DATA_URL = "https://seo.alpro-api-service.com/v1/bb-live-data"
MATCH_LIST_URL = "https://seo.alpro-api-service.com/v1/bb-match-list" # Hoặc endpoint danh sách tổng hợp
OUTPUT_M3U = "playlist.m3u"

def fetch_json(url):
    try:
        req = urllib.request.Request(
            url, 
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))
    except:
        return None

def format_time(timestamp):
    """Chuyển đổi timestamp sang định dạng Giờ Ngày/Tháng"""
    try:
        if timestamp:
            dt = datetime.fromtimestamp(int(timestamp))
            return dt.strftime("%H:%M %d/%m")
    except:
        pass
    now = datetime.now()
    return now.strftime("%H:%M %d/%m")

def generate_m3u():
    # 1. Lấy dữ liệu live từ API chính
    live_data = fetch_json(LIVE_DATA_URL)
    if not live_data or "bb_live_data" not in live_data:
        print("Không kết nối được API cakhia.")
        return

    matches = live_data.get("bb_live_data", [])
    m3u_content = "#EXTM3U\n\n"
    
    default_casters = ["Cris", "A Long", "Khang Hi", "Siêu Quậy", "Kayti", "Wem By"]
    
    for idx, match in enumerate(matches):
        match_id = match.get("match_id", "")
        status = match.get("status_name", "NS")
        
        # Bỏ qua các trận đã kết thúc hoàn toàn (FT) để playlist sạch sẽ
        if status == "FT":
            continue
            
        # 2. Thử truy vấn thêm thông tin chi tiết từng trận nếu API hỗ trợ cấu trúc match detail
        # Dựa theo pattern của các trang bóng đá/bóng rổ dạng này:
        detail_url = f"https://seo.alpro-api-service.com/v1/bb-match/{match_id}"
        match_info = fetch_json(detail_url) or {}
        
        # Trích xuất thông tin thực tế từ API chi tiết hoặc fallback an toàn
        home_team = match_info.get("home_name", match_info.get("home_team", f"Đội Nhà {idx+1}"))
        away_team = match_info.get("away_name", match_info.get("away_team", f"Đội Khách {idx+1}"))
        home_logo = match_info.get("home_logo", match_info.get("home_image", ""))
        
        # Lấy thời gian thực trận đấu
        raw_time = match_info.get("start_time", match_info.get("time", match.get("time")))
        time_str = format_time(raw_time)
        
        # Bình luận viên & Nhóm kênh
        commentator = match_info.get("caster", default_casters[idx % len(default_casters)])
        blv_str = f" ({commentator})" if commentator else ""
        channel_name = match_info.get("channel_name", "Gà Vàng 24h TV")
        
        # Trạng thái hiển thị (🟢 nếu đang đá Live, trống nếu sắp diễn ra)
        status_icon = "🟢" if status not in ["NS", "TBD"] else ""
        sport_icon = "🏀" if "basket" in match_id.lower() or "basket" in str(match_info).lower() else "⚽"
        
        # Chuẩn hóa chuỗi tiêu đề hiển thị đúng yêu cầu
        title_base = f"{status_icon} {time_str} {sport_icon} {home_team} vs {away_team}{blv_str}".strip()
        
        # Các luồng phát HLS và FLV chuẩn của cakhia
        streams = [
            {"type": "hls", "url": f"https://playback.livetl002.com/live/{match_id}.m3u8"},
            {"type": "flv", "url": f"https://playback.livetl002.com/live/{match_id}.flv"}
        ]
        
        for stream in streams:
            stype = stream["type"]
            surl = stream["url"]
            full_title = f"{title_base} [{stype}]"
            
            m3u_item = f'#EXTINF:-1 tvg-logo="{home_logo}" group-title="{channel_name}" , {full_title}\n{surl}\n\n'
            m3u_content += m3u_item

    # Lưu file playlist.m3u
    with open(OUTPUT_M3U, "w", encoding="utf-8") as f:
        f.write(m3u_content.strip() + "\n")
    print(f"Đã cập nhật file {OUTPUT_M3U} thành công với dữ liệu chuẩn từ API mới!")

if __name__ == "__main__":
    generate_m3u()
    
