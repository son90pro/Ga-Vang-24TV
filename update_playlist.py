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
    # Tùy thuộc cấu trúc JSON thực tế của API, lấy danh sách trận đấu
    matches = data.get("bb_live_data", [])
    
    m3u_content = "#EXTM3U x-tvg-url=\"\"\n"
    
    for match in matches:
        match_id = match.get("match_id", "")
        status = match.get("status_name", "NS")
        
        # Bỏ qua các trận đã kết thúc hoàn toàn nếu muốn gọn danh sách
        if status == "FT":
            continue
            
        # Trích xuất thông tin tên đội, logo, bình luận viên (fallback an toàn nếu API đổi tên trường)
        home_team = match.get("home_team", match.get("home_name", "Đội Nhà"))
        away_team = match.get("away_team", match.get("away_name", "Đội Khách"))
        home_logo = match.get("home_logo", match.get("home_image", ""))
        away_logo = match.get("away_logo", match.get("away_image", ""))
        
        # Lấy tên bình luận viên (nếu API có trả về, ví dụ: caster, commentator, blv)
        commentator = match.get("commentator", match.get("caster", match.get("blv", "")))
        blv_str = f" ({commentator})" if commentator else ""
        
        # Lấy tên kênh hoặc phân nhóm (ví dụ: Gà Vàng 24h TV, Xôi Lạc Z TV,...)
        channel_name = match.get("channel_name", match.get("group_name", "Gà Vàng 24h TV"))
        
        # Tiêu đề hiển thị trên IPTV player (giống mẫu hình 2)
        home_score = match.get("home_score", 0)
        away_score = match.get("away_score", 0)
        
        if status in ["NS", "TBD"]:
            time_status = "Sắp diễn ra"
        else:
            time_status = f"{status} ({home_score}-{away_score})"
            
        title = f"{time_status} ⚽ {home_team} vs {away_team}{blv_str}"
        
        # Link stream tương ứng
        stream_url = f"https://cakhia.gold/live/{match_id}"
        
        # Định dạng dòng EXTINF chuẩn IPTV hỗ trợ logo và nhóm kênh
        # Sử dụng logo đội nhà làm tvg-logo chính đại diện cho trận đấu
        logo_url = home_logo if home_logo else ""
        
        item_string = f'#EXTINF:-1 tvg-id="{match_id}" tvg-name="{home_team} vs {away_team}" tvg-logo="{logo_url}" group-title="{channel_name}",{title}\n{stream_url}\n'
        m3u_content += item_string

    with open(OUTPUT_M3U, "w", encoding="utf-8") as f:
        f.write(m3u_content)
    print(f"Đã cập nhật file {OUTPUT_M3U} thành công với đầy đủ logo, tên đội và BLV!")

if __name__ == "__main__":
    generate_m3u()
    
