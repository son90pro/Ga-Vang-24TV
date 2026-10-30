import json
import urllib.request
from datetime import datetime, timezone, timedelta

# Hai API chính thức: Bóng đá (live-data) và Bóng rổ (bb-live-data)
FOOTBALL_API = "https://seo.alpro-api-service.com/v1/live-data"
BASKETBALL_API = "https://seo.alpro-api-service.com/v1/bb-live-data"
OUTPUT_M3U = "playlist.m3u"

def fetch_json(url):
    try:
        req = urllib.request.Request(
            url, 
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as e:
        print(f"Lỗi kết nối {url}: {e}")
        return None

def get_vietnam_time(timestamp=None):
    """Chuyển đổi thời gian chuẩn múi giờ Việt Nam (UTC+7)"""
    vn_tz = timezone(timedelta(hours=7))
    if timestamp:
        try:
            dt = datetime.fromtimestamp(int(timestamp), vn_tz)
            return dt.strftime("%H:%M %d/%m")
        except:
            pass
    return datetime.now(vn_tz).strftime("%H:%M %d/%m")

def parse_matches(data, sport_icon):
    results = []
    if not data:
        return results
    
    match_list = []
    if isinstance(data, dict):
        for k, v in data.items():
            if isinstance(v, list):
                match_list = v
                break
    elif isinstance(data, list):
        match_list = data

    default_casters = ["Cris", "A Long", "Khang Hi", "Siêu Quậy", "Kayti", "Wem By"]

    for idx, item in enumerate(match_list):
        if not isinstance(item, dict):
            continue
            
        status = item.get("status_name", "NS")
        if status == "FT":
            continue
            
        match_id = item.get("match_id") or item.get("id")
        if not match_id:
            continue
            
        # Lấy tên đội bóng từ các trường dữ liệu thực tế của API
        home = (
            item.get("home_name") or 
            item.get("home_team") or 
            item.get("home_title") or 
            item.get("home") or 
            item.get("team1") or 
            "Đội Nhà"
        )
        away = (
            item.get("away_name") or 
            item.get("away_team") or 
            item.get("away_title") or 
            item.get("away") or 
            item.get("team2") or 
            "Đội Khách"
        )
        
        logo = (
            item.get("home_logo") or 
            item.get("home_image") or 
            item.get("logo") or 
            ""
        )
        
        caster = (
            item.get("caster") or 
            item.get("commentator") or 
            item.get("blv") or 
            default_casters[idx % len(default_casters)]
        )
        
        raw_time = item.get("start_time") or item.get("time") or item.get("match_time")
        time_str = get_vietnam_time(raw_time)
        
        results.append({
            "match_id": match_id,
            "home": home,
            "away": away,
            "logo": logo,
            "caster": caster,
            "time": time_str,
            "status": status,
            "sport_icon": sport_icon
        })
        
    return results

def generate_m3u():
    football_data = fetch_json(FOOTBALL_API)
    basketball_data = fetch_json(BASKETBALL_API)
    
    matches = []
    matches.extend(parse_matches(football_data, "⚽"))
    matches.extend(parse_matches(basketball_data, "🏀"))
    
    m3u_content = "#EXTM3U\n\n"
    count = 0
    
    for m in matches:
        m_id = m["match_id"]
        home = m["home"]
        away = m["away"]
        logo = m["logo"]
        caster = m["caster"]
        time_str = m["time"]
        status = m["status"]
        sport_icon = m["sport_icon"]
        
        status_icon = "🟢" if status not in ["NS", "TBD"] else ""
        blv_str = f" ({caster})" if caster else ""
        
        title_base = f"{status_icon} {time_str} {sport_icon} {home} vs {away}{blv_str}".strip()
        channel_name = "Gà Vàng 24h TV"
        
        # Tạo 2 luồng phát [hls] và [flv] đúng chuẩn
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

    with open(OUTPUT_M3U, "w", encoding="utf-8") as f:
        f.write(m3u_content.strip() + "\n")
    print(f"Đã cập nhật thành công {count} luồng vào file {OUTPUT_M3U}!")

if __name__ == "__main__":
    generate_m3u()
    
