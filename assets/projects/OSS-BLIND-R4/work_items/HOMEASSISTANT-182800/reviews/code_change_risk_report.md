# Home Assistant #182800 盲测 Oracle 对照报告

生成时间：2026-09-22
Oracle：[home-assistant/core#182800](https://github.com/home-assistant/core/pull/182800)，head `e1734829562dc7ba54f5a4ac4e944772722cdf42`

## 结论

6 条冻结用例覆盖已有 ID3 输入只保留单一标签、TSSE 与音频内容保留、磁盘缓存回放、无标签输入兼容及 provider 无关性。没有范围过伸，也没有新增 design feedback。

## 证据

| 位置 | Oracle 行为 | 盲测承接 | 结论 |
|---|---|---|---|
| `homeassistant/components/tts/__init__.py` | `tts_file.save` 前把流位置重置到 0 | CP-001～CP-003 | 命中 |
| `tests/components/tts/test_init.py` | 已有一个 ID3 头的真实 MP3 处理后仍只有一个 | CP-001 | 命中 |
| PR 行为说明 | TSSE 与音频不变，磁盘缓存重复播放恢复 | CP-002～CP-004 | 命中 |
| 通用 `write_tags` 路径 | 无标签输入与多 provider 兼容回归 | CP-005、CP-006 | 相关回归 |

## 验证层级

- L0：8 类资产 SHA-256 已冻结，Oracle 未参与生成。
- L1：检查固定 head 的 3 个 changed files、实现 diff 与新增回归测试。
- L2：未 checkout Home Assistant 上游源码，未在本地运行其测试。

本报告不修改 Case Plan 或正式 testcase。
