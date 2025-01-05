import praw
import os
from datetime import datetime, timezone, timedelta

# Reddit API Credentials
REDDIT_CLIENT_ID = os.environ['REDDIT_CLIENT_ID']
REDDIT_CLIENT_SECRET = os.environ['REDDIT_CLIENT_SECRET']
REDDIT_USER_AGENT =  os.environ['REDDIT_USER_AGENT']

# Subreddits to scan
SUBREDDITS = ["hardware", "nintendoswitch2", "gamingleaksandrumours", "intel", "amd", "rebubble", "singularity"]

def fetch_hot_posts_today(subreddits, limit=10):
    reddit = praw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
        user_agent=REDDIT_USER_AGENT
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
                    "Subreddit": subreddit_name,
                    "Post ID": post.id,
                    "Title": post.title,
                    "Score": post.score,
                    "URL": post.url,
                    "Comments Count": post.num_comments,
                    "Selftext": post.selftext,
                    "Posted UTC": post_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "Comments": []
                }

                # Limit comment expansion to just 1 level
                post.comments.replace_more(limit=1)
                for comment in post.comments[:5]:  # Grab first few root-level comments
                    post_data["Comments"].append({
                        "Comment ID": comment.id,
                        "Author": str(comment.author),
                        "Text": comment.body,
                        "Score": comment.score
                    })

                results.append(post_data)
    
    return results

def generate_html_report(data, filename="index.html"):
    html_content = """
    <html>
    <head>
        <title>Reddit Hot Posts Report</title>
        <style>
            table { width: 100%%; border-collapse: collapse; }
            th, td { border: 1px solid black; padding: 8px; text-align: left; }
            th { background-color: #f2f2f2; }
        </style>
    </head>
    <body>
        <h2>Reddit Hot Posts from Last 24 Hours</h2>
        <table>
            <tr>
                <th>Subreddit</th>
                <th>Title</th>
                <th>Score</th>
                <th>URL</th>
                <th>Comments Count</th>
                <th>Posted UTC</th>
                <th>Selftext</th>
                <th>Comments</th>
            </tr>
    """

    for post in data:
        comments_html = "<ul>"
        for comment in post["Comments"]:
            comments_html += f"<li><b>{comment['Author']} (Score: {comment['Score']}):</b> {comment['Text']}</li>"
        comments_html += "</ul>"

        html_content += f"""
            <tr>
                <td>{post["Subreddit"]}</td>
                <td>{post["Title"]}</td>
                <td>{post["Score"]}</td>
                <td><a href="{post["URL"]}">{post["URL"]}</a></td>
                <td>{post["Comments Count"]}</td>
                <td>{post["Posted UTC"]}</td>
                <td>{post["Selftext"][:500]}</td>
                <td>{comments_html}</td>
            </tr>
        """

    html_content += """
        </table>
    </body>
    </html>
    """

    with open(filename, "w", encoding="utf-8") as file:
        file.write(html_content)

if __name__ == "__main__":
    data = fetch_hot_posts_today(SUBREDDITS, limit=10)
    generate_html_report(data)
    print("Report saved as index.html")

