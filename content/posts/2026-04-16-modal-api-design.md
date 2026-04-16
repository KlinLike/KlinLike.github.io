---
title: "主模式+参数：一种避免布尔爆炸的 API 设计"
date: 2026-04-16T16:45:34+08:00
categories: [软件工程]
tags: [api-design, ui]
draft: false
---

这是一种常见的软件工程设计，尤其在UI系统里，主要表现是：一个主模式+少量参数。

举个例子，在iOS `UILabel` 中有两个常用参数：
- `numberOfLines` - 最多显示几行
- `lineBreakMode` - 超出行数时怎么处理（截断、显示中间、省略等）

常见组合：

```
numberOfLines = 0 + byWordWrapping
=> 多行自动换行，不限制高度（详情页风格）

numberOfLines = 1 + byTruncatingTail
=> 单行尾部省略号（通知标题常见）

numberOfLines = 2 + byTruncatingTail
=> 两行预览，超出加 ...
```

这就是"主模式+少量参数"的体现：
- **主模式**：`lineBreakMode`（怎么溢出）
- **参数**：`numberOfLines`（限制多少）

## 如果不使用这种设计，会造成什么混乱？

如果不用这种设计，而改成一堆bool值，比如：

```
isSingleLine
isWrap
isClip
isEllipsis
isTruncateHead
isTruncateMiddle
isTruncateTail
```

会立刻出现4类混乱：

- **语义冲突**：`isWrap=true` 和 `isSingleLine=true` 同时开怎么办？`isEllipsis=true` 但 `isClip=false` 怎么解释？每个调用者理解都不同。

- **组合爆炸**：7 个布尔有 128 种组合，很多组合无意义或冲突，测试根本覆盖不完。

- **调用方难用**：业务代码到处写"先关这个再开那个"，迁移版本时特别容易漏改，出现"同样写法不同页面效果不一致"。

- **框架实现脆弱**：内部只能堆 if/else 判优先级，后续加一个新需求（比如 2 行省略）就可能破坏老逻辑。

而 `UILabel` 现在的设计把这些混乱直接消掉了：
- `numberOfLines` 管"最多几行"
- `lineBreakMode` 管"超出怎么处理"

两个正交维度各用一个字段，比七个互斥布尔清晰得多。设计 API 时，先问"有几个独立维度"，再决定用几个字段。

> **注**：正交维度指两个配置项互不影响、各管各的，任意组合都有意义（改行数不影响溢出策略，反之亦然）。互斥布尔指多个布尔值之间存在隐含冲突，同时只能有一个为 true（如 `isTruncateHead` / `isTruncateMiddle` / `isTruncateTail`），本质上是同一个维度的不同选项，应该用枚举而非布尔表达。
