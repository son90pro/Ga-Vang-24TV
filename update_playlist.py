import json
import urllib.request
from datetime import datetime, timezone, timedelta

# API chính từ cakhia.gold
API_URL = "https://seo.alpro-api-service.com/v1/bb-live-data"
OUTPUT_M3U = "playlist.m3u"

def fetch_data():
    try:
        req = urllib.request.Request(
            API_URL, 
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as e:
        print(f"Lỗi kết nối API: {e}")
        return None

def get_vietnam_time(timestamp=None):
    """Chuyển đổi hoặc lấy thời gian hiện chuẩn múi giờ Việt Nam (UTC+7)"""
    vn_tz = timezone(timedelta(hours=7))
    if timestamp:
        try:
            dt = datetime.fromtimestamp(int(timestamp), vn_tz)
            return dt.strftime("%H:%M %d/%m")
        except:
            pass
    # Mặc định lấy thời gian hiện tại theo giờ Việt Nam
    now_vn = datetime.now(vn_tz)
    return now_vn.strftime("%H:%M %d/%m")

def generate_m3u():
    data = fetch_data()
    if not data or "bb_live_data" not in data:
        print("Không lấy được dữ liệu từ API.")
        return

    matches = data.get("bb_live_data", [])
    m3u_content = "#EXTM3U\n\n"
    
    # Danh sách bình luận viên xoay vòng cho các trận
    default_casters = ["Cris", "A Long", "Khang Hi", "Siêu Quậy", "Kayti", "Wem By"]
    
    for idx, match in enumerate(matches):
        match_id = match.get("match_id", "")
        status = match.get("status_name", "NS")
        
        # Bỏ qua các trận đã kết thúc hoàn toàn (FT) để playlist gọn gàng
        if status == "FT":
            continue
            
        # Lấy thời gian chuẩn Việt Nam
        raw_time = match.get("start_time", match.get("time"))
        time_str = get_vietnam_time(raw_time)
        
        # Trích xuất tên đội và logo nếu API trả về, nếu không sẽ gọi endpoint chi tiết hoặc fallback
        home_team = match.get("home_name", match.get("home_team", ""))
        away_team = match.get("away_name", match.get("away_team", ""))
        home_logo = match.get("home_logo", match.get("home_image", ""))
        
        # Nếu API danh sách không có tên đội, ta thử lấy thông tin từ endpoint chi tiết trận đấu
        if not home_team or not away_team:
            try:
                detail_url = f"https://seo.alpro-api-service.com/v1/bb-match/{match_id}"
                req_detail = urllib.request.Request(detail_url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req_detail, timeout=3) as res_det:
                    det_data = json.loads(res_det.read().decode("utf-8"))
                    home_team = det_data.get("home_name", f"Trận {idx+1} (Nhà)")
                    away_team = det_data.get("away_name", f"Trận {idx+1} (Khách)")
                    home_logo = det_data.get("home_logo", home_logo)
            except:
                # Fallback an toàn nếu không gọi được API chi tiết
                home_team = f"CLB Nhà {idx+1}"
                away_team = f"CLB Khách {idx+1}"

        # Bình luận viên & nhà đài
        commentator = match.get("caster", default_casters[idx % len(default_casters)])
        blv_str = f" ({commentator})" if commentator else ""
        channel_name = match.get("channel_name", "Gà Vàng 24h TV")
        
        # Trạng thái Live (🟢 nếu đang đá, để trống nếu sắp diễn ra)
        status_icon = "🟢" if status not in ["NS", "TBD"] else ""
        sport_icon = "⚽"
        
        # Chuẩn hóa tiêu đề hiển thị
        title_base = f"{status_icon} {time_str} {sport_icon} {home_team} vs {away_team}{blv_str}".strip()
        
        # Tạo 2 luồng phát [hls] và [flv]
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
    print(f"Đã cập nhật file {OUTPUT_M3U} thành công với múi giờ Việt Nam và thông tin trận đấu!")

if __name__ == "__main__":
    generate_m3u()
    
