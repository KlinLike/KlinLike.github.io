#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# --- new_post.py (Hugo 版本) ---
# 为 Hugo 博客快速创建一篇使用北京 (+0800) 时区的新文章模板

import os
from datetime import datetime, timedelta, timezone

def create_hugo_post_template():
    """
    非交互式地创建一篇新的 Hugo 博客文章模板。
    """
    # 1. 设置时区为北京时间 (UTC+8)
    beijing_tz = timezone(timedelta(hours=8))

    # 2. 获取当前北京时间
    now = datetime.now(beijing_tz)
    current_date = now.strftime('%Y-%m-%d')
    # Hugo 使用 ISO 8601 格式：YYYY-MM-DDTHH:MM:SS+08:00
    full_timestamp = now.strftime('%Y-%m-%dT%H:%M:%S+08:00')

    # 3. 定义占位符和文件名
    category = "uncategorized"
    slug = "new-post"
    
    # 确保 content/posts 目录存在
    posts_dir = 'content/posts'
    if not os.path.exists(posts_dir):
        os.makedirs(posts_dir)
    filename = os.path.join(posts_dir, f"{current_date}-{category}-{slug}.md")

    # 4. 定义 Hugo Front Matter 模板
    template = f"""---
title: "🌱🌳TITLE"
date: {full_timestamp}
tags: [TAG1, TAG2]
draft: false
---

"""

    # 5. 创建并写入文件
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(template)
        print(f"[OK] 成功创建新文章模板: {filename}")
        print("     请修改文件中的 TITLE, TAG1, TAG2 并开始写作。")
        print(f"     本地预览: http://localhost:1313/posts/{current_date}-{category}-{slug}/")
    except IOError as e:
        print(f"[ERROR] 创建文件时出错: {e}")

if __name__ == '__main__':
    create_hugo_post_template()
