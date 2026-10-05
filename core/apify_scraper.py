import asyncio
import os
from apify_client import ApifyClientAsync
from dotenv import load_dotenv

load_dotenv()

APIFY_API_KEY = os.getenv("APIFY_API_KEY")


async def fetch_linkedin_posts(linkedin_url):
    client = ApifyClientAsync(APIFY_API_KEY)
    post_list = []
    POST_LIMIT = 5

    run_input = {
        "urls": [linkedin_url],
        "limit": POST_LIMIT,
        "maxPosts": POST_LIMIT,
        "postsLimit": POST_LIMIT,
    }

    print("Starting Apify Actor...")
    run = await client.actor("supreme_coder/linkedin-post").call(
        run_input=run_input
    )

    print("\n--- Extracted LinkedIn Posts ---")

    dataset_id = run["defaultDatasetId"] if isinstance(run, dict) else run.default_dataset_id

    count = 0
    async for item in client.dataset(dataset_id).iterate_items():
        if count >= POST_LIMIT:
            break

        post_text = item.get("text") or item.get("content") or item.get("postText")
        if post_text:
            post_list.append(post_text)
            count += 1

    # Moved outside the loop so all posts are returned
    return post_list