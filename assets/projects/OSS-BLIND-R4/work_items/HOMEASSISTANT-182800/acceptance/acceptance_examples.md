# Acceptance Examples

| example_id | source_gate_ids | title | given | when | then | verification_side | oracle_strength | confidence | inference_basis |
|---|---|---|---|---|---|---|---|---|---|
| AE-001 | TG-001 | 已有 ID3 的 MP3 更新后只保留一个有效 ID3 头 | 准备一个已包含有效 ID3 标签和音频帧的 MP3。 | 写入 Home Assistant 所需标签并生成输出文件。 | 输出文件可被 ID3 解析器正常读取。<br>输出文件中只存在一个有效 ID3 头。 | TTS MP3 标签写入与文件解析层 | backend_job | confirmed |  |
| AE-002 | TG-002 | 更新标签后保留原 TSSE 元数据 | 准备一个包含确定 TSSE 值的已标记 MP3。 | 写入或更新 Home Assistant 标签。 | 输出文件中的 TSSE 值与输入文件一致。 | TTS MP3 元数据解析层 | backend_job | confirmed |  |
| AE-003 | TG-003 | 标签处理不改变 MP3 音频帧 | 准备一个音频帧内容和摘要已知的 MP3。 | 写入或更新 Home Assistant 标签。 | 排除标签区域后，输出音频帧内容与输入一致。<br>输出音频帧的稳定摘要与输入一致。 | TTS MP3 音频帧数据层 | backend_job | confirmed |  |
| AE-004 | TG-004 | 磁盘缓存中的已标记 MP3 可严格解码且非静音 | 已标记 MP3 先由内存路径生成，随后写入磁盘缓存。 | 从磁盘缓存读取文件并交给严格 MP3 解码器。 | 解码器成功产生音频样本。<br>解码后的音频样本不是全静音。 | TTS 磁盘缓存与音频解码层 | backend_job | confirmed |  |
| AE-005 | TG-005 | 无 ID3 的 MP3 可添加标签并保持可播放 | 准备一个不含 ID3 标签但可正常解码的 MP3。 | 写入 Home Assistant 所需标签并生成输出文件。 | 输出文件包含所需标签。<br>输出文件可被严格 MP3 解码器解码并产生非静音音频样本。 | TTS MP3 标签写入与音频解码层 | backend_job | confirmed |  |
| AE-006 | TG-006 | 已带标签音频处理结果不依赖 TTS provider | 准备来自两个不同 TTS provider、均已带标签且音频有效的 MP3。 | 对两个输入执行相同的 Home Assistant 标签处理。 | 两个输出都只包含一个有效 ID3 头。<br>两个输出都保留各自 TSSE、保持音频帧且可正常解码。 | TTS provider 兼容与 MP3 输出层 | business_behavior | confirmed |  |
