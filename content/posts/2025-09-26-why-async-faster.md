---
title:  "为什么异步编程比同步更快，而CPU完成的工作量是一样的？"
date: 2025-09-26T14:00:54+08:00
tags: [C++, 异步, Async, 编程范式]
---

答案的关键在于：异步编程并没有减少CPU的总工作量，而是提高了CPU的利用率，极大减少了“等待”时间。

# 事件循环

大多数现代异步框架都基于 事件循环模型，它的工作流程如下：
1. 任务入队：当代码发起一个异步请求时（如读取文件、发送网络数据），框架会将 这个任务 以及 完成后应该调用的回调函数 一并提交给OS；
2. 立即返回：提交之后，主线程不会等待结果，而是立即返回，继续执行之后的代码；
3. 内核处理：操作系统接管了任务，它会用更高效的方式来完成，并且可以在硬件层面等待数据就绪（比如数据全都读取到缓冲区后发起中断），不用占用CPU；
4. 事件循环与任务队列：主线程在执行完同步代码后，就会开始轮询任务队列（也就是事件循环）；
5. 当OS完成了操作，就会创建一个事件，并将与之关联的回调函数放入任务队列中；
6. 事件循环发现任务队列中有了新任务，就会取出任务并执行（也就是将回调函数推入到 调用栈 执行）。

结合EPOLL + socket来看就是：
1. 任务入队：epoll_ctl(..., EPOLL_CTL_ADD, socket, ...) *-> 告诉内核，请帮我监视这个socket，该函数立即返回，也就是 注册任务后不等待*
2. 内核处理：内核开始在后台独立工作，等待网卡数据。当数据到达时，内核会将对应socket标记为就绪
3. 事件循环与任务队列：epoll_wait(...) *-> 主循环阻塞在这里，但不消耗CPU，而是睡眠，并且等待内核的唤醒通知*
4. 一旦socket就绪，epoll_wait就会被唤醒并返回，同时告诉程序那些socket已经就绪（这里对应的是上面的5.6.两步，取出任务并执行，任务就是唤醒epoll_wait）
5. 程序得知socket状态后，继续执行

通过这个机制，在理性情况下，CPU永远在做有意义的事情：要么执行同步代码，要么从任务队列中取出异步任务进行后续处理。

# Qt的事件模型

Qt的框架设计非常优秀，其事件模型是教科书级别的Reactor实现。

对GUI框架而言，有一个优先级更高的问题：主线程，也就是GUI线程，绝对不能被阻塞。一旦被阻塞，用户界面就会失去响应，体验极差。

有关的核心组件：
- QApplication/QCoreApplication：是应用程序的管理者，它拥有并负责启动事件循环；
- 事件队列：一个先进先出的队列，用来存放所有待处理的QEvent对象；
- QEvent：一个事件的表示，无论是用户的输入（鼠标、键盘），还是系统内部的定时器超时，窗口重绘请求，都会被封装成一个QEvent对象;
- QObject:Qt中绝大多数类的基类，具备接受和处理事件的能力。

工作流程：
0. 程序启动并调用app.exec()，事件循环开始；
1. 循环首先检查事件队列是否为空；
2. 如果队列为空，事件循环会进入休眠状态，将CPU控制权交还给操作系统；
3. 当操作系统或Qt内部产生新的事件时，事件循环被唤醒；
4. 事件循环从队列头部取出事件（新事件会被封装成QEvent对象并添加到事件队列末尾），它会识别事件的目标接受者（一个QObject对象）并调用对象的.event()方法，同时将事件对象作为参数传递过去；
5. .event()方法会根据事件的具体类型，调用对应的事件处理函数，如mousePressEvent()\keyPressEvent();
6. 一个event处理完毕后，循环立即回到第一步（检查下个事件）；
7. 持续1-6直到接收到退出时间，然后app.exec()返回。

