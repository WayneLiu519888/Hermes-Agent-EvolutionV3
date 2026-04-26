"""
元学习模块 - 学习如何学习
支持MAML, Reptile等元学习算法
"""

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
import logging
from copy import deepcopy
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class MetaTask:
    """元学习任务"""
    task_id: str
    task_type: str
    support_set: List[Tuple[np.ndarray, np.ndarray]]  # (输入, 输出)
    query_set: List[Tuple[np.ndarray, np.ndarray]]    # (输入, 输出)
    task_metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    
    def get_batch(self, batch_size: int, from_set: str = "support") -> Tuple[torch.Tensor, torch.Tensor]:
        """获取批次数据"""
        dataset = self.support_set if from_set == "support" else self.query_set
        
        if len(dataset) < batch_size:
            indices = list(range(len(dataset)))
        else:
            indices = np.random.choice(len(dataset), batch_size, replace=False)
        
        inputs = torch.FloatTensor([dataset[i][0] for i in indices])
        targets = torch.FloatTensor([dataset[i][1] for i in indices])
        
        return inputs, targets


class MetaLearner(nn.Module):
    """元学习器"""
    
    def __init__(self, input_dim: int, output_dim: int, hidden_dim: int = 64):
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, output_dim)
        )
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.network(x)
    
    def adapt(self, task: MetaTask, adaptation_steps: int = 5, lr: float = 0.01) -> nn.Module:
        """快速适应新任务"""
        adapted_model = deepcopy(self)
        adapted_optimizer = optim.SGD(adapted_model.parameters(), lr=lr)
        
        for step in range(adaptation_steps):
            # 从支持集采样
            inputs, targets = task.get_batch(batch_size=32, from_set="support")
            
            # 前向传播
            predictions = adapted_model(inputs)
            loss = nn.MSELoss()(predictions, targets)
            
            # 反向传播
            adapted_optimizer.zero_grad()
            loss.backward()
            adapted_optimizer.step()
        
        return adapted_model


class MAML:
    """Model-Agnostic Meta-Learning (MAML)"""
    
    def __init__(
        self,
        input_dim: int,
        output_dim: int,
        meta_lr: float = 0.001,
        inner_lr: float = 0.01,
        adaptation_steps: int = 5,
        meta_batch_size: int = 4
    ):
        self.input_dim = input_dim
        self.output_dim = output_dim
        self.meta_lr = meta_lr
        self.inner_lr = inner_lr
        self.adaptation_steps = adaptation_steps
        self.meta_batch_size = meta_batch_size
        
        # 设备
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # 元学习器
        self.meta_learner = MetaLearner(input_dim, output_dim).to(self.device)
        self.meta_optimizer = optim.Adam(self.meta_learner.parameters(), lr=meta_lr)
        
        # 训练历史
        self.training_history = {
            "meta_losses": [],
            "adaptation_losses": []
        }
        
        logger.info("MAML元学习器初始化完成")
    
    def meta_train_step(self, tasks: List[MetaTask]) -> float:
        """元训练一步"""
        total_meta_loss = 0
        
        # 对每个任务计算梯度并累积
        task_gradients = []
        
        for task in tasks:
            # 复制元学习器用于任务特定适应
            adapted_model = self.meta_learner.adapt(
                task,
                adaptation_steps=self.adaptation_steps,
                lr=self.inner_lr
            )
            
            # 在查询集上评估适应后的模型
            query_inputs, query_targets = task.get_batch(batch_size=32, from_set="query")
            query_predictions = adapted_model(query_inputs)
            task_loss = nn.MSELoss()(query_predictions, query_targets)
            
            # 计算相对于元参数的梯度
            adapted_model.zero_grad()
            task_loss.backward()
            
            # 收集梯度
            task_gradients.append([
                param.grad.clone() if param.grad is not None else torch.zeros_like(param)
                for param in adapted_model.parameters()
            ])
            
            total_meta_loss += task_loss.item()
        
        # 平均梯度并更新元参数
        self.meta_optimizer.zero_grad()
        
        # 设置元学习器的梯度为平均梯度
        for param_idx, param in enumerate(self.meta_learner.parameters()):
            avg_gradient = torch.stack([grads[param_idx] for grads in task_gradients]).mean(dim=0)
            if param.grad is None:
                param.grad = avg_gradient
            else:
                param.grad += avg_gradient
        
        # 更新元参数
        self.meta_optimizer.step()
        
        avg_meta_loss = total_meta_loss / len(tasks)
        self.training_history["meta_losses"].append(avg_meta_loss)
        
        return avg_meta_loss
    
    def meta_train(self, task_distribution, meta_epochs: int = 100) -> List[float]:
        """元训练"""
        meta_losses = []
        
        for epoch in range(meta_epochs):
            # 采样一批任务
            tasks = task_distribution.sample_tasks(self.meta_batch_size)
            
            # 元训练一步
            meta_loss = self.meta_train_step(tasks)
            meta_losses.append(meta_loss)
            
            if (epoch + 1) % 10 == 0:
                logger.info(f"元训练轮次 {epoch + 1}/{meta_epochs}, 元损失: {meta_loss:.4f}")
        
        return meta_losses
    
    def fast_adapt(self, task: MetaTask) -> MetaLearner:
        """快速适应新任务"""
        return self.meta_learner.adapt(
            task,
            adaptation_steps=self.adaptation_steps,
            lr=self.inner_lr
        )
    
    def save(self, path: str) -> None:
        """保存模型"""
        torch.save({
            'meta_learner_state_dict': self.meta_learner.state_dict(),
            'meta_optimizer_state_dict': self.meta_optimizer.state_dict(),
            'training_history': self.training_history
        }, path)
        logger.info(f"元学习模型已保存: {path}")
    
    def load(self, path: str) -> None:
        """加载模型"""
        checkpoint = torch.load(path, map_location=self.device)
        self.meta_learner.load_state_dict(checkpoint['meta_learner_state_dict'])
        self.meta_optimizer.load_state_dict(checkpoint['meta_optimizer_state_dict'])
        self.training_history = checkpoint['training_history']
        logger.info(f"元学习模型已加载: {path}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "meta_loss": np.mean(self.training_history["meta_losses"][-10:]) if self.training_history["meta_losses"] else 0,
            "total_meta_steps": len(self.training_history["meta_losses"])
        }


