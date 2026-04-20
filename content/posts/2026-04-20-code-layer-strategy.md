---
title: "Keil项目代码分层策略"
date: 2026-04-20T20:00:52+08:00
categories: [软件工程]
tags: [architecture, embedded]
draft: false
---

怎么判断一个代码文件应该被放在Driver层还是App层？

可以问两个问题：

**1. 它会不会include更低层次的东西？** 比如 `printf`、业务配置
- **会** → 这个文件应该被归到App层
- **不会** → 这个文件可能是Driver或Middleware层

**2. 把它原样拷到另一个完全不同的项目，能用吗？**
- **能** → 这个文件是Driver或Middleware层
- **不能** → App层，因为这说明耦合了太多业务了

我目前用的Keil项目分层策略：

| 层级 | 职责 | 示例 |
|---|---|---|
| Core | CubeMX自动生成 | |
| Middlewares | 硬件无关的通用算法 | `queue.c` |
| Driver | 绑定某颗硬件芯片/外设的代码，只要硬件相同就能复用 | `STM32F1xx_HAL_Driver` |
| App | 产品/业务相关的代码 | `clock.c` |
