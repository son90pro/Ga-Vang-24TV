import json
import urllib.request

API_URL = "https://seo.alpro-api-service.com/v1/bb-live-data"
OUTPUT_M3U = "playlist.m3u"

def fetch_data():
    req = urllib.request.Request(
        API_URL, 
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    )
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode("utf-8"))

def generate_m3u():
    data = fetch_data()
    matches = data.get("bb_live_data", [])
    
    # Bắt đầu nội dung file M3U
    m3u_content = "#EXTM3U x-tvg-url=\"\"\n"
    
    # Định nghĩa ưu tiên trạng thái trận đấu
    # Các trận đang đá (Q1, Q2, Q3, Q4...) hoặc sắp đá (NS, TBD)
    active_matches = []
    other_matches = []
    
    for match in matches:
        status = match.get("status_name", "NS")
        # Bỏ qua các trận đã đá xong hoàn toàn nếu muốn gọn, hoặc giữ lại tùy ý
        if status == "FT":
            continue
            
        match_id = match.get("match_id")
        home_score = match.get("home_score", 0)
        away_score = match.get("away_score", 0)
        
        # Tiêu đề hiển thị trên IPTV player
        if status in ["NS", "TBD"]:
            title = f"🔴 [Sắp diễn ra] Match ID: {match_id}"
            group = "Sắp diễn ra"
        else:
            title = f"⚽ [{status}] ({home_score}-{away_score}) Match ID: {match_id}"
            group = "Đang diễn ra (LIVE)"
            
        # Link stream giả định dựa theo cấu trúc cakhia (thường nhúng qua match_id)
        # Anh có thể thay đổi domain stream thực tế của cakhia nếu có player cụ thể
        stream_url = f"https://cakhia.gold/live/{match_id}"
        
        item_string = f"#EXTINF:-1 tvg-group=\"{group}\",{title}\n{stream_url}\n"
        
        # Ưu tiên đưa các trận đang live lên đầu
        if status not in ["NS", "TBD"]:
            active_matches.append(item_string)
        else:
            other_matches.append(item_string)

    # Gộp danh sách: Live ưu tiên trước, sau đó đến Sắp diễn ra
    for item in active_matches + other_matches:
        m3u_content += item

    with open(OUTPUT_M3U, "w", encoding="utf-8") as f:
        f.write(m3u_content)
    print(f"Đã cập nhật thành công file {OUTPUT_M3U} với {len(active_matches) + len(other_matches)} trận đấu!")

if __name__ == "__main__":
    generate_m3u()
  
