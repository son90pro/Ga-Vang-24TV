import json
import urllib.request
import re
from datetime import datetime, timezone, timedelta

# Endpoint chính chứa HTML live content được phát hiện từ Network tab
LIVE_CONTENT_URL = "https://cakhia.gold/app/uploads/match-content/update-content-live.json"
FALLBACK_API = "https://seo.alpro-api-service.com/v1/bb-live-data"
OUTPUT_M3U = "playlist.m3u"

def fetch_data(url):
    try:
        req = urllib.request.Request(
            url, 
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://cakhia.gold/"
            }
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            content = response.read().decode("utf-8")
            try:
                return json.loads(content)
            except:
                return content
    except Exception as e:
        print(f"Lỗi kết nối {url}: {e}")
        return None

def generate_m3u():
    vn_tz = timezone(timedelta(hours=7))
    current_time_str = datetime.now(vn_tz).strftime("%H:%M %d/%m")
    
    matches = []
    
    # 1. Thử lấy dữ liệu từ file JSON chứa live_content HTML
    res_data = fetch_data(LIVE_CONTENT_URL)
    
    if isinstance(res_data, dict) and "live_content" in res_data:
        html_content = res_data["live_content"]
        
        # Quét tất cả các match_id xuất hiện trong đường dẫn /live/{match_id}
        match_ids = re.findall(r'/live/([a-zA-Z0-9]+)', html_content)
        match_ids = list(dict.fromkeys(match_ids)) # Lọc trùng ID
        
        default_casters = ["Cris", "A Long", "Khang Hi", "Siêu Quậy", "Kayti", "Wem By"]
        
        for idx, m_id in enumerate(match_ids):
            matches.append({
                "match_id": m_id,
                "home": f"Đội Nhà {idx+1}",
                "away": f"Đội Khách {idx+1}",
                "logo": "",
                "caster": default_casters[idx % len(default_casters)],
                "time": current_time_str
            })

    # 2. Fallback nếu không đọc được live_content: quét qua API bb-live-data
    if not matches:
        api_data = fetch_data(FALLBACK_API)
        if isinstance(api_data, dict) and "bb_live_data" in api_data:
            default_casters = ["Cris", "A Long", "Khang Hi", "Siêu Quậy", "Kayti", "Wem By"]
            for idx, item in enumerate(api_data["bb_live_data"]):
                status = item.get("status_name", "NS")
                if status == "FT":
                    continue
                m_id = item.get("match_id")
                matches.append({
                    "match_id": m_id,
                    "home": f"Đội Nhà {idx+1}",
                    "away": f"Đội Khách {idx+1}",
                    "logo": "",
                    "caster": default_casters[idx % len(default_casters)],
                    "time": current_time_str
                })

    # Tiến hành tạo nội dung file M3U chuẩn khớp yêu cầu
    m3u_content = "#EXTM3U\n\n"
    count = 0
    
    for match in matches:
        m_id = match["match_id"]
        home = match["home"]
        away = match["away"]
        logo = match["logo"]
        caster = match["caster"]
        time_str = match["time"]
        
        channel_name = "Gà Vàng 24h TV"
        
        # Định dạng chuẩn: Giờ Ngày | Icon bóng đá | Tên đội vs Tên đội (BLV)
        title_base = f"{time_str} ⚽ {home} vs {away} ({caster})"
        
        # Tạo 2 luồng phát [hls] và [flv] tương ứng
        streams = [
            {"type": "hls", "url": f"https://playback.livetl002.com/live/{m_id}.m3u8"},
            {"type": "flv", "url": f"https://playback.livetl002.com/live/{m_id}.flv"}
        ]
        
        for stream in streams:
            stype = stream["type"]
            surl = stream["url"]
            full_title = f"{title_base} [{stype}]"
            
            m3u_item = f'#EXTINF:-1 tvg-logo="{logo}" group-title="{channel_name}" , {full_title}\n{surl}\n\n'
            m3u_content += m3u_item
            count += 1

    # Lưu kết quả ra file playlist.m3u
    with open(OUTPUT_M3U, "w", encoding="utf-8") as f:
        f.write(m3u_content.strip() + "\n")
    print(f"Đã cập nhật thành công {count} luồng phát vào file {OUTPUT_M3U}!")

if __name__ == "__main__":
    generate_m3u()
    
