# 我的个人博客

这是我的个人博客仓库，基于 [Jekyll](https://jekyllrb.com/) 构建，并由 [GitHub Pages](https://pages.github.com/) 托管。

## 环境设置

在开始之前，请确保你的本地开发环境已经安装了以下软件：

1.  **Ruby**: [下载并安装 Ruby+Devkit](https://rubyinstaller.org/downloads/)
2.  **Bundler**: 一个 Ruby 的依赖管理工具。安装 Ruby 后，在命令行中运行：
    ```bash
    gem install bundler
    ```
3.  **安装项目依赖**: 在本仓库的根目录（即此 `README.md` 文件所在的目录）下运行以下命令，它会根据 `Gemfile` 文件安装所有必需的组件（如 Jekyll 本身、主题等）。
    ```bash
    bundle install
    ```

## 如何使用

### 1. 创建一篇新文章

所有的文章都存放在 `_posts` 文件夹中。要创建一篇新文章，请遵循以下步骤：

1.  在 `_posts` 文件夹内创建一个新文件。
2.  文件名必须遵循 Jekyll 的标准格式：`YYYY-MM-DD-your-post-title.md`。
    * 例如：`2025-08-15-my-first-post.md`
3.  在文件的最上方，必须包含 "Front Matter"（文件头），用于定义文章的元数据。这是一个基本的模板：

    ```yaml
    ---
    layout: post
    title:  "你的文章标题"
    date:   2025-08-15 10:30:00 +0800
    tags: [tag1, tag2]
    ---
    ```
    * `title`: 文章的标题。
    * `date`: 文章的发布日期和时间。请确保格式正确，`+0800` 代表东八区时间。
    * `tags`: 文章的标签，方便分类和检索。

4.  在文件头下方，使用 Markdown 语法撰写你的文章正文。

### 2. 添加图片

1.  将你的图片文件（如 `.png`, `.jpg` 等）统一放置在 `assets/images` 文件夹下。如果该文件夹不存在，请手动创建。
2.  在 Markdown 文章中，使用以下格式来引用图片：

    ```markdown
    ![这里是图片的描述]({{ site.baseurl }}/assets/images/你的图片文件名.png)
    ```
    * **示例**: `![运行结果图]({{ site.baseurl }}/assets/images/2025-01-20-socket-programming-basics-4.png)`
    * **注意**: 使用 `{{ site.baseurl }}` 是最佳实践，Jekyll 会在生成网站时自动将其替换为正确的路径前缀，确保图片在本地预览和线上部署后都能正确显示。

### 3. 本地运行与调试

在发布到线上之前，你可以在本地预览网站的效果。

1.  打开你的命令行工具，并确保当前路径位于博客仓库的根目录。
2.  运行以下命令：

    ```bash
    bundle exec jekyll serve
    ```
    * 这个命令会启动一个本地的 web 服务器。
    * `bundle exec` 确保了你使用的是在 `Gemfile.lock` 中定义的、与项目完全匹配的 Jekyll 版本，避免了潜在的依赖冲突。

3.  服务器启动后，在浏览器中打开 `http://127.0.0.1:4000` 即可看到你的博客。
4.  在你保存了对文章的任何修改后，Jekyll 会自动重新生成网站，你只需刷新浏览器即可看到最新的效果。

### 4. 发布博客

你的博客托管在 GitHub Pages 上，发布过程非常简单：

1.  将你的所有改动（包括新文章、新图片等）提交到 Git。

    ```bash
    # 添加所有改动
    git add .

    # 创建一个提交记录
    git commit -m "新增文章：你的文章标题"

    # 推送到 GitHub
    git push
    ```

2.  推送完成后，GitHub Pages 会自动为你重新构建和部署网站。通常等待一到两分钟后，你就可以在你的线上博客地址看到更新了。

---

## 技术延伸：Jekyll 是如何工作的？

* **静态站点生成器 (Static Site Generator, SSG)**: Jekyll 是一个典型的 SSG。它与 WordPress 这类动态网站（需要数据库和后端语言实时生成页面）不同。Jekyll 会在**构建时**读取你的所有源文件（`.md` 文件、`_layouts` 里的 HTML 模板、`assets` 里的资源等），然后将它们编译成一个完整的、由纯 HTML/CSS/JS 组成的**静态网站**。

* **工作流程**:
    1.  **读取**: Jekyll 读取 `_config.yml` 配置文件、`_posts` 目录下的文章、`_layouts` 目录下的布局模板等。
    2.  **解析与转换**: 它使用 Markdown 转换器（如 kramdown）将 `.md` 文件转换成 HTML 片段。同时，它会解析文件头（Front Matter）中的元数据。
    3.  **渲染**: Jekyll 使用名为 **Liquid** 的模板引擎。你在图片链接中使用的 `{{ site.baseurl }}` 就是 Liquid 的语法。它会将转换后的 HTML 内容片段嵌入到指定的布局模板 (`layout: post`) 中，并替换掉所有 Liquid 变量和逻辑，最终生成完整的 HTML 页面。
    4.  **输出**: 所有生成的静态文件（HTML, CSS, JS, 图片等）被统一输出到 `_site` 文件夹中。这个文件夹就是你博客的最终形态。

* **框架的设计思想**: Jekyll 遵循“**约定优于配置 (Convention over Configuration)**”的原则。这意味着只要你遵循它的约定（如 `_posts` 文件夹结构、文件名格式），很多事情它都会自动帮你处理好，无需复杂的配置。这是一种能极大提高开发效率的框架设计模式。

当你运行 `bundle exec jekyll serve` 时，就是在本地完整地执行了上述流程，并将 `_site` 文件夹的内容通过一个小型服务器呈现给你。而当你 `git push` 到 GitHub 时，GitHub Pages 的服务器也在云端为你执行了完全相同的流程。