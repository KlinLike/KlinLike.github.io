---
title: "如何避免框架开发中的笛卡尔积爆炸"
date: 2026-05-08T18:21:02+08:00
categories: [软件工程]
tags: [api-design, software-engineering, embedded]
draft: false
---

假如一个对象有多个维度，就会有非常多的变体，如果增加接口的时候不克制，就会出现接口数量爆炸的情况，举个例子：

```c
// 基础按钮
Button* addButton(Page* p, s16 x, s16 y, s16 w, s16 h, const char* text, void(*onClick)(Button*));
// 带图标
Button* addButtonIcon(Page* p, s16 x, s16 y, s16 w, s16 h, const ImgRes* icon, const char* text, void(*onClick)(Button*));
// 带圆角+颜色
Button* addButtonRound(Page* p, s16 x, s16 y, s16 w, s16 h, u16 color, u8 radius, const char* text, void(*onClick)(Button*));
// 带图标+圆角
Button* addButtonIconRound(Page* p, s16 x, s16 y, s16 w, s16 h, const ImgRes* icon, u16 color, u8 radius, const char* text, void(*onClick)(Button*));
// 带长按
Button* addButtonLongPress(Page* p, s16 x, s16 y, s16 w, s16 h, const char* text, void(*onClick)(Button*), void(*onLong)(Button*));
// 带图标+长按
Button* addButtonIconLongPress(Page* p, ...);
// 带禁用态
Button* addButtonDisable(Page* p, ...);
// ...无穷无尽
```

这就是笛卡尔积爆炸，也叫变体爆炸。在长期维护的项目中，如果不克制地处理，这种情况很容易在不知不觉中出现，给维护带来巨大的压力。

## 如何处理

### 分层API

分层式 API 设计是很直觉的解决思路：先提供一个克制的、带有大量默认值的基础API，覆盖大多数场景；再提供一个带完整 config 结构体的扩展API，覆盖剩余场景。比如：

**基础 API**：

```c
Button* addButton(Page* p, s16 x, s16 y, const char* text, void(*onClick)(Button*));
```

**完全体 API**：

```c
typedef struct {
    s16 w, h;              // 0 = 自动计算
    u16 bgColor;           // 0 = 透明
    u8  radius;            // 0 = 直角
    const ImgRes* icon;    // NULL = 无图标
    u16 textColor;         // 0 = 白色(默认)
    bool disabled;         // false
    bool toggle;           // false = 普通按钮
    void(*onLongPress)(Button*);  // NULL = 不响应长按
} ButtonCfg;

Button* addButtonEx(Page* p, s16 x, s16 y, const char* text,
                    void(*onClick)(Button*), const ButtonCfg* cfg);
```

这个模式也非常适合嵌入式环境。

完全体 API 结构体可能太复杂，我们可以提供一些预设：

```c
// 内置几种 preset
extern const ButtonCfg BTN_PRESET_PLAIN;     // 纯色无圆角
extern const ButtonCfg BTN_PRESET_CARD;      // 卡片风格（圆角+背景色）
extern const ButtonCfg BTN_PRESET_DANGER;    // 警示风格（红底白字）

// 调用者基于 preset 微调
ButtonCfg cfg = BTN_PRESET_CARD;
cfg.icon = &iconSave;
cfg.onLongPress = onSaveLong;
Button* btn = addButtonEx(page, 10, 20, "保存", onSave, &cfg);
```

### Builder 模式

```c
Button* btn = button_create(page, "保存", onSave)
    ->pos(10, 20)
    ->size(120, 48)
    ->background(0x1E90, 12)
    ->icon(&iconSave)
    ->onLongPress(onSaveLong)
    ->disabled(false)
    ->build();
```

可读性强，顺序无关，IDE 自动补全方便，不过略笨重，内存敏感的时候可能会有性能压力。
主要压力来自：

1. **函数调用链**：每个链式 setter 都是一次调用，热点路径里会累计开销。
2. **构建期临时变量**：部分实现会引入临时状态或中间数据（是否发生取决于实现）。
3. **代码体积增长**：如果每个 setter 都独立实现，Flash/指令缓存压力会变大。
4. **延迟构建的参数缓存**：若采用先收集参数再 `build()`，保存参数需要额外内存。

### 先创建后配置

```c
Button* btn = button_new(page, "保存", onSave);
button_set_pos(btn, 10, 20);
button_set_size(btn, 120, 48);
button_set_background(btn, 0x1E90, 12);
button_set_icon(btn, &iconSave);
button_set_on_long_press(btn, onSaveLong);
button_commit(btn);  // 配置完成，开始渲染
```

API 扁平，可以随时增加新的 setter，但是代码行数很多，而且中间状态对象可能不合法。

## 小结

- **分层 API + Cfg + Preset**：嵌入式最常用，便宜、可读、易扩展
- **Builder**：可读性最佳，代价是更多临时分配与方法调用
- **先创建后配置**：扩展性最强，代价是行数多、存在中间不合法状态

核心原则只有一句：**不要让维度数量决定接口数量**，而要让一个接口接受多维度。
