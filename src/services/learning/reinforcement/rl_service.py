"""
强化学习模块 - 基于奖励的学习和优化
支持多种RL算法：DQN, PPO, A2C等
"""

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import deque
import random
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class RLState:
    """强化学习状态"""
    observation: np.ndarray
    context: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_tensor(self) -> torch.Tensor:
        """转换为PyTorch张量"""
        return torch.FloatTensor(self.observation)


@dataclass
class RLAction:
    """强化学习动作"""
    action_id: int
    action_type: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "action_id": self.action_id,
            "action_type": self.action_type,
            "parameters": self.parameters,
            "confidence": self.confidence
        }


@dataclass
class RLExperience:
    """强化学习经验"""
    state: RLState
    action: RLAction
    reward: float
    next_state: RLState
    done: bool
    info: Dict[str, Any] = field(default_factory=dict)
    
    def to_tuple(self) -> Tuple:
        """转换为元组"""
        return (
            self.state.observation,
            self.action.action_id,
            self.reward,
            self.next_state.observation,
            self.done
        )


class ReplayBuffer:
    """经验回放缓冲区"""
    
    def __init__(self, capacity: int = 10000):
        self.capacity = capacity
        self.buffer = deque(maxlen=capacity)
        self.position = 0
        
    def push(self, experience: RLExperience) -> None:
        """添加经验"""
        self.buffer.append(experience)
        
    def sample(self, batch_size: int) -> List[RLExperience]:
        """随机采样"""
        if len(self.buffer) < batch_size:
            return list(self.buffer)
        return random.sample(self.buffer, batch_size)
    
    def __len__(self) -> int:
        return len(self.buffer)
    
    def clear(self) -> None:
        """清空缓冲区"""
        self.buffer.clear()


class QNetwork(nn.Module):
    """Q网络"""
    
    def __init__(self, state_dim: int, action_dim: int, hidden_dim: int = 128):
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, action_dim)
        )
        
    def forward(self, state: torch.Tensor) -> torch.Tensor:
        return self.network(state)


