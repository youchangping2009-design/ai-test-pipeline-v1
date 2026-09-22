# Testpoints View

- Project: `OSS-BLIND-R4`
- Work Item: `HOMEASSISTANT-182800`
- Truth Source: `testcases/case_plan.json`
- Projection Only: `true`

> This file is a review-friendly projection derived from `case_plan`; it is not a testcase truth source.

| 测试点ID | 页面 | 板块 | 模块 | 功能点 | 测试维度 | 测试点 | 核心断言 | 优先级 | 来源 CasePlan | 是否生成用例 |
|---|---|---|---|---|---|---|---|---|---|---|
| TP-001 | TTS 音频缓存处理 | MP3 标签写入与缓存回放 | TTS 音频标签 | ID3 标签合并 | data_persistence | 已有 ID3 的 MP3 更新后只保留一个有效 ID3 头 | ID3 解析器读取输出文件时不返回格式错误；输出文件中只存在一个有效 ID3 头。 | P0 | CP-001 | True |
| TP-002 | TTS 音频缓存处理 | MP3 标签写入与缓存回放 | TTS 音频标签 | ID3 标签合并 | data_persistence | 更新标签后保留原 TSSE 元数据 | 输出文件中的 TSSE 值与输入文件一致。 | P0 | CP-002 | True |
| TP-003 | TTS 音频缓存处理 | MP3 标签写入与缓存回放 | TTS 音频标签 | ID3 标签合并 | data_persistence | 标签处理不改变 MP3 音频帧 | 排除标签区域后，输出音频帧内容与输入一致；输出音频帧的稳定摘要与输入一致。 | P0 | CP-003 | True |
| TP-004 | TTS 音频缓存处理 | MP3 标签写入与缓存回放 | TTS 音频标签 | 缓存音频回放 | backend_job | 磁盘缓存中的已标记 MP3 可严格解码且非静音 | 严格 MP3 解码器产生至少一个音频样本；解码后的音频样本不是全静音。 | P0 | CP-004 | True |
| TP-005 | TTS 音频缓存处理 | MP3 标签写入与缓存回放 | TTS 音频标签 | ID3 标签合并 | backend_job | 无 ID3 的 MP3 可添加标签并保持可播放 | 输出文件包含所需标签；输出文件可被严格 MP3 解码器解码并产生非静音音频样本。 | P1 | CP-005 | True |
| TP-006 | TTS 音频缓存处理 | MP3 标签写入与缓存回放 | TTS 音频标签 | ID3 标签合并 | cross_surface_linkage | 已带标签音频处理结果不依赖 TTS provider | 两个 provider 的处理完成后，输出都只包含一个有效 ID3 头，保留各自 TSSE 和音频帧，并可由严格解码器产生至少一个非静音音频样本。 | P0 | CP-006 | True |
