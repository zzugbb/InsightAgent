# 目标环境部署与恢复演练工具包

## 状态

**待外部验收（缺目标环境）**。VM 上仅建议对**一次性临时 Compose 项目**执行备份恢复演练；不要在未备份的情况下重建或删除现有 Chroma/PostgreSQL 开发容器。

## 组件

| 脚本 | 作用 |
| --- | --- |
| `scripts/check_pilot_deploy_config.py` | 试点配置只读预检（既有） |
| `scripts/pilot_compose.py` | 试点 Compose 启停（既有，需仓库外 env） |
| `scripts/smoke_pilot_compose.py` | 隔离 mock 栈演练（既有） |
| `scripts/pilot_https_probe.sh` | 只读 HTTPS/health/TLS 证书日期探测 |
| `scripts/pilot_backup_restore_drill.sh` | 对**显式 `--project`** 做 stop→backup→restore 并输出耗时 JSON |
| `scripts/local_stack_snapshot.py` | 离线卷快照（既有，见 [local-stack-backup-restore.md](local-stack-backup-restore.md)） |

## Chroma 数据路径警告

旧容器可能挂载 `/chroma/chroma`，实际数据或在容器内 `/data`。当前 Compose 已改为卷挂载 `/data`。**未备份禁止**删除或重建现有 `8001` Chroma 容器/卷。

## 部署→升级→回滚（目标环境具备后）

1. `backend/.venv/bin/python scripts/check_pilot_deploy_config.py --env-file <外部配置>`
2. `backend/.venv/bin/python scripts/pilot_compose.py up --env-file <外部配置> --project <固定名>`
3. `scripts/pilot_https_probe.sh --url https://<目标域名>`
4. 记录镜像摘要、配置校验码与 health 结果。
5. 升级：替换镜像摘要后 `pilot_compose.py up`（先备份，见下）。
6. 回滚：恢复上一镜像摘要并 `up`；失败则按备份恢复卷。

## 备份恢复演练（临时项目）

```bash
# 仅新建项目名，勿用开发默认项目
bash scripts/pilot_backup_restore_drill.sh \
  --project insightagent-drill-$(date +%Y%m%d) \
  --snapshot-dir /tmp/insightagent-drill-snapshot
```

干跑：`--dry-run`。输出 JSON 含 `backup_seconds` / `restore_seconds`，用于**估算** RPO/RTO，不等于目标环境承诺。

## RPO/RTO 与责任人记录模板

| 字段 | 值 |
| --- | --- |
| 环境名称 | |
| 演练日期 | |
| 责任人 | |
| 备份策略（频率/保留） | |
| 实测 RPO（数据最大可接受丢失） | |
| 实测 RTO（恢复耗时） | |
| PostgreSQL 备份路径/工具 | |
| Chroma 备份路径（确认 `/data`） | |
| 回滚决策人 | |
| 结论 | 通过 / 不通过 / 待重试 |

将填写结果保存在目标环境 runbook，**不要**把含密钥的配置提交仓库。
