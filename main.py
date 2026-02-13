import os
import json
import requests
from anthropic import Anthropic
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime

# 環境変数から取得
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
INSTAGRAM_ACCESS_TOKEN = os.environ.get('INSTAGRAM_ACCESS_TOKEN')
INSTAGRAM_ACCOUNT_ID = os.environ.get('INSTAGRAM_ACCOUNT_ID')

def generate_content():
    """Claude APIで副業・物販コンテンツを生成"""
    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    
    prompt = """
    あなたは副業・物販のプロです。Instagramストーリーズ用の短いコンテンツを作成してください。
    
    テーマ：単発物販で副業を始める
    
    以下のカテゴリから1つ選んでコンテンツを作成：
    1. 物販の基礎知識
    2. 仕入れのコツ
    3. 販売戦略
    4. マインドセット
    5. 成功事例
    
    条件：
    - タイトル（10文字以内）
    - 本文（100文字以内）
    - 行動を促す一言（30文字以内）
    
    JSON形式で出力してください：
    {
        "title": "タイトル",
        "body": "本文",
        "cta": "行動を促す一言"
    }
    """
    
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )
    
    # レスポンスからJSONを抽出
    response_text = message.content[0].text
    # JSONブロックを抽出（```json ... ``` の形式に対応）
    if "```json" in response_text:
        json_text = response_text.split("```json")[1].split("```")[0].strip()
    elif "```" in response_text:
        json_text = response_text.split("```")[1].split("```")[0].strip()
    else:
        json_text = response_text.strip()
    
    content = json.loads(json_text)
    return content

def create_story_image(content):
    """テキストから画像を生成"""
    # 1080x1920 (Instagram Story サイズ)
    width, height = 1080, 1920
    
    # グラデーション背景を作成
    image = Image.new('RGB', (width, height))
    draw = ImageDraw.Draw(image)
    
    # シンプルなグラデーション（紫→ピンク）
    for y in range(height):
        r = int(138 + (255 - 138) * y / height)
        g = int(43 + (105 - 43) * y / height)
        b = int(226 + (180 - 226) * y / height)
        draw.rectangle([(0, y), (width, y+1)], fill=(r, g, b))
    
    # フォント設定（デフォルトフォント使用）
    try:
        title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 80)
        body_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 50)
        cta_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 45)
    except:
        title_font = ImageFont.load_default()
        body_font = ImageFont.load_default()
        cta_font = ImageFont.load_default()
    
    # タイトル
    title_bbox = draw.textbbox((0, 0), content['title'], font=title_font)
    title_width = title_bbox[2] - title_bbox[0]
    draw.text(((width - title_width) / 2, 300), content['title'], 
              fill='white', font=title_font)
    
    # 本文（改行対応）
    body_lines = []
    words = content['body']
    max_width = width - 200
    
    # 簡易的な改行処理
    current_line = ""
    for char in words:
        test_line = current_line + char
        bbox = draw.textbbox((0, 0), test_line, font=body_font)
        if bbox[2] - bbox[0] > max_width:
            body_lines.append(current_line)
            current_line = char
        else:
            current_line = test_line
    body_lines.append(current_line)
    
    y_offset = 600
    for line in body_lines:
        bbox = draw.textbbox((0, 0), line, font=body_font)
        line_width = bbox[2] - bbox[0]
        draw.text(((width - line_width) / 2, y_offset), line,
                  fill='white', font=body_font)
        y_offset += 80
    
    # CTA
    cta_bbox = draw.textbbox((0, 0), content['cta'], font=cta_font)
    cta_width = cta_bbox[2] - cta_bbox[0]
    draw.text(((width - cta_width) / 2, 1500), content['cta'],
              fill='#FFD700', font=cta_font)
    
    # 画像を保存
    image_path = 'story.jpg'
    image.save(image_path, 'JPEG', quality=95)
    return image_path

def upload_to_instagram(image_path):
    """Instagram Storiesに投稿"""
    # ステップ1: メディアをアップロード
    upload_url = f"https://graph.facebook.com/v18.0/{INSTAGRAM_ACCOUNT_ID}/media"
    
    with open(image_path, 'rb') as image_file:
        files = {'file': image_file}
        params = {
            'access_token': INSTAGRAM_ACCESS_TOKEN,
            'media_type': 'STORIES'
        }
        response = requests.post(upload_url, files=files, data=params)
    
    if response.status_code != 200:
        print(f"Upload Error: {response.text}")
        return False
    
    container_id = response.json()['id']
    
    # ステップ2: メディアを公開
    publish_url = f"https://graph.facebook.com/v18.0/{INSTAGRAM_ACCOUNT_ID}/media_publish"
    params = {
        'access_token': INSTAGRAM_ACCESS_TOKEN,
        'creation_id': container_id
    }
    response = requests.post(publish_url, data=params)
    
    if response.status_code == 200:
        print("✅ ストーリーズ投稿成功！")
        return True
    else:
        print(f"Publish Error: {response.text}")
        return False

def main():
    print("🚀 Instagram自動ストーリーズ開始...")
    
    # 1. コンテンツ生成
    print("📝 コンテンツ生成中...")
    content = generate_content()
    print(f"生成されたコンテンツ: {content}")
    
    # 2. 画像作成
    print("🎨 画像作成中...")
    image_path = create_story_image(content)
    print(f"画像作成完了: {image_path}")
    
    # 3. Instagram投稿
    print("📤 Instagram投稿中...")
    success = upload_to_instagram(image_path)
    
    if success:
        print("✅ すべて完了！")
    else:
        print("❌ 投稿に失敗しました")

if __name__ == "__main__":
    main()
