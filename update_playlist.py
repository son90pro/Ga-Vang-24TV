import json
import urllib.request
from datetime import datetime, timezone, timedelta

# Endpoint chính thức của hệ thống API gốc
FOOTBALL_API = "https://seo.alpro-api-service.com/v1/live-data"
BASKETBALL_API = "https://seo.alpro-api-service.com/v1/bb-live-data"
OUTPUT_M3U = "playlist.m3u"

def fetch_json(url):
    try:
        req = urllib.request.Request(
            url, 
            headers={
                "User-Agent": "Mozilla/5.0 (Android 16; Mobile; rv:158.0) Gecko/158.0 Firefox/158.0",
                "Referer": "https://gavangtvs.com/"
            }
        )
        with urllib.request.urlopen(req, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as e:
        print(f"Lỗi kết nối {url}: {e}")
        return None

def format_match_time(timestamp):
    """Chuyển đổi timestamp sang định dạng giờ và ngày tháng chuẩn (VD: 12:00 22/09)"""
    vn_tz = timezone(timedelta(hours=7))
    if timestamp:
        try:
            ts = int(float(timestamp))
            dt = datetime.fromtimestamp(ts, vn_tz)
            return dt.strftime("%H:%M %d/%m")
        except:
            pass
    return datetime.now(vn_tz).strftime("%H:%M %d/%m")

def parse_team_field(team_data):
    """Trích xuất chính xác tên và logo từ object hoặc string của API"""
    if isinstance(team_data, str):
        return team_data.strip(), ""
    elif isinstance(team_data, dict):
        name = (
            team_data.get("name") or 
            team_data.get("team_name") or 
            team_data.get("title") or 
            team_data.get("seo_name") or 
            ""
        )
        logo = (
            team_data.get("logo") or 
            team_data.get("image") or 
            team_data.get("flag") or 
            ""
        )
        return str(name).strip(), str(logo).strip()
    return "", ""

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

    default_casters = ["Cris", "A Long", "Khang Hi", "Siêu Quậy", "Kayti", "Wem By", "Titan", "Naruto", "Đoàn Dự", "Rio", "Lữ Bố.Vip"]

    for idx, item in enumerate(match_list):
        if not isinstance(item, dict):
            continue
            
        status = str(item.get("status_name") or item.get("status") or "").upper()
        if status == "FT":
            continue
            
        match_id = item.get("match_id") or item.get("id") or item.get("matchId")
        format_match_id = str(match_id).strip() if match_id else None
        if not format_match_id:
            continue
            
        # Bóc tách đội nhà và đội khách từ API gốc
        home_raw = item.get("home") or item.get("home_team") or item.get("team1") or item.get("home_name")
        away_raw = item.get("away") or item.get("away_team") or item.get("team2") or item.get("away_name")
        
        home_name, home_logo = parse_team_field(home_raw)
        away_name, away_logo = parse_team_field(away_raw)
        
        home = home_name or item.get("home_title") or "Đội Nhà"
        away = away_name or item.get("away_title") or "Đội Khách"
        
        # Lấy logo ưu tiên từ object đội hoặc các trường ngoài
        logo = home_logo or away_logo or item.get("home_logo") or item.get("logo") or item.get("image") or ""
        if isinstance(logo, dict):
            logo = logo.get("url") or logo.get("logo") or ""
        if logo and not str(logo).startswith("http"):
            logo = ""
            
        caster = (
            item.get("caster") or 
            item.get("commentator") or 
            item.get("blv") or 
            default_casters[idx % len(default_casters)]
        )
        
        raw_time = item.get("start_time") or item.get("time") or item.get("match_time") or item.get("timestamp")
        time_str = format_match_time(raw_time)
        
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
            
    m3u_lines = ["#EXTM3U", ""]
    
    for m in unique_matches:
        m_id = m["match_id"]
        home = m["home"]
        away = m["away"]
        logo = m["logo"]
        caster = m["caster"]
        time_str = m["time"]
        status = m["status"]
        sport_icon = m["sport_icon"]
        
        status_icon = "🟢" if status != "FT" else ""
        
        streams = [
            ("hls", f"https://playback.livetl002.com/live/{m_id}.m3u8"),
            ("flv", f"https://playback.livetl002.com/live/{m_id}.flv")
        ]
        
        for stype, surl in streams:
            extinf_line = f'#EXTINF:-1 tvg-logo="{logo}" group-title="Gà Vàng 24h TV" , {status_icon} {time_str} {sport_icon} {home} vs {away} ({caster}) [{stype}]'.strip()
            m3u_lines.append(extinf_line)
            m3u_lines.append(surl)
            m3u_lines.append("")

    with open(OUTPUT_M3U, "w", encoding="utf-8") as f:
        f.write("\n".join(m3u_lines).strip() + "\n")
    print(f"Đã cập nhật thành công {len(unique_matches)} trận đấu vào file {OUTPUT_M3U}!")

if __name__ == "__main__":
    generate_m3u()
    
