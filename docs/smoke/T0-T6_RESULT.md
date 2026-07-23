# T0–T6：ChatGPT Web Supervisor + GitHub Actions Executor + Codex Thin Worker 最小链路测试结果

## 1. 最终状态

```yaml
test_scope: T0-T6
status: PASS_WITH_WEB_SUPERVISOR_PR_FALLBACK
production_repo_modified: false
relay_secret_exposed: false
relay_endpoint_exposed: false
codex_action_verified: true
incident_notification_emitted: true
```

本测试在公开隔离仓库 `tyxq428/temp_test` 中完成。正式仓库 `tyxq428/ashare_f10_scrapper` 未被修改。

## 2. 最终通过链路

```text
GitHub Environment Secrets
→ Secret-safe T0 preflight
→ Streaming Responses API T1 handshake
→ localhost-only no-log endpoint normalizer
→ openai/codex-action@v1
→ Codex Thin Worker edits one allowed file
→ deterministic scope and result verification
→ secret-free patch artifact
→ separate write-capable publish job
→ isolated branch push
→ ChatGPT Web Supervisor creates Draft PR
→ independent public-log secret audit
→ assigned interruption notification Issue
```

## 3. 验收矩阵

| Gate | 结果 | 证据 |
|---|---|---|
| T0：Secret、HTTPS 与配置预检 | PASS | Workflow run `29974972105`, `connectivity` job |
| T1：Streaming Responses API | PASS | Workflow run `29974972105`, `connectivity` job |
| T2：`openai/codex-action@v1` | PASS | Workflow run `29974972105`, `codex-thin-worker` job |
| 根级 `AGENTS.md` | PASS | 结构化结果与确定性 verifier |
| Scoped `smoke/AGENTS.md` | PASS | 结构化结果与确定性 verifier |
| 只修改允许文件 | PASS | 仅 `smoke/output.txt` 发生产品变更 |
| 输出内容 | PASS | `result=42` |
| Secret-bearing job 仓库权限 | PASS | `contents: read` |
| Secret-free patch handoff | PASS | Artifact leak audit 与 patch replay |
| Secret-free publish job | PASS | 分支 `smoke/codex-thin-worker-29974972105` 已成功 push |
| Action 自动创建 PR | BLOCKED | 当前仓库设置不允许 GitHub Actions 创建 PR |
| ChatGPT Web Supervisor 创建 PR | PASS | Draft PR `#9` |
| Public workflow log audit | PASS | Issue `#8`，run `29974972105` |
| T6 中断通知生成与指派 | PASS | Issue `#10`，run `29975116933` |

## 4. 重要发现

### 4.1 Environment 中保存的是 base URL 也可以安全兼容

初次 T0 发现 Secret 中保存的 endpoint 并非完整 `/responses` 地址。没有要求用户修改或公开 Secret，而是在 Runner 内增加确定性 URL normalizer，将合法 HTTPS base URL 私下归一为 Responses endpoint。

正式架构应保留这一能力，不强迫 Secret 必须采用唯一字符串格式。

### 4.2 Codex Action 不应直接看到真实中转站 URL

最终通过版本在 Runner 内启动一个仅绑定 `127.0.0.1` 的无日志转发器：

```text
openai/codex-action@v1
→ http://127.0.0.1:8787/v1/responses
→ private forwarder
→ Environment Secret 中的真实 endpoint
```

因此：

- Public workflow 不包含真实 URL；
- Codex Action 参数不包含真实 URL；
- Codex 自身错误日志最多只能看到 localhost；
- 转发器不打印上游 URL、Header、请求体或原始错误；
- URL、hostname 和 Key 仍额外注册为 GitHub mask。

### 4.3 Secret 权限和仓库写权限成功分离

采用两个 Job：

1. Codex Job：可以使用 Environment Secrets，但只有 `contents: read`；
2. Publish Job：有 `contents: write`，但不引用 Environment，也拿不到中转站 URL、Key 或模型 Secret。

Codex Job 只输出经过 Secret 扫描的最小 patch 和结构化结果，Publish Job 再重新应用和验证。

### 4.4 PR 创建应归属于 ChatGPT Web Supervisor

