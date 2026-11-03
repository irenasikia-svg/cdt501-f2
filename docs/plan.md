# CDT501 · F2 计划 (docs/plan.md)

> 研究问题：文档 Agent 能否在包含恶意隐藏指令的文档下，既挡住注入攻击，又完成合法任务？
> 本计划依据 `F2_ClaudeCode_Kickoff_Prompt.md`，P0 阶段产出。所有数字在有 `results/` 文件之前一律写 TBD。

## 1. P0 已确认的约束

| 项目 | 决定 |
|---|---|
| LLM 后端 | OpenRouter 免费模型优先（`:free` 系列），DeepSeek 官方 API 作为低价后备。两者都走同一个 OpenAI 兼容客户端，只换 `base_url` / `model`。Anthropic 客户端保留但可选。 |
| 预算 | 尽量 0 元。开发和 `check.sh` 全部用确定性 mock 后端，不消耗 API。真实模型只在 P6 跑，跑前打印估算调用数/token 并等 ced 确认。 |
| 小组 | 4 人。held-out 测试集暂定由 ced 编写和冻结。 |
| 截止 | 约 2026-11-18（距今 15 天）。 |
| Demo | 现场演示 + 录屏都要。Streamlit 带离线 replay 模式，录屏用 replay 录，现场不依赖网络。 |
| 代码托管 | GitHub 仓库 `irenasikia-svg/cdt501-f2`（公开）。组员 clone 后 `uv sync` + `scripts/check.sh` 即可复现。 |

## 2. 免费模型的风险与对策

- 免费模型有速率和每日次数上限，且可能随时下线或换版本。对策：每次运行记录精确 model id；客户端内置限速和重试；k=3 重复所需调用量在 P6 先估算，超出免费额度时缩小真实模型实验的范围（例如只跑 C1 vs C2），并在报告中写明。
- 免费模型的 tool-calling 支持不一。P3 先用一个小探针确认所选模型能稳定输出工具调用；不行就换模型或用 DeepSeek 付费 API（单价低）。
- 结论的主要证据来自 `mock_gullible`（最坏情况）：它证明拦截不依赖模型是否听话。真实模型结果作为补充。

## 3. 系统设计（按 Kickoff §3 实现，暂无改动提议）

```
可信用户任务 → 能力清单(manifest) → Agent 循环 → 提议的工具调用
   → 策略引擎(工具白名单 / 参数检查 / 污点规则 / 默认只读) → 模拟 sink 或拦截 → 审计日志
```

- `sandbox/`：约 20 份模拟文档（中英混合，含繁体），`secrets/` 含 `CANARY-xxxxxxxx`，所有危险工具只写本地日志，域名只用 `*.example` / `*.invalid`。
- 工具：8 个 pydantic 类型化工具，每个结果带来源标签 `trusted_user` / `untrusted_doc` / `secret`。
- 条件：C0 none、C1 prompt_only（官方基线）、C2 policy（我们的方法）、A1 无污点规则、A2 无参数检查、D 仅检测器（单独报告）。
- 策略在 Python 中强制执行，未知工具/未知参数/解析失败一律拒绝（fail closed）。

建议的仓库结构：

```
src/f2agent/{sandbox,tools,agent,llm,policy,detector,eval}/
sandbox/  data/{benign,dev_attacks,heldout}/  results/  logs/  docs/  scripts/  tests/  app.py
```

## 4. 评测（P6 前先写并冻结 `docs/eval_protocol.md`）

ASR、BU、UA、误拦截率、延迟（中位数/p90）、token/成本、覆盖率。真实模型 k≥3，给均值和 95% bootstrap CI；mock k=1。数据按攻击家族划分 dev / held-out。

**需要组内商定的阈值**：`check.sh` 中 C2 BU 的最低值。建议先定 BU(C2, mock_compliant) ≥ 0.9，P5 后视数据调整并记录原因。

## 5. 时间表（15 天，每阶段结束停下等 ced 确认）

| 阶段 | 内容 | 目标日期 |
|---|---|---|
| P0 | 计划（本文件） | 11-03 |
| P1 | 仓库骨架、AGENTS.md、check.sh 骨架、文档模板 | 11-04 |
| P2 | 沙箱 + 类型化工具 + 审计日志（TDD） | 11-05 |
| P3 | Agent 循环 + 后端 + C0/C1（mock 对比） | 11-06 |
| P4 | 策略引擎 C2 + A1/A2 + 检测器 D + 属性测试 + 安全审查 | 11-08 |
| P5 | 良性任务 ~40 + dev 攻击 + 检查器 + held-out 模板 + 冻结工具 | 11-10 |
| — | **ced 编写并冻结 held-out 集** | 11-11 ~ 11-12 |
| P6 | 评测：全量 mock → 确认后真实模型 → 汇总/图表/失败案例 | 11-13 |
| P7 | Streamlit Demo + replay，录屏 | 11-15 |
| P8 | README、架构图（Mermaid + PNG）、结果表、ai_assistance | 11-16 |
| 缓冲 | 报告撰写、排练 | 11-17 ~ 11-18 |

## 6. 环境说明

- 我在云端容器里开发，`superpowers` 系列 skill 可用。Kickoff §0 中 trailofbits 的 `property-based-testing` / `insecure-defaults` / `sharp-edges` 在此环境未安装：P4 会按同样方法手工完成（Hypothesis 属性测试 + 针对 fail-open 路径的人工审查），并在 `docs/security_review.md` 和 `docs/ai_assistance.md` 中如实注明。组员若在本地 Claude Code 装了这些 skill，可以复跑一次作交叉验证。
- 提交作者统一为 `ced`。API key 只放 `.env`，不提交。

## 7. 待 ced 确认

1. 仓库名（建议 `cdt501-f2`）和公开/私有。
2. C2 BU 阈值（建议 0.9）。
3. 时间表是否可行。
