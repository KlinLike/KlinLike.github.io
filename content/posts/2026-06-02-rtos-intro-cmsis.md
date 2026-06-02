---
title: "初识RTOS：任务创建与内存分配"
date: 2026-06-02T19:53:41+08:00
categories: [系统与性能]
tags: [embedded, rtos, memory]
draft: false
---

## 背景：为什么需要RTOS

在裸机编程中，只有一个主循环。如果想同时做两件事，就只能在一个循环里交替执行，代码耦合度高，扩展困难。

RTOS（实时操作系统）将CPU时间切成小片段，轮流分配给不同任务。宏观上看，多个任务"同时"执行；微观上看，它们仍然是交替执行的。

## CMSIS-OS：统一的RTOS接口层

不同的RTOS有不同的API：FreeRTOS用`xTaskCreate`，RT-Thread用`rt_thread_create`。如果代码直接使用某个RTOS的原生API，迁移到另一个RTOS时就需要改动所有调用，维护成本很高。

为此，ARM提供了**CMSIS-OS**——一套中间抽象层，对上提供统一接口，对下适配不同RTOS：

```
┌─────────────────────────────────┐
│       你的应用程序代码           │
│    osThreadNew() 统一接口        │
├─────────────────────────────────┤
│         CMSIS-OS 封装层          │
│    自动适配底层 RTOS API         │
├─────────────────────────────────┤
│  FreeRTOS  │ RT-Thread │ uC/OS  │
│ xTaskCreate│rt_thread_ │OSTask_ │
│            │  create   │ Create │
└─────────────────────────────────┘
```

使用CMSIS-OS创建任务的代码如下：

```c
osThreadId_t taskHandle;
taskHandle = osThreadNew(TaskA, NULL, &task_attributes);
```

CMSIS-OS通过条件编译来决定底层调用哪个RTOS的API，例如：

```c
#define USE_FREERTOS 1
```

在CubeMX中创建工程时，可以在**Middleware**配置中选择FreeRTOS，CubeMX会自动完成CMSIS-OS的适配工作。

## 动态分配与静态分配

动态分配和静态分配指的是：创建任务时，任务所需的内存（**栈空间**和**任务控制块TCB**）从哪里来。

### 动态分配

系统在运行时从**堆（Heap）**中自动分配内存。

- **优点**：使用简单，不需要预先计算内存大小，适合原型开发
- **缺点**：堆内存不足时创建可能失败，存在堆碎片化风险，稳定性稍差

### 静态分配

用户在代码中预先定义好内存空间，创建任务时传入这些预分配的内存地址。

- **优点**：内存来源确定，不依赖堆，绝对可靠
- **缺点**：需要预先计算内存大小，代码更复杂

静态分配更适合对确定性要求高的场景，如医疗设备、航空航天系统。
