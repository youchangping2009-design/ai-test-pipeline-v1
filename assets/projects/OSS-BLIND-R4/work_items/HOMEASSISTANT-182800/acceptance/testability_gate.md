# Testability Gate

| gate_id | source_rule_id | classification | testability | decision | confidence | source_text | reason |
|---|---|---|---|---|---|---|---|
| TG-001 | HA-R001 | backend_job | testable | generate_acceptance_example | confirmed | 已带 ID3 标签的 MP3 写入 Home Assistant 标签后只能保留一个有效 ID3 头。 | 可解析输出文件并确定性统计有效 ID3 头数量。 |
| TG-002 | HA-R002 | backend_job | testable | generate_acceptance_example | confirmed | 更新标签时必须保留输入中的 TSSE 元数据。 | 可在处理前后读取并比较 TSSE 标签。 |
| TG-003 | HA-R003 | backend_job | testable | generate_acceptance_example | confirmed | 标签处理不得改变 MP3 音频帧内容。 | 可排除标签区后比较音频帧内容或其稳定摘要。 |
| TG-004 | HA-R004 | backend_job | testable | generate_acceptance_example | confirmed | 缓存文件从内存路径切换为磁盘读取后仍应可被严格解码器正常播放，不能静音。 | 可控制缓存切换并对磁盘文件执行实际解码与非静音断言。 |
| TG-005 | HA-R005 | backend_job | testable | generate_acceptance_example | confirmed | 未带 ID3 标签的 MP3 仍可添加所需标签并保持可播放。 | 可提供无标签输入并检查标签与音频解码结果。 |
| TG-006 | HA-R006 | third_party_capability | testable | generate_acceptance_example | confirmed | 已带标签音频的处理结果不应依赖具体 TTS provider。 | 可使用不同来源但等价的已带标签 MP3 比较相同输出不变量。 |
| TG-007 | RISK-001 | risk_hardening | risk_only | risk_note_only | confirmed | 标签版本、扩展头、padding 或异常标签可能影响合并兼容性。 | 公开需求未定义支持矩阵和损坏输入策略，保留为兼容风险。 |
| TG-008 | RISK-002 | risk_hardening | risk_only | risk_note_only | confirmed | 只验证播放器返回成功可能漏掉静音，应检查实际可解码音频。 | 正式可播放结果由 HA-R004 承接，本项约束测试 Oracle 质量。 |
| TG-009 | RISK-003 | risk_hardening | risk_only | risk_note_only | confirmed | 处理过程若重编码音频会引入不必要的质量与性能回退。 | 音频内容保真由 HA-R003 承接，未声明性能阈值不生成强验收。 |
| TG-010 | RISK-004 | risk_hardening | risk_only | risk_note_only | confirmed | 对未带标签输入的兼容路径也可能被标签定位逻辑影响。 | 无标签兼容行为由 HA-R005 正式承接，此项仅保留回归提示。 |