*-> 这里的第三步和前面的第四步都涉及唤醒，但需要注意的是：OS和App之间是有隔离的，也就是我们常说的 内核空间 和 用户空间。内核空间通常不会直接调用一个用户空间函数，因为这会有很大的风险。所以唤醒并不是通过OS直接调用 用户空间内的某个回调函数实现的，而是通过内核唤醒进程实现的。*

信号槽：
信号槽是建立在事件循环上的抽象，它简化了对象间的通信。
这种优势在不同线程的对象间通信中展现得尤其明显：当一个信号通过队列连接发射到一个位于另一线程的槽时，系统并不会直接调用该槽函数。系统会创建一个QEvent，其内部包含了要执行的槽函数及其参数，随后将这个QEvent投递到接收者对象所在线程的事件队列中。最终接受者线程的事件循环会取出这个QEvent并执行对应的槽函数。

*-> app.exec()只负责启动主线程（也就是GUI线程）的事件循环。对于其他的工作线程，如果它们也需要处理事件，则必须在线程内部手动启用一个属于他自己的事件循环。这就是为什么上面说每个线程自己的事件循环，也就是“事件循环不是唯一的，而是与线程绑定的”。*

# 设计模式的变迁

我们用制作一杯咖啡过程来举例：
1. 磨咖啡豆 (耗时2秒)
2. 用磨好的咖啡粉 萃取浓缩咖啡 (耗时3秒)
3. 打发牛奶 制作奶泡 (耗时4秒)
4. 将浓缩咖啡和奶泡混合，再加入巧克力酱，制成摩卡 (耗时1秒)
每个步骤都依赖于前一个步骤的完成。

下面是示例代码的基础部分(cpp)：
```
#include <iostream>
#include <string>
#include <thread>
#include <chrono>
#include <functional>
#include <future>

// 模拟一个需要一定时间才能完成的操作
void simulate_work(int ms) {
    std::this_thread::sleep_for(std::chrono::milliseconds(ms));
}

// 咖啡制作的各个步骤的产出品
struct Grounds { std::string value = "咖啡粉"; };
struct Espresso { std::string value = "浓缩咖啡"; };
struct MilkFoam { std::string value = "奶泡"; };
struct Mocha { std::string value = "一杯香浓的摩卡"; };
```

# 阶段1：回调函数 Callback
回调函数是最原始、最直接的异步处理方式。核心思想是：当你昨晚这件事后，请调用我给你的这个函数。

用制作咖啡的过程举例就是：
磨完豆子之后，调用萃取函数，萃取完成后，调用制作奶泡函数，最后调用混合函数。

用去快餐店点餐举例就是：
你去点餐，留下电话，老板会在做好后打你电话。

这个模式的痛点显而易见：
1. 回调地狱：代码无限延伸，形成一个难以阅读和维护的嵌套结构；
2. 控制反转：我们失去了对流程的直接控制，将程序的下一步执行权完全交给了第三方函数。如果第三方函数有bug，程序就会出问题。
3. 每个第三方函数都需要实现自己的错误处理，繁琐且冗余

