import json
import urllib.request
from datetime import datetime, timezone, timedelta

# Endpoint chính thức mới từ gavangtvs.com
API_URL = "https://gavangtvs.com/app/uploads/match-content/update-content-live.json"
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

def extract_match_info(item):
    """Bóc tách thông minh tên đội, logo, BLV và thời gian từ JSON cấu trúc mới"""
    home = ""
    away = ""
    logo = ""
    caster = "Cris"
    
    if not isinstance(item, dict):
        return "Đội Nhà", "Đội Khách", "", "Cris", datetime.now(timezone(timedelta(hours=7))).strftime("%H:%M %d/%m"), "⚽"

    # 1. Lấy tên đội nhà / đội khách từ các key phổ biến hoặc object con
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

    # 2. Lấy thông tin BLV (Caster)
    for c_key in ["caster", "commentator", "blv", "author"]:
        if c_key in item and isinstance(item[c_key], str) and item[c_key].strip():
            caster = item[c_key].strip()
            break

    # 3. Fallback bóc tách từ chuỗi tiêu đề (title/name) nếu thiếu tên đội
    if not home or not away or home == "Đội Nhà" or away == "Đội Khách":
        for title_k in ["title", "name", "match_name", "slug"]:
            t_val = item.get(title_k)
            if isinstance(t_val, str) and any(sep in t_val for sep in [" vs ", " VS ", " Vs ", " - "]):
                for sep in [" vs ", " VS ", " Vs ", " - "]:
                    if sep in t_val:
                        parts = t_val.split(sep)
                        if len(parts) >= 2:
                            if not home or home == "Đội Nhà": home = parts[0].strip()
                            if not away or away == "Đội Khách": away = parts[1].strip()
                            break

    home = home or "Đội Nhà"
    away = away or "Đội Khách"

    # 4. Xác định môn thể thao (Bóng đá hay Bóng rổ dựa vào nội dung hoặc đường dẫn logo)
    sport_icon = "⚽"
    if "basketball" in logo.lower() or any(b_key in str(item).lower() for b_key in ["basketball", "nba", "bb-"]):
        sport_icon = "🏀"

    raw_time = item.get("start_time") or item.get("time") or item.get("match_time") or item.get("timestamp")
    time_str = format_match_time(raw_time)
    status = str(item.get("status_name") or item.get("status") or "").upper()

    return home, away, logo, caster, time_str, sport_icon, status

def generate_m3u():
    data = fetch_json(API_URL)
    if not data:
        print("Không thể tải dữ liệu từ API mới!")
        return
    
    match_list = []
    if isinstance(data, dict):
        for k in ["data", "matches", "list", "result", "items", "content", "matchList"]:
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

    matches = []
    for idx, item in enumerate(match_list):
        if not isinstance(item, dict):
            continue
            
        match_id = item.get("match_id") or item.get("id") or item.get("matchId")
        format_match_id = str(match_id).strip() if match_id else None
        if not format_match_id:
            continue
            
        home, away, logo, caster, time_str, sport_icon, status = extract_match_info(item)
        
        if status == "FT":
            continue

        matches.append({
            "match_id": format_match_id,
            "home": home,
            "away": away,
            "logo": logo,
            "caster": caster,
            "time": time_str,
            "sport_icon": sport_icon,
            "status": status
        })
    
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
    print(f"Đã cập nhật thành công {len(unique_matches)} trận đấu vào file {OUTPUT_M3U} từ nguồn gavangtvs.com!")

if __name__ == "__main__":
    generate_m3u()
    
