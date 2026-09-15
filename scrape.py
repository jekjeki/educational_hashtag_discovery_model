import instaloader
import json
from datetime import datetime
import os

class InstagramCrawler:
    def __init__(self):
        self.loader = instaloader.Instaloader()
        
    def login(self, username, password):
        """Login ke Instagram (opsional, untuk akun private)"""
        try:
            self.loader.login(username, password)
            print("Login berhasil!")
            return True
        except Exception as e:
            print(f"Login gagal: {e}")
            return False
    
    def crawl_posts(self, username, max_posts=500):
        """Crawl posts dari akun Instagram"""
        posts_data = []
        
        try:
            profile = instaloader.Profile.from_username(
                self.loader.context, 
                username
            )
            
            print(f"Mengambil data dari @{username}")
            print(f"Followers: {profile.followers}")
            print(f"Following: {profile.followees}")
            print(f"Total Posts: {profile.mediacount}\n")
            
            for idx, post in enumerate(profile.get_posts()):
                if idx >= max_posts:
                    break
                
                post_info = {
                    'shortcode': post.shortcode,
                    'url': f"https://www.instagram.com/p/{post.shortcode}/",
                    'caption': post.caption if post.caption else "",
                    'likes': post.likes,
                    'comments': post.comments,
                    'date': post.date_utc.strftime('%Y-%m-%d %H:%M:%S'),
                    'is_video': post.is_video,
                    'video_views': post.video_view_count if post.is_video else 0,
                    'location': post.location.name if post.location else None,
                    'hashtags': list(post.caption_hashtags) if post.caption_hashtags else []
                }
                
                posts_data.append(post_info)
                print(f"Post {idx + 1} berhasil diambil - Likes: {post.likes}, Comments: {post.comments}")
            
            return posts_data
            
        except Exception as e:
            print(f"Error: {e}")
            return []
    
    def save_to_json(self, data, filename='instagram_posts.json'):
        """Simpan data ke file JSON"""
        folder = "dataset"
        os.makedirs(folder, exist_ok=True)
        
        file_path = os.path.join(folder, filename)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\nData berhasil disimpan ke {filename}")
    
    def download_posts(self, username, max_posts=10):
        """Download posts beserta gambar/video"""
        try:
            profile = instaloader.Profile.from_username(
                self.loader.context, 
                username
            )
            
            for idx, post in enumerate(profile.get_posts()):
                if idx >= max_posts:
                    break
                self.loader.download_post(post, target=f"{username}_posts")
                print(f"Post {idx + 1} berhasil didownload")
                
        except Exception as e:
            print(f"Error downloading: {e}")


if __name__ == "__main__":
    crawler = InstagramCrawler()
    
    # for private account
    # crawler.login('username', 'password')
    
    # Crawl posts dari akun tertentu
    target_username = "lifeatpcu"
    posts = crawler.crawl_posts(target_username, max_posts=500)
    
    # Simpan ke JSON
    if posts:
        crawler.save_to_json(posts, filename=f"{target_username}_posts.json")
    
    # download posts 
    # crawler.download_posts(target_username, max_posts=5)