import requests
import time
import json
import datetime
import os
from collections import defaultdict
from datetime import datetime, timezone, timedelta
import praw

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
        time.sleep(1)  # be nice to the server
        
        # Extract metadata (assuming the first element is the post data)
        post_metadata = (details.get("posts", [])[0:1] or [{}])[0]
        post_name = post_metadata.get("title", "")
        score = post_metadata.get("score", 0)
        uuid = post_metadata.get("uuid", "")
        post_url = f"https://patriots.win/p/{uuid}"
        
        raw_comments = details.get("comments", [])
        comments_count = len(raw_comments) if isinstance(raw_comments, list) else 0
        
        created = post_metadata.get("created")
        if created:
            posted_at = datetime.utcfromtimestamp(created / 1000).strftime("%Y-%m-%d %H:%M:%S UTC")
        else:
            posted_at = ""
        
        text_content = post_metadata.get("content", "")
        
        nested_comments = build_comment_tree(raw_comments, max_depth=4)
        
        post_data = {
            "post_name": post_name,
            "score": score,
            "url": post_url,
            "comments_count": comments_count,
            "posted_at": posted_at,
            "text_content": text_content,
            "comments": nested_comments,
            "subreddit": "r/thedonald"  # Treat patriots.win posts as from r/thedonald
        }
        all_posts.append(post_data)
    
    return all_posts

def fetch_patriots_post_details(post_id):
    url = f"https://patriots.win/api/v2/post/post.json?id={post_id}&comments=true"
    response = requests.get(url)
    return response.json()

def build_comment_tree(comments, max_depth=4):
    children = defaultdict(list)
    for c in comments:
        parent_id = c.get("comment_parent_id", 0)
        children[parent_id].append(c)
    
    # Sort children by score descending
    for key in children:
        children[key].sort(key=lambda x: x.get("score", 0), reverse=True)
    
    def build_tree(comment, depth):
        node = {
            "raw_content": comment.get("raw_content", ""),
            "author": comment.get("author", "")
        }
        if depth < max_depth:
            # Limit each level to the top 4 replies
            node["replies"] = [build_tree(child, depth + 1) for child in children.get(comment.get("id"), [])[:4]]
        else:
            node["replies"] = []
        return node
    
    # Get top-level comments (parent id 0) and limit to first 5 chains
    top_level = [c for c in comments if c.get("comment_parent_id", 0) == 0][:5]
    return [build_tree(c, 1) for c in top_level]

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
                # Map Reddit fields to the unified format
                post_data = {
                    "post_name": post.title,
                    "score": post.score,
                    "url": post.url,
                    "comments_count": post.num_comments,
                    "posted_at": post_time.strftime("%Y-%m-%d %H:%M:%S UTC"),
                    "text_content": post.selftext,
                    "comments": [],
                    "subreddit": subreddit_name
                }
                
                # Fetch up to 5 top-level comments (1-level deep)
                post.comments.replace_more(limit=1)
                for comment in post.comments[:5]:
                    comment_data = {
                        "raw_content": comment.body,
                        "author": str(comment.author),
                        "replies": []  # No nested replies for simplicity
                    }
                    post_data["comments"].append(comment_data)
                
                results.append(post_data)
    return results

# ------------------ MAIN FUNCTION ------------------
def main():
    combined_posts = []
    
    # Fetch posts from patriots.win
    try:
        patriots_posts = fetch_patriots_posts()
    except Exception as e:
        print("Error fetching patriots posts:", e)
        patriots_posts = []
    
    # Fetch posts from Reddit (using the defined subreddits)
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