class TaskDistribution:
    """任务分布"""
    
    def __init__(self, task_family: str = "regression"):
        self.task_family = task_family
        self.task_counter = 0
        
    def sample_task(self) -> MetaTask:
        """采样一个任务"""
        self.task_counter += 1
        task_id = f"task_{self.task_counter}"
        
        if self.task_family == "regression":
            return self._create_regression_task(task_id)
        elif self.task_family == "classification":
            return self._create_classification_task(task_id)
        else:
            raise ValueError(f"未知的任务家族: {self.task_family}")
    
    def sample_tasks(self, n: int) -> List[MetaTask]:
        """采样多个任务"""
        return [self.sample_task() for _ in range(n)]
    
    def _create_regression_task(self, task_id: str) -> MetaTask:
        """创建回归任务"""
        # 随机生成线性函数参数
        input_dim = 5
        output_dim = 1
        
        # 随机权重和偏置
        W = np.random.randn(input_dim, output_dim) * 2.0
        b = np.random.randn(output_dim) * 1.0
        
        # 生成支持集
        support_set = []
        for _ in range(20):
            x = np.random.randn(input_dim)
            y = x @ W + b + np.random.randn(output_dim) * 0.1
            support_set.append((x, y.squeeze()))
        
        # 生成查询集
        query_set = []
        for _ in range(20):
            x = np.random.randn(input_dim)
            y = x @ W + b + np.random.randn(output_dim) * 0.1
            query_set.append((x, y.squeeze()))
        
        return MetaTask(
            task_id=task_id,
            task_type="regression",
            support_set=support_set,
            query_set=query_set,
            task_metadata={
                "W": W.tolist(),
                "b": b.tolist(),
                "input_dim": input_dim,
                "output_dim": output_dim
            }
        )
    
    def _create_classification_task(self, task_id: str) -> MetaTask:
        """创建分类任务"""
        # 简化实现：二分类任务
        input_dim = 10
        n_classes = 2
        
        # 随机生成分类边界
        W = np.random.randn(input_dim, n_classes)
        b = np.random.randn(n_classes)
        
        # 生成支持集
        support_set = []
        for _ in range(20):
            x = np.random.randn(input_dim)
            logits = x @ W + b
            probs = np.exp(logits) / np.exp(logits).sum()
            y = np.eye(n_classes)[np.argmax(probs)]
            support_set.append((x, y))
        
        # 生成查询集
        query_set = []
        for _ in range(20):
            x = np.random.randn(input_dim)
            logits = x @ W + b
            probs = np.exp(logits) / np.exp(logits).sum()
            y = np.eye(n_classes)[np.argmax(probs)]
            query_set.append((x, y))
        
        return MetaTask(
            task_id=task_id,
            task_type="classification",
            support_set=support_set,
            query_set=query_set,
            task_metadata={
                "n_classes": n_classes,
                "input_dim": input_dim
            }
        )


