# 帧数设置问题说明

## 问题

API 设置了 480 帧，但生成的视频只有 32 帧，或者执行失败。

## 根本原因

工作流中使用的 **AnimateDiff 模型**只支持固定的帧数（32 帧）。这是模型训练时的限制，不能通过 API 参数简单修改。

## 错误信息

当尝试使用非 32 帧（如 96 帧）时，ComfyUI 会报错：

```
RuntimeError: The size of tensor a (96) must match the size of tensor b (32) at non-singleton dimension 1
```

这个错误发生在 AnimateDiff 的位置编码 (positional encoding) 层，因为模型的 PE 是为 32 帧预训练的。

## 当前状态

- ✅ **参数正确传递**: API 正确地设置了 Node 552 (Number of Frames) 的值
- ✅ **连接正确**: EmptyLatentImage 的 `batch_size` 正确连接到 Node 552
- ✅ **ImageBatchMulti 修复**: `inputcount` 使用 widget 值而不是错误的连接
- ❌ **模型限制**: AnimateDiff 模型只支持 32 帧

## 解决方案

### 方案 1: 使用固定帧数（推荐）

修改 API 配置，将帧数限制为 32：

```json
{
  "num_frames_min": 32,
  "num_frames_max": 32
}
```

### 方案 2: 修改工作流

更换为支持可变帧数的模型/节点：

1. **使用 LTX-Video 模型**：支持更长的视频生成
2. **使用 Context Windows**：AnimateDiff 的上下文窗口功能
3. **使用其他视频生成节点**：如 SVD, I2VGen-XL 等

### 方案 3: 分段生成

如果需要生成长视频：
1. 将长视频分成多个 32 帧的片段
2. 每个片段独立生成
3. 使用视频拼接节点合并

## 验证测试

使用 32 帧测试：

```bash
python vj/tests/quick_test_debug.py
# 修改 num_frames 为 32
```

## 相关文件

- 错误日志: `BUG_FIX_FRAMES.md`
- 工作流: `user/default/workflows/i2v-low-res.json`
- AnimateDiff 节点: 工作流中的运动模块

## 技术细节

AnimateDiff 的位置编码维度：
- 时间维度: 32 (固定)
- 空间维度: 根据分辨率动态调整

当 `batch_size` != 32 时，位置编码无法正确广播，导致维度不匹配错误。