回调地狱的示例代码：
```
// 1. 磨咖啡豆 (异步)
void grindBeans_cb(std::function<void(Grounds)> callback) {
    std::thread([=]() {
        std::cout << "1. 开始磨咖啡豆...\n";
        simulate_work(1000);
        Grounds grounds;
        std::cout << "1. 咖啡豆磨好了 -> " << grounds.value << "\n";
        callback(grounds); // 完成后，调用传入的回调函数
    }).detach();
}

// 2. 萃取浓缩咖啡 (异步)
void brewEspresso_cb(const Grounds& grounds, std::function<void(Espresso)> callback) {
    std::thread([=]() {
        std::cout << "2. 开始用'" << grounds.value << "'萃取浓缩咖啡...\n";
        simulate_work(1500);
        Espresso espresso;
        std::cout << "2. 浓缩咖啡做好了 -> " << espresso.value << "\n";
        callback(espresso);
    }).detach();
}

// 3. 制作奶泡 (异步)
void frothMilk_cb(std::function<void(MilkFoam)> callback) {
    std::thread([=]() {
        std::cout << "3. 开始制作奶泡...\n";
        simulate_work(2000);
        MilkFoam foam;
        std::cout << "3. 奶泡做好了 -> " << foam.value << "\n";
        callback(foam);
    }).detach();
}

// 4. 混合制作摩卡 (异步)
void makeMocha_cb(const Espresso& e, const MilkFoam& f, std::function<void(Mocha)> callback) {
    std::thread([=]() {
        std::cout << "4. 开始混合 " << e.value << " 和 " << f.value << "...\n";
        simulate_work(500);
        Mocha mocha;
        std::cout << "4. 摩卡做好了!\n";
        callback(mocha);
    }).detach();
}


// 回调地狱!!!
void run_callback_example() {
    std::cout << "\n--- 阶段1: 回调函数示例 ---\n";
    
    // 使用嵌套的Lambda表达式来编排流程
    grindBeans_cb([](Grounds grounds) {
        brewEspresso_cb(grounds, [](Espresso espresso) {
            frothMilk_cb([=](MilkFoam foam) { // espresso需要捕获
                makeMocha_cb(espresso, foam, [](Mocha mocha) {
                    std::cout << ">>> 最终成品: " << mocha.value << std::endl;
                });
            });
        });
    });

    // 主线程需要等待，否则程序会直接退出
    std::this_thread::sleep_for(std::chrono::seconds(6));
}
```

# 阶段2：Promise
Promise模式引入了一个核心概念：一个代表了未来结果的对象。

用去快餐店点餐举例就是：
你去点餐，不用留下电话，取而代之的是给你一个叫号器（Promise对象）。叫号器有几种状态：
- pending,进行中：厨房正在做；
- fulfilled,已成功：叫号器振动，可以取餐了；
- rejected,失败：指示器显示号码取消，可能是食材没了。

这里的关键在于，控制权回到了你的手上。你可以决定什么时候查看叫号器，也可以决定做好之后要怎么做（比如先放一会等你完成手头的事情再去取餐，因为你有取餐凭证——叫号器）。

Promise带来的巨大进步：
1. 通过链式调用，将金字塔结构拉平成了线性的流程，代码可读性大大增强；
2. 控制权回归；
3. 统一的错误处理；
4. 可以组合多个Promise，简化了复杂任务的处理。

Promise模式的示例代码(cpp中用promise&future实现)：

