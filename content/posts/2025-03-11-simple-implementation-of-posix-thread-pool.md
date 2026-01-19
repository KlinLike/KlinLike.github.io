---
title: "基于POSIX的线程池的简单实现"
date: 2025-03-11T22:56:40+08:00
categories: [并发]
tags: [multithreading, cpp]
---

*本文的主要内容是我学习线程池时候写下的代码，在此基础上加上一些我的理解和关键知识点*

# 实现线程池时需要注意的点
1. 线程安全：所有对共享资源的访问都应该正确加锁
2. 资源释放：任务队列、工作线程需要被处理并释放
3. 错误处理：例如创建线程失败，需要有正确的回滚操作（释放所有已经创建的资源）
4. 条件变量：需要正确使用条件变量，比如需要处理虚假唤醒
5. 链表操作：链表操作函数需要正确处理各种情况，如空链表的处理
6. 任务生命：需要注意任务的创建和销毁由谁执行
7. 死锁风险：确保不会因为锁未释放造成死锁

# 设计思想
使用生产者-消费者模型，工作线程是消费者，主线程是生产者。

分层设计。
看结构体：nodeTask包含任务函数和数据，是业务层；
nodeWorker包含工作线程，是执行层；
PoolManager管理任务和线程，是控制层。
函数的分层已经在程序中用注释进行了分类。