class DQNAgent:
    """DQN智能体"""
    
    def __init__(
        self,
        state_dim: int,
        action_dim: int,
        learning_rate: float = 0.001,
        gamma: float = 0.99,
        epsilon_start: float = 1.0,
        epsilon_end: float = 0.01,
        epsilon_decay: float = 0.995,
        buffer_capacity: int = 10000,
        batch_size: int = 64,
        target_update: int = 10
    ):
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.gamma = gamma
        self.epsilon = epsilon_start
        self.epsilon_start = epsilon_start
        self.epsilon_end = epsilon_end
        self.epsilon_decay = epsilon_decay
        self.batch_size = batch_size
        self.target_update = target_update
        self.update_counter = 0
        
        # 设备
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # 网络
        self.policy_net = QNetwork(state_dim, action_dim).to(self.device)
        self.target_net = QNetwork(state_dim, action_dim).to(self.device)
        self.target_net.load_state_dict(self.policy_net.state_dict())
        self.target_net.eval()
        
        # 优化器
        self.optimizer = optim.Adam(self.policy_net.parameters(), lr=learning_rate)
        
        # 经验回放
        self.memory = ReplayBuffer(buffer_capacity)
        
        # 训练历史
        self.training_history = {
            "losses": [],
            "rewards": [],
            "epsilons": []
        }
        
        logger.info(f"DQN智能体初始化完成，设备: {self.device}")
    
    def select_action(self, state: RLState, training: bool = True) -> RLAction:
        """选择动作"""
        state_tensor = state.to_tensor().unsqueeze(0).to(self.device)
        
        if training and random.random() < self.epsilon:
            # 探索：随机选择动作
            action_id = random.randrange(self.action_dim)
        else:
            # 利用：选择Q值最大的动作
            with torch.no_grad():
                q_values = self.policy_net(state_tensor)
                action_id = q_values.argmax().item()
        
        # 创建动作对象
        action = RLAction(
            action_id=action_id,
            action_type="rl_action",
            parameters={"q_value": q_values[0][action_id].item() if not training else None},
            confidence=1.0 - self.epsilon if training else 1.0
        )
        
        return action
    
    def store_experience(self, experience: RLExperience) -> None:
        """存储经验"""
        self.memory.push(experience)
    
    def train_step(self) -> Optional[float]:
        """训练一步"""
        if len(self.memory) < self.batch_size:
            return None
        
        # 采样经验
        batch = self.memory.sample(self.batch_size)
        
        # 转换为张量
        states = torch.FloatTensor([exp.state.observation for exp in batch]).to(self.device)
        actions = torch.LongTensor([exp.action.action_id for exp in batch]).to(self.device)
        rewards = torch.FloatTensor([exp.reward for exp in batch]).to(self.device)
        next_states = torch.FloatTensor([exp.next_state.observation for exp in batch]).to(self.device)
        dones = torch.FloatTensor([exp.done for exp in batch]).to(self.device)
        
        # 计算当前Q值
        current_q_values = self.policy_net(states).gather(1, actions.unsqueeze(1))
        
        # 计算目标Q值
        with torch.no_grad():
            next_q_values = self.target_net(next_states).max(1)[0]
            target_q_values = rewards + (1 - dones) * self.gamma * next_q_values
        
        # 计算损失
        loss = nn.MSELoss()(current_q_values.squeeze(), target_q_values)
        
        # 优化
        self.optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.policy_net.parameters(), 1.0)
        self.optimizer.step()
        
        # 更新目标网络
        self.update_counter += 1
        if self.update_counter % self.target_update == 0:
            self.target_net.load_state_dict(self.policy_net.state_dict())
        
        # 衰减epsilon
        self.epsilon = max(self.epsilon_end, self.epsilon * self.epsilon_decay)
        
        # 记录历史
        loss_value = loss.item()
        self.training_history["losses"].append(loss_value)
        self.training_history["epsilons"].append(self.epsilon)
        
        return loss_value
    
    def train_episode(self, env, max_steps: int = 1000) -> float:
        """训练一个回合"""
        state = env.reset()
        total_reward = 0
        
        for step in range(max_steps):
            # 选择动作
            action = self.select_action(state, training=True)
            
            # 执行动作
            next_state, reward, done, info = env.step(action)
            
            # 存储经验
            experience = RLExperience(
                state=state,
                action=action,
                reward=reward,
                next_state=next_state,
                done=done,
                info=info
            )
            self.store_experience(experience)
            
            # 训练
            loss = self.train_step()
            
            # 更新状态
            state = next_state
            total_reward += reward
            
            if done:
                break
        
        # 记录奖励
        self.training_history["rewards"].append(total_reward)
        
        return total_reward
    
    def save(self, path: str) -> None:
        """保存模型"""
        torch.save({
            'policy_net_state_dict': self.policy_net.state_dict(),
            'target_net_state_dict': self.target_net.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'epsilon': self.epsilon,
            'training_history': self.training_history
        }, path)
        logger.info(f"模型已保存: {path}")
    
    def load(self, path: str) -> None:
        """加载模型"""
        checkpoint = torch.load(path, map_location=self.device)
        self.policy_net.load_state_dict(checkpoint['policy_net_state_dict'])
        self.target_net.load_state_dict(checkpoint['target_net_state_dict'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        self.epsilon = checkpoint['epsilon']
        self.training_history = checkpoint['training_history']
        logger.info(f"模型已加载: {path}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "memory_size": len(self.memory),
            "epsilon": self.epsilon,
            "update_counter": self.update_counter,
            "avg_loss": np.mean(self.training_history["losses"][-100:]) if self.training_history["losses"] else 0,
            "avg_reward": np.mean(self.training_history["rewards"][-100:]) if self.training_history["rewards"] else 0
        }


class RLEnvironment:
    """强化学习环境基类"""
    
    def __init__(self):
        self.state_dim = None
        self.action_dim = None
        
    def reset(self) -> RLState:
        """重置环境"""
        raise NotImplementedError
    
    def step(self, action: RLAction) -> Tuple[RLState, float, bool, Dict[str, Any]]:
        """执行一步"""
        raise NotImplementedError
    
    def render(self) -> None:
        """渲染环境"""
        pass
    
    def close(self) -> None:
        """关闭环境"""
        pass


class TaskLearningEnvironment(RLEnvironment):
    """任务学习环境"""
    
    def __init__(self, task_complexity: float = 0.5):
        super().__init__()
        self.task_complexity = task_complexity
        self.state_dim = 10  # 状态维度
        self.action_dim = 5   # 动作维度
        self.current_state = None
        self.step_count = 0
        self.max_steps = 100
        
    def reset(self) -> RLState:
        """重置环境"""
        self.step_count = 0
        self.current_state = np.random.randn(self.state_dim) * self.task_complexity
        
        return RLState(
            observation=self.current_state,
            context={"step": self.step_count, "complexity": self.task_complexity}
        )
    
    def step(self, action: RLAction) -> Tuple[RLState, float, bool, Dict[str, Any]]:
        """执行一步"""
        self.step_count += 1
        
        # 模拟任务执行
        action_success = random.random() > (0.3 * self.task_complexity)
        
        if action_success:
            # 成功：向目标状态移动
            target_state = np.ones(self.state_dim)
            progress = 1.0 / (self.step_count + 1)
            next_state = self.current_state + (target_state - self.current_state) * progress
            reward = 1.0 - (self.step_count / self.max_steps)
        else:
            # 失败：随机扰动
            next_state = self.current_state + np.random.randn(self.state_dim) * 0.1
            reward = -0.5
        
        # 限制状态范围
        next_state = np.clip(next_state, -1.0, 1.0)
        self.current_state = next_state
        
        # 检查是否完成
        done = self.step_count >= self.max_steps or np.linalg.norm(next_state - np.ones(self.state_dim)) < 0.1
        
        next_rl_state = RLState(
            observation=next_state,
            context={"step": self.step_count, "success": action_success}
        )
        
        info = {
            "action_success": action_success,
            "progress": self.step_count / self.max_steps,
            "distance_to_target": np.linalg.norm(next_state - np.ones(self.state_dim))
        }
        
        return next_rl_state, reward, done, info


class ReinforcementLearningService:
    """强化学习服务"""
    
    def __init__(self):
        self.agents: Dict[str, DQNAgent] = {}
        self.environments: Dict[str, RLEnvironment] = {}
        
        logger.info("强化学习服务初始化完成")
    
    def create_agent(
        self,
        agent_id: str,
        state_dim: int,
        action_dim: int,
        **kwargs
    ) -> bool:
        """创建智能体"""
        if agent_id in self.agents:
            logger.warning(f"智能体已存在: {agent_id}")
            return False
        
        try:
            agent = DQNAgent(state_dim, action_dim, **kwargs)
            self.agents[agent_id] = agent
            logger.info(f"智能体创建成功: {agent_id}")
            return True
        except Exception as e:
            logger.error(f"智能体创建失败: {e}")
            return False
    
    def create_environment(
        self,
        env_id: str,
        env_type: str = "task_learning",
        **kwargs
    ) -> bool:
        """创建环境"""
        if env_id in self.environments:
            logger.warning(f"环境已存在: {env_id}")
            return False
        
        try:
            if env_type == "task_learning":
                env = TaskLearningEnvironment(**kwargs)
            else:
                raise ValueError(f"未知的环境类型: {env_type}")
            
            self.environments[env_id] = env
            logger.info(f"环境创建成功: {env_id}")
            return True
        except Exception as e:
            logger.error(f"环境创建失败: {e}")
            return False
    
    async def train_agent(
        self,
        agent_id: str,
        env_id: str,
        episodes: int = 100,
        max_steps: int = 1000
    ) -> Dict[str, Any]:
        """训练智能体"""
        if agent_id not in self.agents:
            return {"success": False, "error": f"智能体不存在: {agent_id}"}
        
        if env_id not in self.environments:
            return {"success": False, "error": f"环境不存在: {env_id}"}
        
        agent = self.agents[agent_id]
        env = self.environments[env_id]
        
        logger.info(f"开始训练智能体: {agent_id}, 环境: {env_id}, 回合数: {episodes}")
        
        episode_rewards = []
        
        for episode in range(episodes):
            total_reward = agent.train_episode(env, max_steps)
            episode_rewards.append(total_reward)
            
            if (episode + 1) % 10 == 0:
                logger.info(f"回合 {episode + 1}/{episodes}, 奖励: {total_reward:.2f}, 平均奖励: {np.mean(episode_rewards[-10:]):.2f}")
        
        stats = agent.get_stats()
        stats.update({
            "episodes": episodes,
            "final_avg_reward": np.mean(episode_rewards[-10:]),
            "max_reward": max(episode_rewards),
            "min_reward": min(episode_rewards)
        })
        
        return {
            "success": True,
            "stats": stats,
            "episode_rewards": episode_rewards
        }
    
    async def predict_action(
        self,
        agent_id: str,
        state: RLState,
        training: bool = False
    ) -> Optional[RLAction]:
        """预测动作"""
        if agent_id not in self.agents:
            logger.error(f"智能体不存在: {agent_id}")
            return None
        
        agent = self.agents[agent_id]
        return agent.select_action(state, training)
    
    def get_agent_stats(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """获取智能体统计信息"""
        if agent_id not in self.agents:
            return None
        
        return self.agents[agent_id].get_stats()
    
    def save_agent(self, agent_id: str, path: str) -> bool:
        """保存智能体"""
        if agent_id not in self.agents:
            return False
        
        try:
            self.agents[agent_id].save(path)
            return True
        except Exception as e:
            logger.error(f"智能体保存失败: {e}")
            return False
    
    def load_agent(self, agent_id: str, path: str) -> bool:
        """加载智能体"""
        try:
            # 如果智能体不存在，需要知道状态和动作维度
            if agent_id not in self.agents:
                # 这里需要从文件或配置中获取维度信息
                # 简化实现：创建默认智能体然后加载
                pass
            
            self.agents[agent_id].load(path)
            return True
        except Exception as e:
            logger.error(f"智能体加载失败: {e}")
            return False


# 全局强化学习服务实例
rl_service = ReinforcementLearningService()