```
// 1. 磨咖啡豆 (返回 future)
std::future<Grounds> grindBeans_promise() {
    std::promise<Grounds> p;
    std::future<Grounds> f = p.get_future();

    std::thread([p = std::move(p)]() {
        std::cout << "1. 开始磨咖啡豆...\n";
        simulate_work(1000);
        Grounds grounds;
        std::cout << "1. 咖啡豆磨好了 -> " << grounds.value << "\n";
        p.set_value(grounds);
    }).detach();
    
    return f;
}

// 2. 萃取浓缩咖啡 (接收 future，返回 future)
std::future<Espresso> brewEspresso_promise(std::future<Grounds> grounds_f) {
    std::promise<Espresso> p;
    std::future<Espresso> f = p.get_future();

    std::thread([p = std::move(p), grounds_f = std::move(grounds_f)]() {
        Grounds grounds = grounds_f.get(); 
        std::cout << "2. 开始用'" << grounds.value << "'萃取浓缩咖啡...\n";
        simulate_work(1500);
        Espresso espresso;
        std::cout << "2. 浓缩咖啡做好了 -> " << espresso.value << "\n";
        p.set_value(espresso);
    }).detach();

    return f;
}

// 3. 制作奶泡 (返回 future)
std::future<MilkFoam> frothMilk_promise() {
    std::promise<MilkFoam> p;
    std::future<MilkFoam> f = p.get_future();

    std::thread([p = std::move(p)](){
        std::cout << "3. 开始制作奶泡...\n";
        simulate_work(2000);
        MilkFoam foam;
        std::cout << "3. 奶泡做好了 -> " << foam.value << "\n";
        p.set_value(foam);
    }).detach();

    return f;
}

// 4. 混合制作摩卡 (接收 futures, 返回 future)
std::future<Mocha> makeMocha_promise(std::future<Espresso> e_f, std::future<MilkFoam> f_f) {
     std::promise<Mocha> p;
     std::future<Mocha> mocha_f = p.get_future();

     std::thread([p = std::move(p), e_f = std::move(e_f), f_f = std::move(f_f)](){
        Espresso e = e_f.get();
        MilkFoam f = f_f.get();
        std::cout << "4. 开始混合 " << e.value << " 和 " << f.value << "...\n";
        simulate_work(500);
        Mocha mocha;
        std::cout << "4. 摩卡做好了!\n";
        p.set_value(mocha);
     }).detach();

     return mocha_f;
}

void run_promise_example() {    
    // 启动并行任务
    std::future<Grounds> grounds_f = grindBeans_promise();
    std::future<MilkFoam> milk_f = frothMilk_promise(); // 制作奶泡可以和磨豆、萃取并行

    // 编排依赖关系
    std::future<Espresso> espresso_f = brewEspresso_promise(std::move(grounds_f));
    std::future<Mocha> mocha_f = makeMocha_promise(std::move(espresso_f), std::move(milk_f));
    
    // 在主线程阻塞等待最终结果
    try {
        Mocha final_mocha = mocha_f.get();
        std::cout << ">>> 最终成品: " << final_mocha.value << std::endl;
    } catch (const std::exception& e) {
        std::cerr << "制作过程中出错: " << e.what() << '\n';
    }
}
```
*-> std::promise & future是无法被复制的，所以需要用std::move*


# 阶段3：Async/Await
Promise的调用链在逻辑非常复杂时，仍然会显得冗长。Async/Await并非发明了新的底层机制，而是给Promise模式提供了一层语法糖。
async/await模式的本质，是一种障眼法，它允许我们用写同步代码的逻辑和顺序，来描述和控制完全异步、非阻塞的执行流程。


用去快餐店点餐举例就是：
你不用再亲自等叫号器，而是直接告诉你的助手：等餐品准备好后，送到我的桌子上。

这个例子可能不太明显，下面用制作咖啡来举例（这个助理实际上是调度程序）：
你不再需要亲自等叫号器，而是直接告诉你的助理：
1. 等待 (await) 咖啡豆磨好
2. 然后，等待 (await) 用它萃取出浓缩咖啡
3. 同时，等待 (await) 牛奶打发好
4. 最后，等待 (await) 它们混合成摩卡

你可以写出更符合人类直觉的代码，助理这会在等待的间隙处理其他事情（比如事件循环），并在任务完成后回来继续执行下一步。

Async/Await的优势：
1. 可读性极强；
2. 错误处理更加自然；
3. 调试更加方便，不像调试Promise链那样困难。


