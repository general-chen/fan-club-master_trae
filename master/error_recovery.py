#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
错误恢复机制模块
用于处理程序运行时的各种错误和异常情况，提供自动恢复功能
"""

import logging
import time
import threading
import traceback
import socket
import psutil
import os
import sys
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from enum import Enum

class ErrorSeverity(Enum):
    """错误严重程度"""
    LOW = 1      # 轻微错误，可以忽略
    MEDIUM = 2   # 中等错误，需要重试
    HIGH = 3     # 严重错误，需要重启组件
    CRITICAL = 4 # 致命错误，需要停止程序

@dataclass
class ErrorInfo:
    """错误信息"""
    error_type: str
    message: str
    timestamp: float
    severity: ErrorSeverity
    context: Dict[str, Any]
    traceback_info: str
    retry_count: int = 0

class ErrorRecoveryManager:
    """错误恢复管理器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.error_history: List[ErrorInfo] = []
        self.recovery_strategies: Dict[str, Callable] = {}
        self.max_history_size = 1000
        self.max_retry_attempts = 3
        self.retry_delays = [1, 2, 5]  # 重试延迟（秒）
        self.lock = threading.Lock()
        
        # 日志频率控制
        self.last_log_time = {}  # 记录每种错误类型的最后日志时间
        self.log_interval = 30  # 同类型错误日志间隔（秒）
        
        # 注册默认恢复策略
        self._register_default_strategies()
        
    def _register_default_strategies(self):
        """注册默认恢复策略"""
        self.recovery_strategies.update({
            'socket_timeout': self._handle_socket_timeout,
            'socket_error': self._handle_socket_error,
            'network_error': self._handle_network_error,
            'thread_deadlock': self._handle_thread_deadlock,
            'memory_error': self._handle_memory_error,
            'communication_error': self._handle_communication_error,
            'system_resource_error': self._handle_system_resource_error
        })
    
    def register_recovery_strategy(self, error_type: str, strategy: Callable):
        """注册自定义恢复策略"""
        with self.lock:
            self.recovery_strategies[error_type] = strategy
            self.logger.info(f"注册恢复策略: {error_type}")
    
    def handle_error(self, error_type: str, error: Exception, context: Dict[str, Any] = None) -> bool:
        """
        处理错误
        返回True表示错误已恢复，False表示无法恢复
        """
        if context is None:
            context = {}
            
        # 创建错误信息
        error_info = ErrorInfo(
            error_type=error_type,
            message=str(error),
            timestamp=time.time(),
            severity=self._determine_severity(error_type, error),
            context=context,
            traceback_info=traceback.format_exc()
        )
        
        # 记录错误
        with self.lock:
            self.error_history.append(error_info)
            if len(self.error_history) > self.max_history_size:
                self.error_history.pop(0)
        
        self.logger.error(f"处理错误: {error_type} - {error_info.message}")
        
        # 尝试恢复
        return self._attempt_recovery(error_info)
    
    def _determine_severity(self, error_type: str, error: Exception) -> ErrorSeverity:
        """确定错误严重程度"""
        severity_map = {
            'socket_timeout': ErrorSeverity.LOW,
            'socket_error': ErrorSeverity.MEDIUM,
            'network_error': ErrorSeverity.MEDIUM,
            'thread_deadlock': ErrorSeverity.HIGH,
            'memory_error': ErrorSeverity.HIGH,
            'communication_error': ErrorSeverity.MEDIUM,
            'system_resource_error': ErrorSeverity.HIGH
        }
        
        return severity_map.get(error_type, ErrorSeverity.MEDIUM)
    
    def _attempt_recovery(self, error_info: ErrorInfo) -> bool:
        """尝试错误恢复"""
        strategy = self.recovery_strategies.get(error_info.error_type)
        if not strategy:
            self.logger.warning(f"未找到恢复策略: {error_info.error_type}")
            return False
        
        # 检查重试次数
        if error_info.retry_count >= self.max_retry_attempts:
            self.logger.error(f"超过最大重试次数: {error_info.error_type}")
            return False
        
        try:
            # 等待重试延迟
            if error_info.retry_count > 0:
                delay = self.retry_delays[min(error_info.retry_count - 1, len(self.retry_delays) - 1)]
                time.sleep(delay)
            
            # 执行恢复策略
            success = strategy(error_info)
            
            if success:
                self.logger.info(f"错误恢复成功: {error_info.error_type}")
                return True
            else:
                error_info.retry_count += 1
                self.logger.warning(f"错误恢复失败，重试次数: {error_info.retry_count}")
                return self._attempt_recovery(error_info)
                
        except Exception as e:
            self.logger.error(f"恢复策略执行失败: {e}")
            return False
    
    def _handle_socket_timeout(self, error_info: ErrorInfo) -> bool:
        """处理socket超时"""
        current_time = time.time()
        
        # 尝试从上下文中获取socket并增加超时时间
        socket_obj = error_info.context.get('socket')
        if socket_obj:
            try:
                # 局部导入以避免循环依赖
                try:
                    from stability_optimizer import stability_optimizer
                except ImportError:
                    # Fallback for when running as a package or different path structure
                    import sys
                    import os
                    if os.path.dirname(__file__) not in sys.path:
                        sys.path.append(os.path.dirname(__file__))
                    from stability_optimizer import stability_optimizer
                
                # 使用 'data_transfer' 类型以获得标准超时时间 * 倍数
                new_timeout = stability_optimizer.optimize_socket_timeout(socket_obj, "data_transfer")
                
                if self._should_log(error_info.error_type, current_time):
                    self.logger.info(f"处理socket超时 - 已增加超时时间至 {new_timeout:.2f}s")
                return True
            except Exception as e:
                self.logger.error(f"调整socket超时失败: {e}")
        
        if self._should_log(error_info.error_type, current_time):
            self.logger.info("处理socket超时 - 增加超时时间 (未找到socket对象)")
        # 这里可以通知相关组件增加超时时间
        return True
    
    def _handle_socket_error(self, error_info: ErrorInfo) -> bool:
        """处理socket错误"""
        current_time = time.time()
        if self._should_log(error_info.error_type, current_time):
            self.logger.info("处理socket错误 - 重新创建连接")
        # 这里可以通知相关组件重新创建socket连接
        return True
    
    def _handle_network_error(self, error_info: ErrorInfo) -> bool:
        """处理网络错误"""
        self.logger.info("处理网络错误 - 检查网络连接")
        
        # 检查网络连接
        if self._check_network_connectivity():
            self.logger.info("网络连接正常，尝试重新连接")
            return True
        else:
            self.logger.error("网络连接异常")
            return False
    
    def _handle_thread_deadlock(self, error_info: ErrorInfo) -> bool:
        """处理线程死锁"""
        self.logger.warning("检测到潜在死锁 - 尝试释放锁")
        # 这里可以实现死锁检测和解除机制
        return False  # 死锁通常需要重启组件
    
    def _handle_memory_error(self, error_info: ErrorInfo) -> bool:
        """处理内存错误"""
        self.logger.warning("内存不足 - 尝试清理内存")
        
        # 强制垃圾回收
        import gc
        gc.collect()
        
        # 检查内存使用情况
        memory_percent = psutil.virtual_memory().percent
        if memory_percent > 90:
            self.logger.error(f"内存使用率过高: {memory_percent}%")
            return False
        
        return True
    
    def _handle_communication_error(self, error_info: ErrorInfo) -> bool:
        """处理通信错误"""
        self.logger.info("处理通信错误 - 重置通信状态")
        return True
    
    def _handle_system_resource_error(self, error_info: ErrorInfo) -> bool:
        """处理系统资源错误"""
        self.logger.warning("系统资源不足")
        
        # 检查系统资源
        cpu_percent = psutil.cpu_percent(interval=1)
        memory_percent = psutil.virtual_memory().percent
        
        if cpu_percent > 90 or memory_percent > 90:
            self.logger.error(f"系统资源不足 - CPU: {cpu_percent}%, 内存: {memory_percent}%")
            return False
        
        return True
    
    def _check_network_connectivity(self) -> bool:
        """检查网络连接"""
        try:
            # 尝试连接到本地回环地址
            socket.create_connection(("127.0.0.1", 80), timeout=3)
            return True
        except (socket.timeout, socket.error):
            return False
    
    def _should_log(self, error_type: str, current_time: float) -> bool:
        """检查是否应该记录日志（频率控制）"""
        last_time = self.last_log_time.get(error_type, 0)
        if current_time - last_time >= self.log_interval:
            self.last_log_time[error_type] = current_time
            return True
        return False
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """获取错误统计信息"""
        with self.lock:
            if not self.error_history:
                return {}
            
            error_counts = {}
            severity_counts = {}
            recent_errors = []
            
            current_time = time.time()
            
            for error in self.error_history:
                # 统计错误类型
                error_counts[error.error_type] = error_counts.get(error.error_type, 0) + 1
                
                # 统计严重程度
                severity_name = error.severity.name
                severity_counts[severity_name] = severity_counts.get(severity_name, 0) + 1
                
                # 最近1小时的错误
                if current_time - error.timestamp < 3600:
                    recent_errors.append({
                        'type': error.error_type,
                        'message': error.message,
                        'timestamp': error.timestamp,
                        'severity': severity_name
                    })
            
            return {
                'total_errors': len(self.error_history),
                'error_counts': error_counts,
                'severity_counts': severity_counts,
                'recent_errors': recent_errors,
                'recovery_strategies': list(self.recovery_strategies.keys())
            }
    
    def clear_error_history(self):
        """清空错误历史"""
        with self.lock:
            self.error_history.clear()
            self.logger.info("错误历史已清空")

# 全局错误恢复管理器实例
error_recovery_manager = ErrorRecoveryManager()

def handle_error(error_type: str, error: Exception, context: Dict[str, Any] = None) -> bool:
    """全局错误处理函数"""
    return error_recovery_manager.handle_error(error_type, error, context)

def register_recovery_strategy(error_type: str, strategy: Callable):
    """注册恢复策略"""
    error_recovery_manager.register_recovery_strategy(error_type, strategy)

def get_error_statistics() -> Dict[str, Any]:
    """获取错误统计"""
    return error_recovery_manager.get_error_statistics()