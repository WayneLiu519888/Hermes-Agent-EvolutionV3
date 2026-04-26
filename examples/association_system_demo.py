#!/usr/bin/env python3
"""
关联发现和优化系统使用示例
"""

import os
import sys
import tempfile
from datetime import datetime

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.evolution.memory.database import AssociationDatabase
from src.evolution.memory.association_discoverer import AssociationDiscoverer
from src.evolution.memory.association_optimizer import AssociationOptimizer

def main():
    """主函数"""
    print("🔍 HermesAgentEvolution - 关联发现和优化系统示例")
    print("=" * 60)
    
    # 使用临时数据库文件
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as temp_db:
        db_path = temp_db.name
    
    try:
        # 1. 初始化组件
        print("\n1. 初始化组件...")
        db = AssociationDatabase(db_path)
        discoverer = AssociationDiscoverer(db_path)
        optimizer = AssociationOptimizer(db_path)
        
        print("   ✅ 数据库初始化完成")
        print("   ✅ 关联发现器初始化完成")
        print("   ✅ 关联优化器初始化完成")
        
        # 2. 添加示例记忆条目
        print("\n2. 添加示例记忆条目...")
        
        entries = [
            ("Python是一种高级编程语言", "text", {"category": "programming", "language": "Python"}),
            ("机器学习是人工智能的一个分支", "text", {"category": "ai", "subfield": "ML"}),
            ("数据分析涉及收集、处理和解释数据", "text", {"category": "data", "skill": "analysis"}),
            ("Web开发包括前端和后端技术", "text", {"category": "web", "type": "development"}),
            ("深度学习基于神经网络", "text", {"category": "ai", "subfield": "DL"}),
            ("SQL用于数据库查询", "text", {"category": "database", "language": "SQL"}),
        ]
        
        entry_ids = []
        for content, content_type, metadata in entries:
            entry_id = db.add_memory_entry(content, content_type, metadata)
            entry_ids.append(entry_id)
            print(f"   添加: {content[:30]}... (ID: {entry_id})")
        
        # 3. 发现关联
        print("\n3. 发现关联关系...")
        discovery_result = discoverer.discover_all()
        
        print(f"   发现了 {discovery_result.get('total_associations', 0)} 个关联")
        
        # 显示每种方法的发现结果
        methods_result = discovery_result.get('methods', {})
        for method, result in methods_result.items():
            count = result.get('new_associations', 0)
            if count > 0:
                print(f"   {method}: 发现了 {count} 个关联")
        
        # 4. 优化关联
        print("\n4. 优化关联关系...")
        optimization_result = optimizer.optimize_all_associations()
        
        print(f"   优化了 {optimization_result.associations_optimized} 个关联")
        print(f"   删除了 {optimization_result.associations_removed} 个低质量关联")
        print(f"   平均强度变化: {optimization_result.average_strength_change:+.3f}")
        print(f"   平均置信度变化: {optimization_result.average_confidence_change:+.3f}")
        
        # 5. 获取推荐
        print("\n5. 获取智能推荐...")
        for i, entry_id in enumerate(entry_ids[:3]):  # 为前3个条目获取推荐
            recommendations = optimizer.get_recommendations(entry_id, limit=3)
            
            if recommendations:
                # 获取条目内容
                entry = db.get_memory_entry(entry_id)
                content_preview = entry['content'][:20] + "..." if len(entry['content']) > 20 else entry['content']
                
                print(f"\n   为条目 '{content_preview}' 的推荐:")
                for j, rec in enumerate(recommendations, 1):
                    print(f"     {j}. {rec['content'][:30]}...")
                    print(f"        类型: {rec['association_type']}, "
                          f"强度: {rec['strength']:.3f}, "
                          f"置信度: {rec['confidence']:.3f}")
        
        # 6. 分析模式
        print("\n6. 分析关联模式...")
        patterns = optimizer.analyze_patterns()
        
        if patterns:
            print(f"   发现了 {len(patterns)} 个模式:")
            for i, pattern in enumerate(patterns, 1):
                pattern_type = pattern.get('pattern_type', 'unknown')
                confidence = pattern.get('confidence', 0)
                support = pattern.get('support_count', 0)
                print(f"     {i}. {pattern_type} (置信度: {confidence:.3f}, 支持数: {support})")
        
        # 7. 获取统计信息
        print("\n7. 系统统计信息...")
        stats = optimizer.get_optimization_stats()
        
        print(f"   总记忆条目: {stats.get('total_memory_entries', 0)}")
        print(f"   总关联数: {stats.get('total_associations', 0)}")
        print(f"   平均关联强度: {stats.get('average_strength', 0):.3f}")
        print(f"   平均置信度: {stats.get('average_confidence', 0):.3f}")
        
        quality_dist = {
            '高质量': stats.get('high_quality_count', 0),
            '中等质量': stats.get('medium_quality_count', 0),
            '低质量': stats.get('low_quality_count', 0)
        }
        
        print("   关联质量分布:")
        for quality, count in quality_dist.items():
            if stats['total_associations'] > 0:
                percentage = (count / stats['total_associations']) * 100
                print(f"     {quality}: {count} ({percentage:.1f}%)")
        
        # 8. 清理低质量关联
        print("\n8. 清理低质量关联...")
        removed_count = optimizer.cleanup_low_quality_associations(min_quality_score=0.3)
        print(f"   清理了 {removed_count} 个低质量关联")
        
        # 最终统计
        final_stats = optimizer.get_optimization_stats()
        print(f"\n   最终关联数: {final_stats.get('total_associations', 0)}")
        
    finally:
        # 清理临时文件
        if os.path.exists(db_path):
            os.unlink(db_path)
    
    print("\n" + "=" * 60)
    print("✅ 示例运行完成!")
    print("\n系统功能验证:")
    print("  ✓ 记忆条目管理")
    print("  ✓ 关联自动发现")
    print("  ✓ 关联智能优化")
    print("  ✓ 智能推荐系统")
    print("  ✓ 模式分析")
    print("  ✓ 质量监控和清理")

if __name__ == "__main__":
    main()