Async/Await的示例代码：
*-> 基于ASIO的协程模式，体现了 async/await 这种设计思想。之所以使用ASIO而不是C++标准库，是因为没有发现标准库能用同样优雅方式实现的方法。*
```	
#include <iostream>
#include <string>
#include <chrono>
#include <asio.hpp>
#include <asio/co_spawn.hpp>
#include <asio/detached.hpp>
#include <asio/steady_timer.hpp>


// 为了方便观察，我们创建一个带线程ID的打印函数
void print(const std::string& msg) {
    std::cout << "[Thread " << std::this_thread::get_id() << "] " << msg << std::endl;
}

struct Grounds { std::string value = "咖啡粉"; };
struct Espresso { std::string value = "浓缩咖啡"; };
struct MilkFoam { std::string value = "奶泡"; };
struct Mocha { std::string value = "一杯香浓的摩卡"; };


// 所有异步函数现在返回 asio::awaitable<T>，这是 Asio 原生支持协程的类型

// 1. 磨咖啡豆
asio::awaitable<Grounds> grindBeans_asio() {
    print("1. 开始磨咖啡豆...");
    
    // 获取当前协程的执行器(executor)来创建定时器
    auto executor = co_await asio::this_coro::executor;
    asio::steady_timer timer(executor, std::chrono::seconds(1));
    
    // co_await 一个原生的 asio 异步操作
    co_await timer.async_wait(asio::use_awaitable);
    
    Grounds grounds;
    print("1. 咖啡豆磨好了 -> " + grounds.value);
    co_return grounds;
}

// 2. 萃取浓缩咖啡
asio::awaitable<Espresso> brewEspresso_asio(const Grounds& grounds) {
    print("2. 开始用'" + grounds.value + "'萃取浓缩咖啡...");
    auto executor = co_await asio::this_coro::executor;
    asio::steady_timer timer(executor, std::chrono::seconds(2));
    co_await timer.async_wait(asio::use_awaitable);
    
    Espresso espresso;
    print("2. 浓缩咖啡做好了 -> " + espresso.value);
    co_return espresso;
}

// 3. 制作奶泡
asio::awaitable<MilkFoam> frothMilk_asio() {
    print("3. 开始制作奶泡...");
    auto executor = co_await asio::this_coro::executor;
    asio::steady_timer timer(executor, std::chrono::seconds(1));
    co_await timer.async_wait(asio::use_awaitable);

    MilkFoam foam;
    print("3. 奶泡做好了 -> " + foam.value);
    co_return foam;
}

// 4. 混合制作摩卡
asio::awaitable<Mocha> makeMocha_asio(const Espresso& e, const MilkFoam& f) {
    print("4. 开始混合 " + e.value + " 和 " + f.value + "...");
    auto executor = co_await asio::this_coro::executor;
    asio::steady_timer timer(executor, std::chrono::milliseconds(500));
    co_await timer.async_wait(asio::use_awaitable);

    Mocha mocha;
    print("4. 摩卡做好了!");
    co_return mocha;
}

// 顶层的工作流协程
asio::awaitable<void> makeMochaWorkflow() {
    print("--- Asio 协程工作流开始 ---");

    // 1. 并行启动两个不相干的任务
    // co_spawn 会立即开始执行这两个协程，并返回一个 awaitable 对象
    auto grounds_task = asio::co_spawn(co_await asio::this_coro::executor, grindBeans_asio(), asio::use_awaitable);
    auto milk_task = asio::co_spawn(co_await asio::this_coro::executor, frothMilk_asio(), asio::use_awaitable);

    // 2. 等待磨豆任务完成，因为下一步依赖它
    auto grounds = co_await grounds_task;

    // 3. 开始萃取任务
    auto espresso = co_await brewEspresso_asio(grounds);

    // 4. 等待打奶泡任务完成
    auto foam = co_await milk_task;

    // 5. 混合并等待最终结果
    auto final_mocha = co_await makeMocha_asio(espresso, foam);

    print(">>> 最终成品: " + final_mocha.value);
    print("--- Asio 协程工作流结束 ---");
}


int main() {
    // 1. 创建 Asio 的核心 io_context，它扮演了事件循环调度器的角色
    asio::io_context ctx;

    // 2. 使用 co_spawn 将我们的顶层协程任务“扔”到 io_context 上去执行
    //    asio::detached 表示我们“发射后不管”，不在这里等待它的结果
    asio::co_spawn(ctx, makeMochaWorkflow(), asio::detached);

    // 3. 运行 io_context 的事件循环。
    //    它会执行所有异步任务，直到没有任务可做时才会返回。
    print("Asio 事件循环开始运行...");
    ctx.run();
    print("Asio 事件循环结束。");

    return 0;
}
```


