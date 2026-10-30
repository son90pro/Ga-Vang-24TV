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

def extract_info(item, keys, default_val):
    """Hàm hỗ trợ bóc tách dữ liệu an toàn (xử lý được cả dạng chuỗi lẫn dictionary từ API)"""
    for key in keys:
        val = item.get(key)
        if val:
            if isinstance(val, str) and val.strip():
                return val.strip()
            elif isinstance(val, dict):
                for sub_key in ["name", "team_name", "title", "common_name", "url", "link"]:
                    sub_val = val.get(sub_key)
                    if isinstance(sub_val, str) and sub_val.strip():
                        return sub_val.strip()
    return default_val

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
        format_match_id = str(match_id).strip() if match_id else None
        if not format_match_id:
            continue
            
        # Lấy tên đội bóng và logo chuẩn xác (tự động bóc tách dù API trả về chuỗi hay object dict)
        home = extract_info(item, ["home_name", "home_team_name", "home_title", "home_team", "home", "team1"], "Đội Nhà")
        away = extract_info(item, ["away_name", "away_team_name", "away_title", "away_team", "away", "team2"], "Đội Khách")
        logo = extract_info(item, ["home_logo", "home_image", "logo", "team1_logo", "image"], "")
        
        caster = (
            item.get("caster") or 
            item.get("commentator") or 
            item.get("blv") or 
            default_casters[idx % len(default_casters)]
        )
        
        raw_time = item.get("start_time") or item.get("time") or item.get("match_time")
        time_str = get_vietnam_time(raw_time)
        
        results.append({
            "match_id": format_match_id,
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
    
    # Lọc bỏ các trận đấu trùng lặp dựa trên match_id duy nhất
    seen_ids = set()
    unique_matches = []
    for m in matches:
        if m["match_id"] not in seen_ids:
            seen_ids.add(m["match_id"])
            unique_matches.append(m)
            
    m3u_content = "#EXTM3U\n\n"
    count = 0
    
    for m in unique_matches:
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
    