Publish Job 成功推送了独立分支，但 `GITHUB_TOKEN` 因仓库 Actions 设置无法创建 PR。ChatGPT Web Supervisor 随后通过 GitHub 连接器成功创建 Draft PR `#9`。

正式方案推荐固定为：

```text
GitHub Actions Executor / Codex Thin Worker
→ 修改、验证、提交并 push 工作分支

ChatGPT Web Supervisor
→ 审查分支与 Checks
→ 创建或更新 PR
→ 决定合并与后续阶段
```

这既符合组件职责，也避免为了 Action 自动建 PR 而扩大仓库权限。

### 4.5 Public 泄漏审计通过

独立 `workflow_run` 审计器在主工作流结束后：

- 私下下载完整 workflow logs；
- 搜索 endpoint 原值、去尾斜杠形式、hostname、Key、URL 编码形式、标准和 URL-safe Base64 形式；
- 不打印命中内容；
- 只上传不含 Secret 的审计摘要。

最终有效运行 `29974972105` 的审计结果为 PASS，Issue 为 `#8`。

### 4.6 中断通知最小链路通过

独立 T6 Workflow 故意以 exit code 42 中断，然后自动创建并指派 Issue `#10`：

```text
[SMOKE][T6][run 29975116933] EXPECTED_CONTROLLED_INTERRUPTION_PASS
```

这证明 GitHub 侧可以为 `FAILED`、`BLOCKED`、`WAITING_HUMAN`、超时或 stale 事件产生明确通知记录。最终邮件、浏览器或手机推送是否送达，仍取决于用户 GitHub 通知设置，需要用户做一次终端侧确认。

## 5. 测试中的迭代与集中经验

| 现象 | 根因 | 修复/生产规则 |
|---|---|---|
| T0 首轮 endpoint path 失败 | Secret 保存的是 base URL | Runner 内私下标准化，不要求公开或重填 URL |
| Codex 成功但 verifier 找不到结果 | `output-file` 相对路径按仓库根解析 | 所有 Action 文件路径按仓库根显式声明并测试 |
| Scope Guard 出现 `__pycache__` | Python 默认生成字节码缓存 | Agent Workflow 固定 `PYTHONDONTWRITEBYTECODE=1` |
| Publish push 成功但建 PR 失败 | Actions 未获创建 PR 权限 | Web Supervisor 负责 PR；Action 只 push 分支 |
| 主 Workflow 的预期 T6 被前置失败跳过 | `needs` 成功依赖阻断 | 中断通知测试使用独立 Workflow，不依赖产品链路成功 |

这些规则应在正式迁移时写入集中工程经验库和分层 SOP，而不是只留在聊天或临时日志中。

## 6. Token 说明

本次初次连通和调试过程中，共有三次最小 Codex Action 成功调用，原因是需要校正测试工作流的输出路径和 scope guard；这些属于测试基础设施调试，不是同一业务任务的无限自动重试。

GitHub Artifact 未提供可信的模型 usage 明细，因此本文不虚构实际 Token 数。可采用以下工程预算评估单次正式 Thin Worker：

```text
单次最小任务累计输入：约 15,000–40,000 tokens
单次最小任务输出：约 1,000–4,000 tokens
默认 Codex Session：1
同一任务自动二次 Session：0
```

真实计费和 Token 使用量以中转站后台记录为准。

## 7. 正式迁移结论

T0–T6 已足以支持正式规划，推荐生产基线为：

```text
ChatGPT Web Supervisor
+ GitHub Actions Executor
+ Codex Thin Worker
+ Environment Secrets
+ localhost-only private Responses forwarder
+ read-only Secret job
+ secret-free write job
+ Web Supervisor PR control
+ independent log-leak audit
+ incident Issue notification
```

下一阶段可以开始：

1. 将现有 SOP v2 拆成分层指令；
2. 在正式仓库建立任务状态、计划/结果模板和工程经验库规则；
3. 建立 reusable Codex Thin Worker、Gate、Incident 和 Secret Audit workflows；
4. 用一个真实但低风险的仓库任务做生产薄切片；
5. 通过后再把后续开发任务逐步切换到新执行流。
