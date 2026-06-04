---
title: "FreeRTOS的堆管理"
date: 2026-06-04T19:43:47+08:00
categories: [系统与性能]
tags: [embedded, rtos, memory]
draft: false
---

## FreeRTOS的堆是什么

FreeRTOS的堆实际上就是一个**静态数组**，大小由`FreeRTOSConfig.h`中的`configTOTAL_HEAP_SIZE`宏决定。如果定义的值超出芯片可用RAM，编译时会报错。

## 5种Heap方案对比

| 方案 | 特点 | 适用场景 | 使用频率 |
|------|------|----------|----------|
| heap_1 | 只分配，不回收 | 所有任务永久运行，从不删除 | 很少 |
| heap_2 | 可分配可释放，但不合并相邻空闲块 | 固定大小分配 | 很少 |
| heap_3 | 封装标准库`malloc`/`free` | — | 基本不用（嵌入式一般不依赖标准库） |
| heap_4 | 可分配可释放，自动合并相邻空闲块 | 最常用 | **推荐** |
| heap_5 | 支持多段不连续内存 | 有外部RAM等多块内存的硬件 | 特殊场景 |

heap_2释放内存后不会合并相邻的空闲块，长期运行会导致严重的内存碎片。heap_4改进了这一点，释放时会自动合并相邻空闲块，因此是最常用的方案。

如果硬件上有多块不连续内存（如片内RAM + 外扩RAM），就需要使用heap_5。

## 内存管理辅助函数

- `xPortGetFreeHeapSize()`：获取当前剩余空闲堆大小（所有未分配字节的总和）
- `xPortGetMinimumEverFreeHeapSize()`：获取运行以来空闲堆的**历史最小值**，用来判断堆大小是否够用

让程序跑一段时间后调用`xPortGetMinimumEverFreeHeapSize()`，如果返回值只剩个位数或十位数字节，说明堆空间很紧张，需要调大`configTOTAL_HEAP_SIZE`。

当`pvPortMalloc`分配失败时，会触发钩子函数`vApplicationMallocFailedHook()`，可以在其中输出调试信息，方便定位问题。