# 实现代码
```
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <pthread.h>

// 工具层 ---------------------------------------------

--> 在头部插入效率高，但是会LIFO可能会导致最先插入的任务最后被执行

// insert只发生在头部
#define LIST_INSERT(item, list) do {			\
	(item)->prev = NULL;						\
	(item)->next = list;						\
	if((list) != NULL) (list)->prev = (item);	\
	(list) = (item);							\
} while(0)

// remove可以发生在任何位置
#define LIST_REMOVE(item, list) do {							\
	if((item)->prev != NULL) (item)->prev->next = (item)->next;	\
	if((item)->next != NULL) (item)->next->prev = (item)->prev;	\
	if((list) == (item)) (list) = (item)->next;					\
	(item)->next = (item)->prev = NULL;							\
} while(0)

// 结构体 ---------------------------------------------

--> 分别定义任务信息（nodeTask链表）和线程信息（nodeWorker链表），分离任务与工作线程，
--> 并通过管理者（PoolManager）管理，通过这种方式实现了任务与线程的解耦。

struct nodeTask
{
	// 其实可以创建多种任务和任务数据，实现任务和数据的自由组合
	void (*task_func)(struct nodeTask* task);
	void* user_data;

	struct nodeTask* prev;
	struct nodeTask* next;
};

struct nodeWorker{
	pthread_t threadid;
	int terminated;
	struct PoolManager* manager;

	struct nodeWorker* prev;
	struct nodeWorker* next;
};

struct PoolManager{
	struct nodeTask* tasks;
	struct nodeWorker* workers;

	pthread_mutex_t mtx;
	pthread_cond_t cond;
};

// 执行层 ---------------------------------------------

// 工作线程的事件循环
static void* ThreadCallback(void* arg){
	struct nodeWorker* worker = (struct nodeWorker*)arg;
	while(1){
		pthread_mutex_lock(&(worker->manager->mtx));
		// 使用while循环的目的是在唤醒之后也进行条件判断，避免虚假唤醒
		while (worker->manager->tasks == NULL){
			//printf("No Task, thread wait %lu.\n", worker->threadid);
			pthread_cond_wait(&worker->manager->cond, &worker->manager->mtx);
			//printf("Got wake, thread continue %lu.\n", worker->threadid);
			-->  Q 终止判断在pthread_cond_wait前和pthread_cond_wait后有什么差异？
			if(worker->terminated == 1){
				//printf("Thread terminated %lu.\n", worker->threadid);
				pthread_mutex_unlock(&(worker->manager->mtx));
				pthread_exit(NULL);
			}
		}
		-->  Q 这个检查是必要的吗？如果去掉会造成什么影响？
		-->  A 如果去掉，线程会一直执行直到清空任务队列，可能会导致线程无法及时退出，但却解决了任务遗留的问题。
        --> 更进一步的问题是，其实可以在destroy函数里等待任务队列清空，这样清空的速度也许更快。
		if(worker->terminated == 1){
			//printf("Thread terminated %lu.\n", worker->threadid);
			pthread_mutex_unlock(&(worker->manager->mtx));
			pthread_exit(NULL);
		}
		struct nodeTask* task = worker->manager->tasks;
		LIST_REMOVE(task, worker->manager->tasks);
		//printf("Got Task, thread unlock %lu.\n", worker->threadid);
		pthread_mutex_unlock(&(worker->manager->mtx));

		// 拿到任务后要立刻解锁，因为任务执行不需要锁，这样可以提高性能
		// 任务内存由任务自己释放，分离工作线程和任务的内存管理
		task->task_func(task);
	}
	//printf("Thread exit  %lu.\n", worker->threadid);
	return 0;
}

// 控制层 ---------------------------------------------

// 初始化线程池，创建工作线程
int CreatePool(struct PoolManager* manager, int workerCount){
	if(manager == NULL) return -1;	// 要求调用方创建并初始化对象
	if(manager->tasks != NULL) return -2;
	if(manager->workers != NULL) return -3;
	if(workerCount < 1) workerCount = 1;


--> 当条件变量是动态分配的结构体成员时，无法直接使用PTHREAD_COND_INITIALIZER进行静态初始化，
--> 需要借助一个已经初始化的条件变量赋值到目标变量实现初始化。
--> 即使将PTHREAD_COND_INITIALIZER分别赋值给多个变量，这些变量之间也不会搞混，
--> 因为条件变量本质上是一个对象，每个条件变量都有自己独立的状态和数据。
--> 而且PTHREAD_COND_INITIALIZER也等同于pthread_cond_init()，是一个特殊的常量宏。
--> 那为什么会有两种初始化方式呢？
--> 因为有些情况使用静态初始化更加方便高效，比如程序启动时就要用到的全局条件变量，或者希望减少函数调用开销。
--> 同样也有些情况使用动态初始化更加方便，比如要为条件变量指定属性的时候。

	
	//pthread_cond_t blank_cond = PTHREAD_COND_INITIALIZER;
	//memcpy(&manager->cond, &blank_cond, sizeof(pthread_cond_t));

if(pthread_cond_init(&manager->cond, NULL) != 0){
		perror("Init cond fail.\n");
		return -6;
	}
	if(pthread_mutex_init(&manager->mtx, NULL) != 0){
		perror("Init mtx fail.\n");
		return -7;
	}

	int i = 0;
	for(i = 0; i < workerCount; i++){
		// 创建
		struct nodeWorker* w = (struct nodeWorker*)malloc(sizeof(struct nodeWorker));
		if(w == NULL) {
			perror("Malloc worker fail.\n");
			return -4;
		}
		memset(w, 0, sizeof(struct nodeWorker));
		// 设置
		w->manager = manager;
		// 参数3： void *(*)(void *) 是一个函数指针，新创建的线程会从这个函数开始执行
        // 参数4： void* 是传递给新线程执行函数的参数
        // 创建成功返回0
		int ret = pthread_create(&w->threadid, NULL, ThreadCallback, w);
		if(ret){
			perror("Create thread fail.\n");
			// 应该释放整个队列而不是一个阶段，有内存泄漏的风险
			free(w);
			return -5;
		}
		// 插入
		LIST_INSERT(w, manager->workers);
		//printf("Insert worker done : %d\n", i);
	}
	return 0;
}

--> DestroyPool由调用CreatePool的线程执行，也就是“谁创建谁释放”。

-->  函数的一个潜在问题是：任务队列可能还没被清空。
int DestroyPool(struct PoolManager* manager){
	pthread_mutex_lock(&manager->mtx);

	struct nodeWorker* w = manager->workers;
    while(w){
        w->terminated = 1;
        w = w->next;
    }

	pthread_cond_broadcast(&manager->cond);
	pthread_mutex_unlock(&manager->mtx);

	// 等待所有线程退出并清理资源
    w = manager->workers;
    while(w){
        struct nodeWorker* next = w->next;
        pthread_join(w->threadid, NULL); // 等待线程结束
        free(w);
        w = next;
    }
	//printf("All threads joined.\n");

	// 同步资源也不要忘了清理
    pthread_mutex_destroy(&manager->mtx);
    pthread_cond_destroy(&manager->cond);

    // 重置管理器状态
    manager->workers = NULL;
    manager->tasks = NULL;

	return 0;
}

int PushTask(struct PoolManager* manager, struct nodeTask* task){
	if(manager == NULL) return -1;
	if(task == NULL) return -2;

	// 任务被推送到线程池后，由task_entry函数自己释放
	pthread_mutex_lock(&manager->mtx);
	LIST_INSERT(task, manager->tasks);
	pthread_cond_signal(&manager->cond);
	pthread_mutex_unlock(&manager->mtx);
}

// 应用层 ---------------------------------------------

#define THREAD_SIZE	5
#define TASK_SIZE	50

void task_entry(struct nodeTask* task){
	int idx = *(int*)(task->user_data);
	printf("task_entry idx:%d\n", idx);
	free(task->user_data); // 可以不是指针吗？
	free(task);
}

int main(void){
	printf("Start run main.\n");
	struct PoolManager* pool = (struct PoolManager*)malloc(sizeof(struct PoolManager));
	if(pool == NULL){
		perror("Malloc pool fail.\n");
		exit(2);
	}
	memset(pool, 0, sizeof(struct PoolManager));
	if(CreatePool(pool, THREAD_SIZE) != 0){
		perror("Create pool fail.\n");
		exit(1);
	}

	printf("Create pool done.\n");

	int i = 0;
	for(i = 0; i < TASK_SIZE; i++){
		struct nodeTask* task = (struct nodeTask*)malloc(sizeof(struct nodeTask));
		if(task == NULL){
			perror("Malloc task fail.");
			exit(1);
		}
		memset(task, 0, sizeof(struct nodeTask));
		task->task_func = task_entry;
		task->user_data = (int*)malloc(sizeof(int));
		if(task->user_data == NULL){
			perror("Malloc data fail.");
			exit(1);
		}
		*(int*)(task->user_data) = i;

		int ret = PushTask(pool, task);
		//printf("Push task done : %d return %d\n", i, ret);
	}

	while (1){
		pthread_mutex_lock(&pool->mtx);
		if(pool->tasks == NULL) break;
		pthread_mutex_unlock(&pool->mtx);
		sleep(1);
	}
	pthread_mutex_unlock(&pool->mtx);
	printf("Job done, start exit threads.\n");
	DestroyPool(pool);
	printf("Destroy pool done, program exited.\n");
	return 0;
}

```
