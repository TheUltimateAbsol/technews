import requests
import time
import json
import datetime
import os
from datetime import datetime, timezone, timedelta
import praw

# Function to compress text by removing extra whitespace
def compress_text(text):
    if not text:
        return ""
    return " ".join(text.split())

# Function to get only root-level comments (limit to top 3)
def get_root_comments(comments, top_level_limit=3):
    top_level = [c for c in comments if c.get("comment_parent_id", 0) == 0][:top_level_limit]
    root_comments = []
    for c in top_level:
        comment_data = {
            "raw_content": compress_text(c.get("raw_content", "")),
            "author": c.get("author", "")
        }
        root_comments.append(comment_data)
    return root_comments

# ------------------ PATRIOTS.WIN FUNCTIONS ------------------
def fetch_patriots_posts():
    url = "https://patriots.win/api/v2/post/hotv2.json?community=thedonald"
    response = requests.get(url)
    data = response.json()
    posts = data.get("posts", [])[:20]  # Limit to first 20 posts
    all_posts = []
    
    for index, post in enumerate(posts, start=1):
        post_id = post.get("id")
        details = fetch_patriots_post_details(post_id)
        print(f"Fetching patriots post {index} of {len(posts)} (ID: {post_id})")
        time.sleep(1)  # Respect rate limits
        
        post_metadata = (details.get("posts", [])[0:1] or [{}])[0]
        post_name = compress_text(post_metadata.get("title", ""))
        score = post_metadata.get("score", 0)
        text_content = compress_text(post_metadata.get("content", ""))
        
        raw_comments = details.get("comments", [])
        root_comments = get_root_comments(raw_comments, top_level_limit=3)
        
        post_data = {
            "post_name": post_name,
            "score": score,
            "text_content": text_content,
            "comments": root_comments,
            "subreddit": "r/thedonald"  # Tag as coming from r/thedonald
        }
        all_posts.append(post_data)
    
    return all_posts

def fetch_patriots_post_details(post_id):
    url = f"https://patriots.win/api/v2/post/post.json?id={post_id}&comments=true"
    response = requests.get(url)
    return response.json()

# ------------------ REDDIT FUNCTIONS ------------------
def fetch_reddit_posts(subreddits, limit=10):
    reddit = praw.Reddit(
        client_id=os.environ['REDDIT_CLIENT_ID'],
        client_secret=os.environ['REDDIT_CLIENT_SECRET'],
        user_agent=os.environ['REDDIT_USER_AGENT']
    )
    
    now = datetime.now(timezone.utc)
    time_limit = now - timedelta(days=1)
    results = []
    
    for subreddit_name in subreddits:
        subreddit = reddit.subreddit(subreddit_name)
        hot_posts = subreddit.hot(limit=limit)
        
        for post in hot_posts:
            post_time = datetime.fromtimestamp(post.created_utc, tz=timezone.utc)
            if post_time >= time_limit:
                post_data = {
                    "post_name": compress_text(post.title),
                    "score": post.score,
                    "text_content": compress_text(post.selftext),
                    "comments": [],
                    "subreddit": subreddit_name
                }
                post.comments.replace_more(limit=1)
                for comment in post.comments[:3]:
                    comment_data = {
                        "raw_content": compress_text(comment.body),
                        "author": str(comment.author)
                    }
                    post_data["comments"].append(comment_data)
                
                results.append(post_data)
    return results

# ------------------ MAIN FUNCTION ------------------
def main():
    combined_posts = []
    
    try:
        patriots_posts = fetch_patriots_posts()
    except Exception as e:
        print("Error fetching patriots posts:", e)
        patriots_posts = []
    
    reddit_subreddits = ["hardware", "nintendoswitch2", "gamingleaksandrumours", "intel", "amd", "rebubble", "singularity"]
    try:
        reddit_posts = fetch_reddit_posts(reddit_subreddits, limit=10)
    except Exception as e:
        print("Error fetching reddit posts:", e)
        reddit_posts = []
    
    combined_posts.extend(patriots_posts)
    combined_posts.extend(reddit_posts)
    
    with open("combined.json", "w", encoding="utf-8") as f:
        json.dump(combined_posts, f, indent=4)
    
    print("Combined posts saved to combined.json")
    
if __name__ == "__main__":
    main()
