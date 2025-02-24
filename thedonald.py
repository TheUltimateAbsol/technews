import requests
import time
import json
import datetime
from collections import defaultdict

# Fetch the list of posts from the first URL
def fetch_posts():
    url = "https://patriots.win/api/v2/post/hotv2.json?community=thedonald"
    response = requests.get(url)
    data = response.json()
    return data.get("posts", [])

# Fetch detailed post info (including comments) for a given post ID
def fetch_post_details(post_id):
    url = f"https://patriots.win/api/v2/post/post.json?id={post_id}&comments=true"
    response = requests.get(url)
    return response.json()

# Build a nested comment tree up to a maximum depth (4 levels) with limited fields and limited branches per level (max 4)
def build_comment_tree(comments, max_depth=4):
    # Build mapping from parent id to list of child comments
    children = defaultdict(list)
    for c in comments:
        parent_id = c.get("comment_parent_id", 0)
        children[parent_id].append(c)
    
    # Sort each children list by score (highest first)
    for key in children:
        children[key].sort(key=lambda x: x.get("score", 0), reverse=True)
    
    # Recursive function to build the tree with controlled depth, including only desired fields and limiting branches
    def build_tree(comment, depth):
        node = {
            "raw_content": comment.get("raw_content"),
            "score": comment.get("score"),
            "author": comment.get("author"),
            "created": comment.get("created")
        }
        if depth < max_depth:
            # Limit each level to the top 4 replies by score
            node["replies"] = [build_tree(child, depth + 1) for child in children.get(comment["id"], [])[:4]]
        return node
    
    # Get top-level comments (those with parent id 0) and limit to the first 10 comment chains
    top_level = [c for c in comments if c.get("comment_parent_id") == 0][:10]
    return [build_tree(c, 1) for c in top_level]

def main():
    posts = fetch_posts()[:20]  # Only the first 20 posts
    all_posts = []
    
    total = len(posts)
    for index, post in enumerate(posts, start=1):
        post_id = post["id"]
        details = fetch_post_details(post_id)
        print(f"Fetching post {index} of {total} (ID: {post_id})")
        time.sleep(1)
        
        # Extract required fields
        post_metadata = (details.get("posts", [])[0:1] or [{}])[0]
        post_name = post_metadata.get("title", "")
        score = post_metadata.get("score", 0)
        uuid = post_metadata.get("uuid", "")
        post_url = f"https://patriots.win/p/{uuid}"
        
        raw_comments = details.get("comments", [])
        # Calculate the raw number of comments on the post
        comments_count = len(raw_comments) if isinstance(raw_comments, list) else 0
        
        # Convert created timestamp (in milliseconds) to a UTC time string
        created = post_metadata.get("created")
        if created:
            posted_at = datetime.datetime.utcfromtimestamp(created / 1000).strftime("%Y-%m-%d %H:%M:%S UTC")
        else:
            posted_at = ""
        
        text_content = post_metadata.get("content", "")
        
        # Process comments to build a nested comment tree with limited fields and branches
        if isinstance(raw_comments, list):
            nested_comments = build_comment_tree(raw_comments, max_depth=4)
        else:
            nested_comments = []
        
        post_data = {
            "post_name": post_name,
            "score": score,
            "url": post_url,
            "comments_count": comments_count,
            "posted_at": posted_at,
            "text_content": text_content,
            "comments": nested_comments
        }
        
        all_posts.append(post_data)
    
    # Save the aggregated post data to a JSON file
    with open("posts.json", "w", encoding="utf-8") as f:
        json.dump(all_posts, f, indent=4)
    
    print("All posts have been fetched and saved.")

if __name__ == "__main__":
    main()
