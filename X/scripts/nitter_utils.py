#!/usr/bin/env python3
"""
Nitter 实例管理工具
- 自动检测可用实例
- 支持 fallback 机制
- 记录实例健康状态
"""

import time
import json
import logging
from datetime import datetime
from pathlib import Path
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Nitter 实例列表（按稳定性排序）
NITTER_INSTANCES = [
    "https://nitter.tiekoetter.com",
    "https://nitter.privacyredirect.com",
    "https://nitter.net",
]

# 健康状态缓存（秒）
HEALTH_CACHE_FILE = Path(__file__).parent / "nitter_health_cache.json"
HEALTH_CACHE_TTL = 300  # 5 分钟


def load_health_cache():
    """加载健康状态缓存"""
    if HEALTH_CACHE_FILE.exists():
        try:
            with open(HEALTH_CACHE_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return {}


def save_health_cache(cache):
    """保存健康状态缓存"""
    with open(HEALTH_CACHE_FILE, "w") as f:
        json.dump(cache, f)


def check_instance_health(instance, timeout=10):
    """检查单个实例健康状态（使用 curl 避免 Python requests 被拦截）"""
    import subprocess
    try:
        result = subprocess.run(
            ["curl", "-s", "--max-time", str(timeout),
             f"{instance}/elonmusk"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0 and result.stdout:
            content = result.stdout
            # 有效的 Nitter 实例应该包含实际推文数据
            indicators = ["timeline-item", "tweet-content", "profile-card", "pinned"]
            has_content = any(ind in content for ind in indicators)
            is_bot_page = "Making sure you're not a bot" in content
            return has_content and not is_bot_page and len(content) > 2000
        return False
    except Exception:
        return False


def get_best_instance(force_refresh=False):
    """
    获取最健康的 Nitter 实例
    - 优先返回缓存中健康的实例
    - 如果缓存过期或全部不健康，重新检测
    - 返回第一个可用的实例
    """
    import json

    cache = load_health_cache()
    now = time.time()

    # 检查缓存是否有效
    if not force_refresh and cache:
        cached_instance = cache.get("best_instance")
        cached_time = cache.get("timestamp", 0)

        if now - cached_time < HEALTH_CACHE_TTL and cached_instance:
            # 验证缓存的实例是否仍然可用
            if check_instance_health(cached_instance, timeout=3):
                logger.info(f"使用缓存实例: {cached_instance}")
                return cached_instance

    # 重新检测所有实例
    for instance in NITTER_INSTANCES:
        if check_instance_health(instance):
            # 保存健康状态
            cache = {
                "best_instance": instance,
                "timestamp": now,
            }
            save_health_cache(cache)
            logger.info(f"检测到可用实例: {instance}")
            return instance

    # 全部失败，返回第一个（兜底）
    logger.warning("所有实例均不可用，返回兜底实例")
    return NITTER_INSTANCES[0]


def test_all_instances():
    """测试所有实例的可用性"""
    results = []
    for instance in NITTER_INSTANCES:
        status = check_instance_health(instance)
        results.append({
            "instance": instance,
            "available": status,
            "timestamp": datetime.now().isoformat(),
        })
        print(f"{'✅' if status else '❌'} {instance}")
        time.sleep(0.5)  # 避免请求过快

    return results


def get_instance_stats():
    """获取实例统计信息"""
    return {
        "total": len(NITTER_INSTANCES),
        "instances": NITTER_INSTANCES,
        "cache_file": str(HEALTH_CACHE_FILE),
        "cache_ttl": HEALTH_CACHE_TTL,
    }


if __name__ == "__main__":
    print("🔍 测试 Nitter 实例健康状态...")
    results = test_all_instances()
    print(f"\n📊 统计: {sum(1 for r in results if r['available'])}/{len(results)} 实例可用")
    print(f"\n🏆 最佳实例: {get_best_instance()}")