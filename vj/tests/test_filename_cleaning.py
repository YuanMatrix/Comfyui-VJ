#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试文件名清理功能
"""

import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# 导入 sanitize_filename 函数
from vj.video_generation_api import sanitize_filename


def test_filename_sanitization():
    """测试各种问题文件名"""
    
    test_cases = [
        # (原始文件名, 期望结果描述)
        ("Max Richter - On the Nature of Daylight.mp3", "应该替换空格为下划线"),
        ("my song (remix).wav", "应该移除括号"),
        ("audio   file.mp3", "应该处理多个空格"),
        ("test@file#2024.flac", "应该移除特殊字符"),
        ("normal_file-v2.mp3", "不应该改变（已经是标准格式）"),
        ("测试音频.mp3", "应该移除中文字符"),
        ("   spaces.wav", "应该移除前导空格"),
        ("file!@#$%^&*()name.mp3", "应该移除所有特殊符号"),
        ("UPPERCASE FILE.WAV", "应该保留大写，替换空格"),
        ("file.name.with.dots.mp3", "应该保留文件名中的点"),
    ]
    
    print("=" * 80)
    print("🧪 文件名清理测试")
    print("=" * 80)
    print()
    
    passed = 0
    failed = 0
    
    for original, description in test_cases:
        cleaned = sanitize_filename(original)
        
        # 检查是否有空格（不应该有）
        has_spaces = ' ' in cleaned
        # 检查是否有非法字符
        import re
        has_illegal = bool(re.search(r'[^\w\-.]', cleaned))
        
        status = "✅" if not (has_spaces or has_illegal) else "❌"
        
        if not (has_spaces or has_illegal):
            passed += 1
        else:
            failed += 1
        
        print(f"{status} {description}")
        print(f"   原始: {original}")
        print(f"   清理: {cleaned}")
        
        if has_spaces:
            print(f"   ⚠️  仍包含空格！")
        if has_illegal:
            print(f"   ⚠️  仍包含非法字符！")
        
        print()
    
    print("=" * 80)
    print(f"📊 测试结果: {passed} 通过, {failed} 失败")
    print("=" * 80)
    
    return failed == 0


if __name__ == '__main__':
    success = test_filename_sanitization()
    sys.exit(0 if success else 1)
