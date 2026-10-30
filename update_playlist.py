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

def extract_teams_from_item(item):
    """Bóc tách tên đội bóng thông minh từ mọi ngóc ngách của API JSON"""
    home, away, logo = "", "", ""
    
    # 1. Quét các key phổ biến cho Home
    for k in ["home_name", "home_team_name", "home_title", "home_team", "home", "team1", "t1", "host"]:
        val = item.get(k)
        if val:
            if isinstance(val, str) and val.strip():
                home = val.strip()
                break
            elif isinstance(val, dict):
                for sub in ["name", "team_name", "title", "common_name", "display_name"]:
                    if isinstance(val.get(sub), str) and val.get(sub).strip():
                        home = val.get(sub).strip()
                        break
                for l_sub in ["logo", "image", "badge", "flag", "url"]:
                    if isinstance(val.get(l_sub), str) and val.get(l_sub).startswith("http"):
                        logo = val.get(l_sub).strip()
                        break
                if home:
                    break

    # 2. Quét các key phổ biến cho Away
    for k in ["away_name", "away_team_name", "away_title", "away_team", "away", "team2", "t2", "guest", "visitor"]:
        val = item.get(k)
        if val:
            if isinstance(val, str) and val.strip():
                away = val.strip()
                break
            elif isinstance(val, dict):
                for sub in ["name", "team_name", "title", "common_name", "display_name"]:
                    if isinstance(val.get(sub), str) and val.get(sub).strip():
                        away = val.get(sub).strip()
                        break
                if away:
                    break

    # 3. Lấy logo nếu nằm ở các key riêng biệt ngoài cùng
    if not logo:
        for k in ["home_logo", "home_image", "logo", "team1_logo", "image", "badge"]:
            val = item.get(k)
            if isinstance(val, str) and val.startswith("http"):
                logo = val.strip()
                break

    # 4. Fallback thông minh: Tự bóc tách từ chuỗi title/name nếu API không trả về key riêng
    if not home or not away or home == "Đội Nhà" or away == "Đội Khách":
        for title_key in ["title", "name", "match_name", "slug", "tournament_name"]:
            t_val = item.get(title_key)
            if isinstance(t_val, str) and any(sep in t_val for sep in [" vs ", " VS ", " v ", " V ", " vs. ", " - "]):
                for sep in [" vs ", " VS ", " v ", " V ", " vs. ", " - "]:
                    if sep in t_val:
                        parts = t_val.split(sep)
                        if len(parts) >= 2:
                            if not home or home == "Đội Nhà":
                                home = parts[0].strip()
                            if not away or away == "Đội Khách":
                                away = parts[1].strip()
                            break
                if home and away and home != "Đội Nhà" and away != "Đội Khách":
                    break

    return (home or "Đội Nhà", away or "Đội Khách", logo)

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
            
        match_id = item.get("match_id") or item.get("id")
        format_match_id = str(match_id).strip() if match_id else None
        if not format_match_id:
            continue
            
        home, away, logo = extract_teams_from_item(item)
        
        caster = (
            item.get("caster") or 
            item.get("commentator") or 
            item.get("blv") or 
            default_casters[idx % len(default_casters)]
        )
        
        raw_time = item.get("start_time") or item.get("time") or item.get("match_time")
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
    print(f"Đã cập nhật thành công file {OUTPUT_M3U}!")

if __name__ == "__main__":
    generate_m3u()
    
