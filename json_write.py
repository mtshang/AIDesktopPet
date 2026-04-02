# 文件名：json_write.py

import os
import json

def save_config_atomic(config, file_path):
    """
    工业级原子化写入 JSON 配置文件
    彻底杜绝断电、死机导致的文件损坏变 0 字节问题
    """
    dir_name = os.path.dirname(file_path)
    os.makedirs(dir_name, exist_ok=True)
    
    # 1. 设定一个临时文件路径
    temp_path = file_path + ".tmp"
    
    try:
        # 2. 先把数据安安全全地写到临时文件里
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
            
            # 【核心防御】：强迫操作系统把缓冲区的数据立刻、马上刷入物理硬盘！
            f.flush()
            os.fsync(f.fileno()) 
            
        # 3. 数据安全落地后，执行原子级替换（瞬间用 .tmp 覆盖原文件）
        # os.replace 在 Windows 和 Linux 上都是原子操作，极其安全
        os.replace(temp_path, file_path)
        
    except Exception as e:
        print(f"⚠️ 致命防御：写入配置文件失败，但原文件已保住！错误：{e}")
        # 如果写入中途报错，清理掉那个可能损坏的临时文件，原文件安然无恙
        if os.path.exists(temp_path):
            os.remove(temp_path)

