---
title: "杰理字体引擎：CJK判定、文字方向与自动换行"
date: 2026-04-13T17:08:16+08:00
categories: [系统与性能]
tags: [embedded, ui, c]
draft: false
---

## 怎么区分CJK和西文

核心原理是：每个字符在 Unicode 中都有唯一的编码（codepoint），不同文字系统占据不同的编码区段。

UTF-8 是一种变长编码：

| 范围 | 字节数 | 首字节 |
|---|---|---|
| ASCII (英文/数字) | 1 字节 | 0x00–0x7F |
| 拉丁扩展 (法/德/西等) | 2 字节 | 0xC0–0xDF |
| CJK / 泰语 / 韩语等 | 3 字节 | 0xE0–0xEF |
| Emoji / CJK 扩展B | 4 字节 | 0xF0–0xF7 |

先把UTF-8字节序列解码成Unicode codepoint，然后就可以这样来判定：

```c
static bool rtIsCJK(u32 cp){
    if(cp >= 0x2E80 && cp <= 0x9FFF) return true;   // CJK 部首/统一汉字/扩展A
    if(cp >= 0xAC00 && cp <= 0xD7AF) return true;   // 韩语音节
    if(cp >= 0xF900 && cp <= 0xFAFF) return true;   // CJK 兼容汉字
    if(cp >= 0xFE30 && cp <= 0xFE4F) return true;   // CJK 兼容形式
    if(cp >= 0xFF00 && cp <= 0xFFEF) return true;   // 全角字符
    if(cp >= 0x3000 && cp <= 0x303F) return true;   // CJK 标点
    if(cp >= 0x0E00 && cp <= 0x0E7F) return true;   // 泰语
    if(cp >= 0x20000 && cp <= 0x2A6DF) return true; // CJK 扩展B
    return false;
}
```

## 杰理如何处理文字方向

### 语言设置

根据不同的语言，需要为字体引擎设置不同方向：

```c
font_lang_set(UnicodeMixLeftword);   // 阿拉伯语/希伯来语 → 从右往左
font_lang_set(UnicodeMixRightword);  // 其余语言 → 从左往右
```

### 杰理SDK字体引擎

杰理的SDK提供了一个内置的字体引擎，提供了API如 `font_open` / `font_textout_utf8` / `font_text_width`，这个引擎是闭源的 .a 库文件。

字体引擎在初始化的时候根据语言不同选择不同的配置：

```c
.language_id = UnicodeMixLeftword,     // RTL 模式
.pixel.file.name = (char *)FONT_PATH"font.b",  // 使用同一个字库文件
// ...
.language_id = UnicodeMixRightword,    // LTR 模式
.pixel.file.name = (char *)FONT_PATH"font.b",  // 使用同一个字库文件
```

> RTL/LTR可以用同一个字库文件，方向差异不在字库里，在引擎的排版逻辑里。

## 杰理字体引擎工作流程

**0. 分配文本图像缓冲区**

```c
info->text_image_buf_size = info->text_image_stride * info->text_image_height;
info->text_image_buf = (u8*)calloc(1, info->text_image_buf_size);
```

**1. 调用 `font_text_out` 渲染一段文字**，传入参数包括字符串、图像缓冲区和文本框宽度等。

杰理的字体引擎在 `font_text_out` 内部做的事情大致是：

```
输入: "مرحبا Hello" (逻辑序：阿拉伯文在前，英文在后)

LTR 模式 (UnicodeMixRightword):
  光标从左开始 →
  逐字符放置，x 坐标递增

RTL 模式 (UnicodeMixLeftword):
  光标从右开始 ←
  阿拉伯文字符从右往左放置，x 坐标递减
  遇到拉丁文/数字，自动切换为局部 LTR（双向文本处理）
```

**2. 引擎通过回调 `platform_putchar` 逐个字符往缓冲区里写像素信息。**
- 引擎会处理 `\n` 换行（注意，不会处理文本框宽度自动换行）
- 像素数据是单色位图，具体格式取决于BPP

字库文件里存的就是每个字符的"模具"——一张小黑白图。比如字符 "H"，字库里就存了一张小图：

```
■ · · · · ■
■ · · · · ■
■ ■ ■ ■ ■ ■
■ · · · · ■
■ · · · · ■
```

`font_text_out` 做的事情是：查出每个字符对应的小图，算好放在哪儿，然后通过回调将小图一张张贴到画布（输出图像缓冲区）上。

## 文本框换行怎么做

杰理的字体引擎只会处理 `\n` 的硬换行，文本框宽度的换行需要我们自己实现。

一个实现方法是利用杰理提供的 `font_get_text_width`，这个函数可以计算一个字符串在屏幕上显示的宽高。

我们就可以通过逐渐增加字符来计算一行能显示的字符串，直到计算出一行能放下的最大值。举例：行宽限制 80px，西文：

```
第1次: "H"           → font_get_text_width → 8px  ≤ 80 ✓
第2次: "He"          → font_get_text_width → 15px ≤ 80 ✓
第3次: "Hel"         → font_get_text_width → 19px ≤ 80 ✓
第4次: "Hell"        → font_get_text_width → 23px ≤ 80 ✓
第5次: "Hello"       → font_get_text_width → 30px ≤ 80 ✓
第6次: "Hello "      → font_get_text_width → 34px ≤ 80 ✓  ← 空格，合法断点！
第7次: "Hello W"     → font_get_text_width → 42px ≤ 80 ✓
...
第N次: "Hello World" → font_get_text_width → 88px > 80 ✗ 超了！

→ 回退到上一个合法断点 "Hello " 断开
```

什么位置可以进行断行？这是混合策略：
- **西文**：空格、制表符、连字符（`-`）后面可以断 → 按词断
- **CJK**：每个字后面都可以断 → 按字断
- **例外**：下一个字符是避头标点（，。！等）时不能断 → 避免标点出现在行首
