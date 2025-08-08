import os
import requests
import json

# 从 GitHub Secrets 获取环境变量
NOTION_API_KEY = os.getenv('NOTION_API_KEY')
NOTION_PAGE_ID = os.getenv('NOTION_PAGE_ID')
GIST_ID = os.getenv('GIST_ID')
GIST_TOKEN = os.getenv('GIST_TOKEN')

def get_notion_page_content():
    """从 Notion API 获取页面所有文本块内容"""
    url = f"https://api.notion.com/v1/blocks/{NOTION_PAGE_ID}/children"
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status() # 如果请求失败则抛出异常

    data = response.json()
    full_text = ""

    for block in data.get("results", []):
        if "type" in block and block["type"] in ["paragraph", "heading_1", "heading_2", "heading_3", "bulleted_list_item", "numbered_list_item", "to_do", "toggle"]:
            # 提取该类型 block 下的所有纯文本
            text_parts = block[block["type"]].get("rich_text", [])
            for part in text_parts:
                full_text += part.get("plain_text", "")
            full_text += "\n" # 每个 block 后换行

    return full_text

def update_gist(content):
    """更新 GitHub Gist 的内容"""
    url = f"https://api.github.com/gists/{GIST_ID}"
    headers = {
        "Authorization": f"Bearer {GIST_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }

    # 找到 Gist 中的第一个文件并更新其内容
    # 注意：你需要知道你的 Gist 中的文件名，这里假设是 'notion_content.txt'
    filename = "andrea_prompt.txt" # 确保这个文件名与你创建 Gist 时的一致

    data = {
        "files": {
            filename: {
                "content": content
            }
        }
    }

    response = requests.patch(url, headers=headers, data=json.dumps(data))
    response.raise_for_status()
    print(f"Gist updated successfully! Status code: {response.status_code}")

if __name__ == "__main__":
    print("Starting Notion to Gist sync...")
    try:
        notion_content = get_notion_page_content()
        if notion_content.strip(): # 确保有内容才更新
            update_gist(notion_content)
            print("Sync completed.")
        else:
            print("No content found in Notion page. Gist not updated.")
    except Exception as e:
        print(f"An error occurred: {e}")
        exit(1)
