---
title:  "条件变量先 Signal 还是先 Unlock？"
date: 2026-01-15T20:34:58+08:00
categories: [并发]
tags: [multithreading, cpp, condition-variable, mutex]
---

在 C/C++ 多线程编程中，使用条件变量和互斥锁的时候，先 `unlock` 还是先 `signal`/`notify` 都是逻辑正确的，但实际上它们的表现存在细微的差别。

## 先 Signal，后 Unlock

**优点**：保证了发出信号时的共享状态处于锁的保护下，也能防止线程被抢占。

**缺点**：被唤醒的线程刚醒就要等待锁，造成额外的调度开销。

不过现代 Linux 内核对这点进行了优化，增加了条件变量等待队列和互斥量等待队列，唤醒后线程不会阻塞等待，而是移动到等待互斥量的队列，避免了性能损失。

---

## 先 Unlock，后 Signal

**优点**：减少了锁的竞争，被唤醒线程醒来时，锁已经被释放，可以直接获取，这往往提供了更好的性能表现。

**缺点**：在 `unlock` 到 `signal` 间的间隙，可能会有其他线程抢走锁。

- 抢走的后果是被唤醒线程还是阻塞等待，或者更严重的是其他线程修改了本应该被唤醒线程消费的内容。不过这里要小心一个误区，就是如果别的线程消费了数据，就应该把 `ready` 设为 `false`，这样原本的等待线程中的 `while(ready) cond_wait();` 只是会再次进入等待，逻辑上是可靠的

---

## 怎么选

既然每个方法都有优劣，根据不同的情况就会有不同的答案。比较标准的建议是：

**先 Unlock 再 Signal** 能提供更好的通用性能表现，但如果担心锁被抢走/锁保护的数据被修改，就应该考虑选择 **先 Signal 再 Unlock**。但要注意在大多数现代操作系统上，这两种方法的性能差异微乎其微，而先 Signal 更加安全，所以先 Signal 应该是首选。

但我想从底层库设计的角度来说明为什么更应该选择先 Signal。

对底层库设计而言，安全是非常重要的，而先 Unlock 存在的安全隐患不只是数据被不该消费的线程消费了那么简单。假设这样一种情况：

```cpp
// 线程 A (Setter/通知者)
void fulfill(Promise* p, int val) {
    pthread_mutex_lock(&p->mtx);
    p->value = val;
    p->ready = true;
    
    pthread_mutex_unlock(&p->mtx); // <--- [步骤 1] 锁释放了
    
    // --- 灾难可能发生在这个空隙 ---
    
    pthread_cond_signal(&p->cv);   // <--- [步骤 3] 尝试发送信号
}

// 线程 B (Waiter/等待者)
void wait_and_destroy(Promise* p) {
    pthread_mutex_lock(&p->mtx);
    while (!p->ready) {
        pthread_cond_wait(&p->cv, &p->mtx);
    }
    pthread_mutex_unlock(&p->mtx);
    
    delete p; // <--- [步骤 2] 销毁对象！
}
```

原因是可能某种原因导致线程 B 被唤醒了，比如**虚假唤醒**（为了追求高性能，系统允许 `wait` 在极少数情况下即使没有被唤醒也返回）。

如果这个流程换成了先 Signal 再 Unlock，就能保证 `pthread_cond_signal`（步骤 3）一定发生在 `delete p`（步骤 2）之前。

你可以理解为先 Signal 是一种**防御性编程**的习惯，这对底层库的稳定非常重要！