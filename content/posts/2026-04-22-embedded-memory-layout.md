---
title: "嵌入式内存布局：data、bss 与 rodata 段"
date: 2026-04-22T20:30:50+08:00
categories: [系统与性能]
tags: [embedded, memory, c]
draft: false
---

## data段

data段存放有初始值的全局/静态变量，它在 Flash 和 RAM 中各有一份。

**启动前**，初始值保存在 Flash 中：

```
Flash 中的 data 段：
config = 100
```

**启动时**，启动代码（通常是 `Reset_Handler`）将 Flash 中 data 段的初始值复制到 RAM 对应位置：

```
RAM:
┌─────────────────┐
│ data段          │ ← 从 Flash 复制过来的 "100"
│ config = 100    │
├─────────────────┤
│ bss段 (清零)    │
├─────────────────┤
│ heap            │
├─────────────────┤
│ stack           │
└─────────────────┘
```

**运行时**，程序读写的是 RAM 中的副本：

```c
config = 200;  // 修改的是 RAM 中的值，Flash 中的初始值不变
```

**为什么需要两份？** RAM 掉电丢失，所以初始值要保存到能持久化的 Flash 中；运行时需要读写，而 Flash 速度慢还有写入寿命限制，所以启动后要加载到 RAM。

## bss段

和 data 段相比，bss 段存放的是未初始化（或显式初始化为 0）的全局/静态变量：

```c
int config;  // bss段，未初始化
```

- 没有初始值，不需要在 Flash 中存一份
- 启动代码直接在 RAM 中清零即可

所以 bss 段只占用 RAM，不占 Flash。

## rodata段

rodata（read-only data）段存放只读常量，比如字符串字面量、`const` 全局变量等。它只保留在 Flash 中，运行时直接从 Flash 读取，不复制到 RAM，利用了 Flash 空间大和只读的特性，可以有效节省 RAM。

## 代码中如何体现

一个变量最终落在哪个段，取决于它的初始化方式和作用域：

```c
int global;         // bss（未初始化全局变量）
static int file;    // bss（未初始化静态变量，和 global 同段，只是可见性不同）

void func() {
    int local;      // stack（局部变量）
    static int s;   // bss（静态局部变量，生命周期是全局的）
}
```

> **注**：`static` 限制的是可见性，不改变存储位置。`global` 和 `file` 都在 bss 段，区别仅在于 `file` 只对当前文件可见。

## 总结

| 段 | Flash | RAM | 特点 |
|---|---|---|---|
| data | ✅ | ✅ | 有初始值，双份占用 |
| bss | ❌ | ✅ | 无初始值，仅 RAM |
| rodata | ✅ | ❌ | 只读常量，仅 Flash |
