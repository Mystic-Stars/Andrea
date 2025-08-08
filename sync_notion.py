import os
import requests
import json

# 从 GitHub Secrets 获取环境变量
NOTION_API_KEY = os.getenv('NOTION_API_KEY')
NOTION_PAGE_ID = os.getenv('NOTION_PAGE_ID')
GIST_ID = os.getenv('GIST_ID')
GIST_TOKEN = os.getenv('GIST_TOKEN')

# 定义请求头，后续重复使用
HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

def get_block_children_recursive(block_id):
    """
    递归函数，用于获取一个 block 下的所有子 block 内容。
    这是解决同步区块问题的关键。
    """
    all_text = ""
    url = f"https://api.notion.com/v1/blocks/{block_id}/children"
    
    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        data = response.json()

        for block in data.get("results", []):
            # 1. 如果是同步区块，则获取其源头区块的内容
            if block['type'] == 'synced_block':
                # 检查 synced_from 是否为 None，如果是 None，说明这是原始区块
                synced_from = block['synced_block']['synced_from']
                source_block_id = block['id'] if synced_from is None else synced_from['block_id']
                all_text += get_block_children_recursive(source_block_id)

            # 2. 如果是其他包含文本的区块，直接提取文本
            elif block['type'] in ["paragraph", "heading_1", "heading_2", "heading_3", "bulleted_list_item", "numbered_list_item", "to_do", "toggle", "quote", "callout"]:
                text_parts = block[block['type']].get("rich_text", [])
                for part in text_parts:
                    all_text += part.get("plain_text", "")
                all_text += "\n"

    except requests.HTTPError as e:
        print(f"Error fetching block children for {block_id}: {e}")
        # 即使某个 block 获取失败，也继续执行
        
    return all_text


def get_notion_page_content():
    """主函数，从顶层页面开始获取内容"""
    return get_block_children_recursive(NOTION_PAGE_ID)


def update_gist(content):
    """更新 GitHub Gist 的内容"""
    url = f"https://api.github.com/gists/{GIST_ID}"
    gist_headers = {
        "Authorization": f"Bearer {GIST_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    # ------------------------------------------------------------------
    # 重要：请将这里的文件名修改为您 Gist 中的实际文件名！
    # ------------------------------------------------------------------
    filename = "andrea_prompt.txt" 
    
    data = {
        "files": {
            filename: {
                "content": content if content.strip() else " " # 如果内容为空，则传入一个空格以避免删除文件
            }
        }
    }
    
    response = requests.patch(url, headers=gist_headers, data=json.dumps(data))
    response.raise_for_status()
    print(f"Gist updated successfully! Status code: {response.status_code}")


if __name__ == "__main__":
    print("Starting Notion to Gist sync...")
    try:
        notion_content = get_notion_page_content()
        if notion_content:
            print(f"Successfully fetched {len(notion_content)} characters from Notion.")
            update_gist(notion_content)
            print("Sync completed.")
        else:
            print("No content found or fetched from Notion page. Updating Gist with empty content.")
            update_gist("") # 如果 Notion 页面为空，也同步空内容到 Gist
            
    except Exception as e:
        print(f"An error occurred: {e}")
        exit(1)
