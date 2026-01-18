# Hugo 快速入门指南

## 🚀 快速开始

### 1. 本地预览
```bash
hugo server -D
```
然后在浏览器中访问 http://localhost:1313

### 2. 创建新文章
```bash
hugo new posts/2026-01-19-my-new-post.md
```

编辑 `content/posts/2026-01-19-my-new-post.md`：
```yaml
---
title: "我的新文章"
date: 2026-01-19T10:00:00+08:00
tags: [标签1, 标签2]
draft: false  # 改为 false 发布文章
---

这里是文章内容...
```

### 3. 构建站点
```bash
hugo --gc --minify
```
生成的文件在 `public/` 目录

### 4. 部署到 GitHub Pages

只需推送到 GitHub：
```bash
git add .
git commit -m "Add new post"
git push origin main
```

GitHub Actions 会自动构建并部署！

## 📝 常用命令

| 命令 | 说明 |
|------|------|
| `hugo server` | 启动开发服务器 |
| `hugo server -D` | 启动开发服务器（包含草稿） |
| `hugo` | 构建站点 |
| `hugo --gc --minify` | 构建并优化站点 |
| `hugo new posts/xxx.md` | 创建新文章 |
| `hugo version` | 查看 Hugo 版本 |

## 📂 文件位置

- **文章**：`content/posts/`
- **页面**：`content/`（如 about.md）
- **图片**：`static/images/`
- **配置**：`hugo.toml`

## 🎨 主题自定义

编辑 `hugo.toml` 可以修改：
- 站点标题、描述
- 菜单导航
- 社交链接
- 代码高亮样式
- 显示选项

## 📖 更多帮助

详细信息请查看 [MIGRATION.md](MIGRATION.md)
