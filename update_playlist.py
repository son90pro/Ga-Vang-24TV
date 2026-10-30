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

def extract_teams_and_logo(item):
    """Quét toàn bộ key động trong item để lấy chính xác tên đội nhà, đội khách và logo"""
    home = ""
    away = ""
    logo = ""
    
    if not isinstance(item, dict):
        return "Đội Nhà", "Đội Khách", ""
        
    # Quét tất cả các key trong từ điển JSON của trận đấu
    for k, v in item.items():
        k_lower = k.lower()
        if any(x in k_lower for x in ["home", "team1", "host", "t1"]):
            if isinstance(v, str) and v.strip():
                if not home: home = v.strip()
            elif isinstance(v, dict):
                for sub_k, sub_v in v.items():
                    if isinstance(sub_v, str) and sub_v.strip():
                        if not sub_v.startswith("http") and not home:
                            home = sub_v.strip()
                        elif sub_v.startswith("http") and not logo:
                            logo = sub_v.strip()
        elif any(x in k_lower for x in ["away", "team2", "guest", "visitor", "t2"]):
            if isinstance(v, str) and v.strip():
                if not away: away = v.strip()
            elif isinstance(v, dict):
                for sub_k, sub_v in v.items():
                    if isinstance(sub_v, str) and sub_v.strip() and not sub_v.startswith("http"):
                        if not away: away = sub_v.strip()
        elif any(x in k_lower for x in ["logo", "image", "badge", "flag", "icon"]):
            if isinstance(v, str) and v.startswith("http"):
                if not logo: logo = v.strip()

    # Fallback thông minh: Nếu vẫn thiếu, tìm trong mọi chuỗi có chứa ký tự phân tách trận đấu ("vs", "-")
    if not home or not away or home == "Đội Nhà" or away == "Đội Khách":
        for k, v in item.items():
            if isinstance(v, str) and any(sep in v for sep in [" vs ", " VS ", " Vs ", " - "]):
                for sep in [" vs ", " VS ", " Vs ", " - "]:
                    if sep in v:
                        parts = v.split(sep)
                        if len(parts) >= 2:
                            if not home or home == "Đội Nhà": home = parts[0].strip()
                            if not away or away == "Đội Khách": away = parts[1].strip()
                            break

    return home or "Đội Nhà", away or "Đội Khách", logo

def parse_matches(data, sport_icon):
    results = []
    if not data:
        return results
    
    match_list = []
    if isinstance(data, dict):
        for k in ["data", "matches", "list", "result", "items", "content"]:
            if k in data and isinstance(data[k], list):
                match_list = data[k]
                break
        if not match_list:
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
            
        home, away, logo = extract_teams_and_logo(item)
        
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
    print(f"Đã cập nhật thành công file {OUTPUT_M3U} với {len(unique_matches)} trận đấu!")

if __name__ == "__main__":
    generate_m3u()
    
