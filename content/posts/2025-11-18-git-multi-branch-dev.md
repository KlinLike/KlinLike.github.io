---
title: "Git如何使用多分支进行开发"
date: 2025-11-18T10:02:16+08:00
categories: [工具与流程]
tags: [git, workflow]
---

如果希望善用AI辅助开发，对多分支的使用是很有帮助的，因为这样可以**保存有效的代码修改**，也能**避免AI犯傻对已开发好的功能进行破坏**。

---

## Stage 1：本地开发

### 1. 开分支

```bash
git checkout -b feature/new-feat
```

### 2. 疯狂提交

每当AI做出一个成功的修改，就提交一个 commit：

```bash
git add .
git commit -m "fix: fix a bug"
```

**⚠️ 注意**：不要 push 这些临时的 commit，只要不 push，无论怎么 rebase，都不会干扰到别人。

---

## Stage 2：同步主干

当 master 有更新时，有两个选择可以保持同步，避免 feature 分支与主干差异过大，导致后续合并困难。

### 方案一：merge（推荐）

```bash
git merge master
```

**优点**：不会改写历史  
**缺点**：历史会变丑（但这个缺点可以忽略，因为最终 push 前我们可以合并整理 commit）。

运行这个指令会在分支上创建一个 Merge commit。

### 方案二：rebase

```bash
git rebase master
```

如果能确定**没有 push 过这个分支**，可以用 rebase 来保持分支的整洁。

---

## Stage 3：合并提交

在完成了所有开发，分支也用 merge / rebase 合并了最新的主干代码，解决了所有冲突后，就可以进行 commit 整理了。

### 交互式 rebase

执行以下命令后，会打开编辑器，列出所有 commit：

```bash
git rebase -i master
```

编辑器显示内容：

```
pick 1a2b3c wip: step 1
pick 4d5e6f fix: typo
pick 7a8b9c wip: ai gen module A
pick 1d2e3f Merge remote-tracking branch ...
pick 4a5b6c wip: step 2
pick 7d8e9f feat: add class B
pick 1a2b3d Merge remote-tracking branch ...
pick 4d5e6e fix: final bug
```

### 修改操作指令

可以把开头的 `pick` 修改成 `s` 或 `f`：

- **s (squash)**：压缩，它会把这个 commit 合并到上一个 commit，并让你重新编辑 commit message
- **f (fixup)**：同上，但它会丢弃这个 commit 的 message

将除第一行外的所有 `pick` 都改成 `f`，这样最终只保留第一个 commit，其他都合并进去：

```
pick 1a2b3c wip: step 1
f 4d5e6f fix: typo
f 7a8b9c wip: ai gen module A
f 1d2e3f Merge remote-tracking branch ...
f 4a5b6c wip: step 2
f 7d8e9f feat: add class B
f 1a2b3d Merge remote-tracking branch ...
f 4d5e6e fix: final bug
```

### 完成整理

保存修改，然后退出，之后就可以编写最终的 commit 了，这时候你可以针对这一整个分支的提交编写一个清晰的 commit。

整理完成后，这个分支就只剩下干净的 commit。如果这是首次 push，直接推送即可；如果之前已经 push 过，需要使用 force push：

```bash
# 首次 push
git push origin feature/new-feat

# 已 push 过的分支（需要 force push）
git push --force-with-lease origin feature/new-feat
```

**⚠️ 重要提示**：如果一个分支被 push 过后再执行 rebase，会导致远程仓库的该feature分支历史被重写，对其他团队成员造成干扰。
