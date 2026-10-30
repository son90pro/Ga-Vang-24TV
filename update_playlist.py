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
    """Chuyển đổi timestamp sang định dạng giờ và ngày tháng chuẩn (VD: 19:58 30/10)"""
    vn_tz = timezone(timedelta(hours=7))
    if timestamp:
        try:
            ts = int(float(timestamp))
            dt = datetime.fromtimestamp(ts, vn_tz)
            return dt.strftime("%H:%M %d/%m")
        except:
            pass
    return datetime.now(vn_tz).strftime("%H:%M %d/%m")

def get_team_info(obj):
    """Trích xuất tên và logo an toàn từ một trường dữ liệu đội bóng (có thể là string hoặc dict)"""
    name = ""
    logo = ""
    if isinstance(obj, str):
        name = obj.strip()
    elif isinstance(obj, dict):
        for k in ["name", "team_name", "title", "common_name", "display_name", "short_name"]:
            val = obj.get(k)
            if isinstance(val, str) and val.strip():
                name = val.strip()
                break
        for k in ["logo", "image", "badge", "flag", "icon", "url"]:
            val = obj.get(k)
            if isinstance(val, str) and val.startswith("http"):
                logo = val.strip()
                break
    return name, logo

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
            
        # 1. Quét tìm tên và logo đội nhà (Home)
        home, logo = "", ""
        for h_key in ["home", "home_team", "home_name", "team1", "t1", "host"]:
            if h_key in item:
                h_name, h_logo = get_team_info(item.get(h_key))
                if h_name:
                    home = h_name
                if h_logo:
                    logo = h_logo
                if home:
                    break

        # 2. Quét tìm tên đội khách (Away)
        away = ""
        for a_key in ["away", "away_team", "away_name", "team2", "t2", "guest", "visitor"]:
            if a_key in item:
                a_name, a_logo = get_team_info(item.get(a_key))
                if a_name:
                    away = a_name
                    if not logo and a_logo:
                        logo = a_logo
                if away:
                    break

        # 3. Quét dự phòng logo nếu nằm ở các key độc lập bên ngoài
        if not logo:
            for l_key in ["home_logo", "logo", "image", "team1_logo", "badge"]:
                l_val = item.get(l_key)
                if isinstance(l_val, str) and l_val.startswith("http"):
                    logo = l_val.strip()
                    break

        # 4. Dự phòng tuyệt đối: Bóc tách trực tiếp từ chuỗi tiêu đề chung
        if not home or not away:
            for title_k in ["title", "name", "match_name", "slug"]:
                t_val = item.get(title_k)
                if isinstance(t_val, str) and any(sep in t_val for sep in [" vs ", " VS ", " - "]):
                    for sep in [" vs ", " VS ", " - "]:
                        if sep in t_val:
                            parts = t_val.split(sep)
                            if len(parts) >= 2:
                                if not home: home = parts[0].strip()
                                if not away: away = parts[1].strip()
                                break
                    if home and away:
                        break

        home = home or "Đội Nhà"
        away = away or "Đội Khách"

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
    