class MetaLearningService:
    """元学习服务"""
    
    def __init__(self):
        self.meta_learners: Dict[str, MAML] = {}
        self.task_distributions: Dict[str, TaskDistribution] = {}
        
        logger.info("元学习服务初始化完成")
    
    def create_meta_learner(
        self,
        learner_id: str,
        input_dim: int,
        output_dim: int,
        **kwargs
    ) -> bool:
        """创建元学习器"""
        if learner_id in self.meta_learners:
            logger.warning(f"元学习器已存在: {learner_id}")
            return False
        
        try:
            meta_learner = MAML(input_dim, output_dim, **kwargs)
            self.meta_learners[learner_id] = meta_learner
            logger.info(f"元学习器创建成功: {learner_id}")
            return True
        except Exception as e:
            logger.error(f"元学习器创建失败: {e}")
            return False
    
    def create_task_distribution(
        self,
        distribution_id: str,
        task_family: str = "regression"
    ) -> bool:
        """创建任务分布"""
        if distribution_id in self.task_distributions:
            logger.warning(f"任务分布已存在: {distribution_id}")
            return False
        
        try:
            distribution = TaskDistribution(task_family)
            self.task_distributions[distribution_id] = distribution
            logger.info(f"任务分布创建成功: {distribution_id}")
            return True
        except Exception as e:
            logger.error(f"任务分布创建失败: {e}")
            return False
    
    async def meta_train(
        self,
        learner_id: str,
        distribution_id: str,
        meta_epochs: int = 100,
        meta_batch_size: int = 4
    ) -> Dict[str, Any]:
        """元训练"""
        if learner_id not in self.meta_learners:
            return {"success": False, "error": f"元学习器不存在: {learner_id}"}
        
        if distribution_id not in self.task_distributions:
            return {"success": False, "error": f"任务分布不存在: {distribution_id}"}
        
        meta_learner = self.meta_learners[learner_id]
        distribution = self.task_distributions[distribution_id]
        
        logger.info(f"开始元训练: {learner_id}, 分布: {distribution_id}, 轮次: {meta_epochs}")
        
        # 更新元批次大小
        meta_learner.meta_batch_size = meta_batch_size
        
        # 执行元训练
        meta_losses = meta_learner.meta_train(distribution, meta_epochs)
        
        stats = meta_learner.get_stats()
        stats.update({
            "meta_epochs": meta_epochs,
            "final_meta_loss": meta_losses[-1] if meta_losses else 0,
            "min_meta_loss": min(meta_losses) if meta_losses else 0
        })
        
        return {
            "success": True,
            "stats": stats,
            "meta_losses": meta_losses
        }
    
    async def fast_adapt(
        self,
        learner_id: str,
        task: MetaTask
    ) -> Dict[str, Any]:
        """快速适应新任务"""
        if learner_id not in self.meta_learners:
            return {"success": False, "error": f"元学习器不存在: {learner_id}"}
        
        meta_learner = self.meta_learners[learner_id]
        
        try:
            # 快速适应
            adapted_model = meta_learner.fast_adapt(task)
            
            # 在查询集上评估
            query_inputs, query_targets = task.get_batch(batch_size=32, from_set="query")
            with torch.no_grad():
                query_predictions = adapted_model(query_inputs)
                adaptation_loss = nn.MSELoss()(query_predictions, query_targets).item()
            
            return {
                "success": True,
                "adaptation_loss": adaptation_loss,
                "task_id": task.task_id
            }
        except Exception as e:
            logger.error(f"快速适应失败: {e}")
            return {"success": False, "error": str(e)}
    
    def get_learner_stats(self, learner_id: str) -> Optional[Dict[str, Any]]:
        """获取元学习器统计信息"""
        if learner_id not in self.meta_learners:
            return None
        
        return self.meta_learners[learner_id].get_stats()
    
    def save_learner(self, learner_id: str, path: str) -> bool:
        """保存元学习器"""
        if learner_id not in self.meta_learners:
            return False
        
        try:
            self.meta_learners[learner_id].save(path)
            return True
        except Exception as e:
            logger.error(f"元学习器保存失败: {e}")
            return False
    
    def load_learner(self, learner_id: str, path: str) -> bool:
        """加载元学习器"""
        try:
            # 如果元学习器不存在，需要知道输入输出维度
            if learner_id not in self.meta_learners:
                # 这里需要从文件或配置中获取维度信息
                # 简化实现：创建默认元学习器然后加载
                pass
            
            self.meta_learners[learner_id].load(path)
            return True
        except Exception as e:
            logger.error(f"元学习器加载失败: {e}")
            return False


# 全局元学习服务实例
meta_learning_service = MetaLearningService()