# HOMEASSISTANT-182800 公开需求快照

- 来源：https://github.com/home-assistant/core/pull/182800
- 标题：Fix duplicate ID3 tag when tagging TTS audio
- 状态：已合并
- 目标分支：`dev`
- 作者：`bboe`
- 冻结日期：2026-09-22

## 可作为需求输入的行为事实

- 当输入 MP3 已含 ID3 标签时，SpeechManager 写入标签会产生两个 ID3 头。
- FFmpeg 生成的 MP3 默认可能已有 TSSE 标签，因此缓存的 TTS MP3 会触发该问题。
- 首次内存播放可以正常，但内存缓存清理后从磁盘读取的重复标签文件可能被严格解码器静音，即使播放器报告成功。
- 目标是最终仅有一个 ID3 标签，同时保留已有 TSSE 元数据与音频内容。
- 修复应与 TTS provider 无关，适用于任何已经带标签的音频输入。

## 盲测隔离

本快照不包含代码 diff、具体修复方式、测试夹具、测试断言、提交或 Review 评论。上述信息仅允许在后续 Oracle 阶段使用。
