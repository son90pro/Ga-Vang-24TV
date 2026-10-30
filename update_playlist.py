import json
import urllib.request
import re
from datetime import datetime, timezone, timedelta
from html import unescape

# Các endpoint chính thức từ gavangtvs.com (Bóng đá & Bóng rổ)
FOOTBALL_API = "https://gavangtvs.com/app/uploads/match-content/update-content-live.json"
BASKETBALL_API = "https://gavangtvs.com/app/uploads/match-content/update-bb-live.json"
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

def parse_html_content(html_text, sport_icon):
    """Phân tích chuỗi HTML trong live_content để trích xuất thông tin trận đấu"""
    matches = []
    if not html_text or not isinstance(html_text, str):
        return matches

    html_clean = unescape(html_text)
    found_ids = set()
    
    # Các mẫu regex để tìm match_id từ link playback hoặc các thuộc tính dữ liệu
    id_patterns = [
        r'/live/([a-fA-F0-9]{24})\.(?:m3u8|flv)',
        r'data-match-id=["\']?([a-fA-F0-9]{24})["\']?',
        r'data-id=["\']?([a-fA-F0-9]{24})["\']?',
        r'match_id["\']?\s*[:=]\s*["\']?([a-fA-F0-9]{24})["\']?'
    ]
    
    # Chia nhỏ HTML thành các khối trận đấu (match-card) nếu có
    cards = re.split(r'<(?:div|article)[^>]*class="[^"]*match-card[^"]*"', html_clean)
    if len(cards) <= 1:
        for pattern in id_patterns:
            matches_found = re.findall(pattern, html_clean)
            for m_id in matches_found:
                if m_id not in found_ids:
                    found_ids.add(m_id)
                    matches.append({
                        "match_id": m_id,
                        "home": "Đội Nhà",
                        "away": "Đội Khách",
                        "logo": "",
                        "caster": "Cris",
                        "time": datetime.now(timezone(timedelta(hours=7))).strftime("%H:%M %d/%m"),
                        "sport_icon": sport_icon,
                        "status": "LIVE"
                    })
    else:
        for card in cards[1:]:
            match_id = None
            for pattern in id_patterns:
                m = re.search(pattern, card)
                if m:
                    match_id = m.group(1)
                    break
            
            if not match_id or match_id in found_ids:
                continue
            found_ids.add(match_id)

            # Trích xuất logo
            logo_match = re.search(r'src=["\'](https?://[^"\']+\.(?:png|jpg|jpeg|webp))["\']', card, re.IGNORECASE)
            if not logo_match:
                logo_match = re.search(r'background-image:\s*url\(["\']?(https?://[^"\']+)["\']?\)', card, re.IGNORECASE)
            logo = logo_match.group(1) if logo_match else ""

            # Làm sạch text trong card để bóc tách thông tin
            text_clean = re.sub(r'<[^>]+>', ' ', card)
            text_clean = ' '.join(text_clean.split())

            home, away = "Đội Nhà", "Đội Khách"
            vs_match = re.search(r'([A-Za-z0-9\s\(\)\.\-]+?)\s+(?:vs|VS|v|V)\s+([A-Za-z0-9\s\(\)\.\-]+)', text_clean)
            if vs_match:
                h_candidate = vs_match.group(1).strip().split()[-3:]
                a_candidate = vs_match.group(2).strip().split()[:3]
                if h_candidate: home = " ".join(h_candidate)
                if a_candidate: away = " ".join(a_candidate)

            caster = "Cris"
            caster_match = re.search(r'\((?:BLV\s*)?([A-Za-z0-9\s\.]+)\)', text_clean)
            if caster_match:
                potential_caster = caster_match.group(1).strip()
                if len(potential_caster) < 20 and not any(w in potential_caster for w in ["hls", "flv", "Live", "FT"]):
                    caster = potential_caster

            time_str = datetime.now(timezone(timedelta(hours=7))).strftime("%H:%M %d/%m")
            time_match = re.search(r'(\d{2}:\d{2}(?:\s+\d{2}/\d{2})?)', text_clean)
            if time_match:
                time_str = time_match.group(1).strip()

            matches.append({
                "match_id": match_id,
                "home": home if len(home) > 1 else "Đội Nhà",
                "away": away if len(away) > 1 else "Đội Khách",
                "logo": logo,
                "caster": caster,
                "time": time_str,
                "sport_icon": sport_icon,
                "status": "LIVE"
            })

    return matches

def generate_m3u():
    matches = []
    
    # Lấy dữ liệu Bóng đá
    fb_data = fetch_json(FOOTBALL_API)
    if fb_data and isinstance(fb_data, dict):
        matches.extend(parse_html_content(fb_data.get("live_content", ""), "⚽"))

    # Lấy dữ liệu Bóng rổ
    bb_data = fetch_json(BASKETBALL_API)
    if bb_data and isinstance(bb_data, dict):
        matches.extend(parse_html_content(bb_data.get("live_content", ""), "🏀"))

    # Lọc bỏ trùng lặp theo match_id
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
        sport_icon = m["sport_icon"]
        
        status_icon = "🟢"
        
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
    
