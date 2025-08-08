import os
import requests
import json

# 从 GitHub Secrets 获取环境变量
NOTION_API_KEY = os.getenv('NOTION_API_KEY')
NOTION_PAGE_ID = os.getenv('NOTION_PAGE_ID')
GIST_ID = os.getenv('GIST_ID')
GIST_TOKEN = os.getenv('GIST_TOKEN')

# 定义请求头
HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

def rich_text_to_markdown(rich_text_array):
    """
    将 Notion 的 rich_text 数组转换为 Markdown 字符串。
    支持：加粗、斜体、删除线、行内代码、链接。
    """
    md_string = ""
    for part in rich_text_array:
        content = part.get("plain_text", "")
        annotations = part.get("annotations", {})
        
        if annotations.get("bold"):
            content = f"**{content}**"
        if annotations.get("italic"):
            content = f"*{content}*"
        if annotations.get("strikethrough"):
            content = f"~~{content}~~"
        if annotations.get("code"):
            content = f"`{content}`"
            
        if part.get("href"):
            content = f"[{content}]({part.get('href')})"
            
        md_string += content
    return md_string

def block_to_markdown_recursive(block_id):
    """
    递归函数，将 block 及其子 block 转换为 Markdown。
    核心升级：1. 支持分页。 2. 转换为 Markdown。
    """
    all_markdown = ""
    start_cursor = None
    
    while True: # 循环处理分页
        params = {}
        if start_cursor:
            params['start_cursor'] = start_cursor
            
        url = f"https://api.notion.com/v1/blocks/{block_id}/children"
        response = requests.get(url, headers=HEADERS, params=params)
        
        if not response.ok:
            print(f"Error fetching block children for {block_id}: {response.status_code} - {response.text}")
            break

        data = response.json()

        for block in data.get("results", []):
            block_type = block.get("type")
            
            # --- 区块类型到 Markdown 的转换 ---
            if block_type == 'paragraph':
                rich_text = block.get("paragraph", {}).get("rich_text", [])
                if rich_text: # 避免空段落产生多余换行
                    all_markdown += rich_text_to_markdown(rich_text) + "\n\n"
            elif block_type == 'heading_1':
                all_markdown += f"# {rich_text_to_markdown(block['heading_1']['rich_text'])}\n\n"
            elif block_type == 'heading_2':
                all_markdown += f"## {rich_text_to_markdown(block['heading_2']['rich_text'])}\n\n"
            elif block_type == 'heading_3':
                all_markdown += f"### {rich_text_to_markdown(block['heading_3']['rich_text'])}\n\n"
            elif block_type == 'bulleted_list_item':
                all_markdown += f"- {rich_text_to_markdown(block['bulleted_list_item']['rich_text'])}\n"
            elif block_type == 'numbered_list_item':
                all_markdown += f"1. {rich_text_to_markdown(block['numbered_list_item']['rich_text'])}\n"
            elif block_type == 'to_do':
                checked = block['to_do']['checked']
                prefix = "- [x]" if checked else "- [ ]"
                all_markdown += f"{prefix} {rich_text_to_markdown(block['to_do']['rich_text'])}\n"
            elif block_type == 'quote':
                all_markdown += f"> {rich_text_to_markdown(block['quote']['rich_text'])}\n\n"
            elif block_type == 'code':
                language = block['code']['language']
                code_text = rich_text_to_markdown(block['code']['rich_text'])
                all_markdown += f"```{language}\n{code_text}\n```\n\n"
            elif block_type == 'divider':
                all_markdown += "---\n\n"
            elif block_type == 'image':
                img_url = block.get('image', {}).get('file', {}).get('url', '')
                if img_url:
                    all_markdown += f"![image]({img_url})\n\n"
            elif block_type == 'synced_block':
                synced_from = block['synced_block']['synced_from']
                source_id = block['id'] if synced_from is None else synced_from['block_id']
                all_markdown += block_to_markdown_recursive(source_id)
        
        # 处理分页
        if data.get("has_more"):
            start_cursor = data.get("next_cursor")
        else:
            break
            
    return all_markdown

def update_gist(content):
    """更新 GitHub Gist 的内容"""
    url = f"https://api.github.com/gists/{GIST_ID}"
    gist_headers = {
        "Authorization": f"Bearer {GIST_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    # 建议：将文件名改为 .md 后缀，以便更好地被识别为 Markdown 文件
    filename = "andrea_prompt.md" # 您可以根据需要修改
    
    data = {
        "files": {
            filename: {
                "content": content if content.strip() else " "
            }
        }
    }
    
    response = requests.patch(url, headers=gist_headers, data=json.dumps(data))
    response.raise_for_status()
    print(f"Gist updated successfully! Status code: {response.status_code}")

if __name__ == "__main__":
    print("Starting Notion to Gist sync (Markdown Edition)...")
    try:
        markdown_content = block_to_markdown_recursive(NOTION_PAGE_ID)
        if markdown_content:
            print(f"Successfully fetched and converted {len(markdown_content)} characters to Markdown.")
            update_gist(markdown_content)
            print("Sync completed.")
        else:
            print("No content found or fetched from Notion page. Updating Gist with empty content.")
            update_gist("")
            
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
