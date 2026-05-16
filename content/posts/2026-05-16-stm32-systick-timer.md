---
title: "STM32 SysTick 笔记：LOAD/VAL/CTRL 与 udelay"
date: 2026-05-16T18:14:18+08:00
categories: [系统与性能]
tags: [embedded, c]
draft: false
---

## SysTick

SysTick 是 Cortex-M 内核内置的 24-bit 递减计数器，是 CPU 核心的一部分。

SysTick 包含三个核心寄存器：

```
┌─────────────────────────────────────────────────┐
│                   SysTick                        │
│                                                  │
│   ┌──────┐    ┌──────┐    ┌──────┐              │
│   │ LOAD │───►│  VAL │───►│ CTRL │              │
│   └──────┘    └──────┘    └──────┘              │
│       │           │           │                  │
│   重装载值     当前计数值    控制寄存器            │
│                                                  │
└─────────────────────────────────────────────────┘
```

### LOAD 重装载寄存器

设置计数器的初始值/上限值。当 VAL 减到 0 时，会触发中断，VAL 自动重新加载 LOAD 值。

如果更新了 LOAD 值，不会马上生效，只在下次重载的时候生效。

需要注意的是，因为计数是从 0 开始的，所以也要像计数器一样写入 `N - 1`。比如想要 1ms 的周期、时钟是 72MHz，那么应设置 `SysTick->LOAD = 72000 - 1`。

### VAL 当前值寄存器

存储当前计数值，每个时钟周期都会被自动减 1。

不管你往 VAL 里写入什么值，VAL 都会清零、清除 COUNTFLAG 标志，然后从 LOAD 重新装载。

```
时钟信号 ──► VAL = VAL - 1 ──► VAL == 0?
                                    │
                                是  │  否
                                    ▼
                            ┌───────────────┐
                            │ 触发中断       │
                            │ VAL = LOAD    │
                            │ 继续递减       │
                            └───────────────┘
```

### CTRL 控制寄存器

控制 SysTick 的工作模式。关键位：

| 位 | 名称 | 功能 |
|---|---|---|
| bit 0 | ENABLE | 使能 SysTick（1 = 启动） |
| bit 1 | TICKINT | 中断使能（1 = 溢出时产生中断） |
| bit 2 | CLKSOURCE | 时钟源选择（1 = CPU 时钟，0 = 外部时钟） |
| bit 16 | COUNTFLAG | 只读，VAL 减到 0 时置 1（读取后自动清零） |

常用配置：

```c
// 使用CPU时钟，开启中断，使能
SysTick->CTRL = SysTick_CTRL_CLKSOURCE_Msk |  // bit 2 = 1
                SysTick_CTRL_TICKINT_Msk   |  // bit 1 = 1
                SysTick_CTRL_ENABLE_Msk;      // bit 0 = 1
```

> **注**：STM32 默认使用 CPU 时钟，也就是内核时钟。

**禁用 / 启用 SysTick**：

```c
// 禁用
SysTick->CTRL &= ~SysTick_CTRL_ENABLE_Msk;

// 启用
SysTick->CTRL |= SysTick_CTRL_ENABLE_Msk;
```

## 工作流程

```
1. 初始化
   ├─ 设置 LOAD = 72000 - 1  （1ms 周期）
   ├─ 写 VAL = 任意值        （清零并重载 LOAD）
   └─ 设置 CTRL = 0x07       （使能 + 中断 + CPU 时钟）

2. 运行
   每个时钟周期:
   └─ VAL = VAL - 1
   
3. 溢出（VAL 减到 0）
   ├─ 触发 SysTick 中断
   ├─ VAL = LOAD（重载）
   └─ COUNTFLAG = 1

4. 中断服务函数
   └─ uwTick++  （HAL_IncTick()，累计毫秒数）
```

## HAL库用法

```c
// HAL初始化时自动调用
HAL_InitTick(TICK_INT_PRIORITY);  // 内部调用SysTick_Config()

// SysTick中断服务函数
void SysTick_Handler(void) {
    HAL_IncTick();  // uwTick++
    // 如果你想每1ms执行一个操作，可以在这里做，但注意一定要快，
    // 中断处理越短越好
}

// 获取系统运行时间（毫秒）
uint32_t tick = HAL_GetTick();  // 返回uwTick
```

