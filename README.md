博客仓库基于 [Jekyll](https://jekyllrb.com/) 构建，并由 [GitHub Pages](https://pages.github.com/) 托管。

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
5.  如果是只涉及一个点的文章，就用🌱标签；如果是设计面的文章，就用🌳标签。

### 2. 添加图片

1.  将图片文件统一放置在 `assets/images` 文件夹下。如果该文件夹不存在，请手动创建。
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