> **注**：
> - HAL 库会自动配置 SysTick 为 1ms 中断。
> - `TICK_INT_PRIORITY` 的默认值在不同 STM32 系列、不同 HAL 版本里并不一致，CubeMX 会根据 NVIC 分组自动设置。如果项目里用了 RTOS 或对中断时序敏感，建议自己显式确认这个优先级，不要假设它一定是"最高"或"最低"。

## udelay

SysTick 是一个递减计数器，每个时钟周期减 1。我们可以通过计算经过了多少个时钟周期算出经过了多少时间。

```
72MHz 时钟 → 1 个时钟周期 = 1 / 72_000_000 秒 ≈ 13.9 ns
```

HAL 的默认配置是 1ms 中断一次，也就是 `SysTick->LOAD = 72000 - 1`，这意味着：`LOAD + 1 = 72000` 个时钟周期 = 1ms。

`SysTick->VAL` 每个时钟周期都会递减一次，所以 VAL 的变化量就是经过的周期数，可以利用这一点来实现计时。

但是计算不是简单的减法，因为要考虑溢出：

```
VAL: 71999 → 71998 → 71997 → ... → 2 → 1 → 0 → 71999 → 71998 → ...
                                       ↑
                                    溢出，重载 LOAD 值
```

举例：

```
t_old = 1000
t_now = 70000
看起来变小了？不，是溢出过：
VAL: 1000 → 999 → ... → 0 → 71999 → 71998 → ... → 70000
实际经过了：1000 → 0（1000 个周期）+ 0 → 71999 → 70000（1999 个周期）
差值 = 1000 + (72000 - 70000) = 1000 + 2000 = 3000
```

公式：

```
差值 = t_old + (LOAD + 1) - t_now
```

### 实现思路

```
开始 uDelay(n)
    ↓
计算目标周期数 = n × (LOAD + 1) / 1000   // n 是微秒数
    ↓
读取当前 VAL → t_old
    ↓
循环:
    读取 VAL → t_now
    ↓
    if t_old >= t_now:
        差值 = t_old - t_now        // 正常递减
    else:
        差值 = t_old + (LOAD + 1) - t_now  // 溢出情况
    ↓
    累加差值到 count
    t_old = t_now
    ↓
    count >= 目标周期数?
    ├── 否 → 继续循环
    └── 是 → 退出，延迟完成
```

### 完整实现

```c
void udelay(uint32_t us) {
    uint32_t load   = SysTick->LOAD;
    uint32_t target = us * (SystemCoreClock / 1000000);
    // 1 秒 = 1,000,000 微秒，这里算出 us 微秒对应几个时钟周期

    uint32_t t_old = SysTick->VAL;
    uint32_t count = 0;

    while (count < target) {
        uint32_t t_now = SysTick->VAL;
        // VAL 递减；若 t_old >= t_now，说明没溢出，普通减法
        // 若 t_old <  t_now，说明经过一次重载，按公式补一个重载周期
        uint32_t diff = (t_old >= t_now) ? (t_old - t_now)
                                         : (t_old + (load + 1) - t_now);
        count += diff;
        t_old  = t_now;
    }
}
```

### 局限性

差值公式只能区分"没溢出"和"溢出 1 次"两种情况，无法识别"溢出 ≥ 2 次"。如果两次循环之间被高优先级中断打断超过一个重载周期（默认 1ms），就会丢失一次溢出计数，导致延时偏短。

所以工程实践里：只要系统中所有高优先级 ISR 的执行时间 < 1ms，`udelay` 就是可靠的。如果系统里存在可能长时间占用 CPU 的中断（比如 SDIO、DMA、Flash 写入回调），就不要用这种基于 VAL 差分的方式做长延时，直接 `HAL_Delay()` 更稳。

> **注**：`target = us * (SystemCoreClock / 1000000)` 是 32 位乘法，`us` 太大会溢出。在 72MHz 下，`us` 不要超过约 6×10⁷（≈ 60 秒），实际项目里通常远小于这个值。
