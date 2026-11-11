# Issue tracker: Plane

在 [Watch for Me Plane 项目](https://app.plane.so/mian-personal-workspace/projects/bc8d7a2c-5671-4283-bffe-db1aa87cea8e/issues/) 追踪任务与讨论。

- Workspace：`mian-personal-workspace`
- Project ID：`bc8d7a2c-5671-4283-bffe-db1aa87cea8e`
- 工作项前缀：`WFM`
- 仓库：[QinMian5/watch-for-me](https://github.com/QinMian5/watch-for-me)

## 操作

使用配置好的 Plane MCP；先核对 workspace，项目操作传入上述 ID，凭据保留在仓库外。

- 创建前查询已有工作项，避免重复。新任务用 `workitem create`，正文写清范围和完成标准。
- 用 `workitem retrieve_by_identifier` 读取 `WFM-N`，按需读取评论和依赖。
- 开始实施前，用 `state list` 获取 In Progress 的 ID，更新并读回状态；结束时记录真实验证结果，再按完成情况设 Done 或 Cancelled。
- 用 `workitem_comment create` 记录有价值的进展、结论和阻碍。更新正文前先读取，保留其他会话的内容。
- `parent` 表达子任务，原生 `blocked_by` 表达实际依赖。
- 标签从服务读取 ID，用 `manage_label` 增减，保留无关标签。

Plane 的 HTML 使用单行字符串，以 `<p>`、`<ul>` 等表达结构，不保留空段落。保存后读回正文与关联。

## Wayfinding operations

- **地图**：带 `wayfinder:map` 标签的工作项；正文含 Destination、Notes、Decisions so far、Not yet specified、Out of scope。
- **票据**：地图的子工作项（`parent` 为地图 ID），带 `wayfinder:research`、`wayfinder:prototype`、`wayfinder:grilling` 或 `wayfinder:task` 之一。正文只写 `## Question`。
- **阻塞**：用 `workitem_relation create`，`relation_type: blocked_by`；先建票、再第二遍接线。
- **认领**：开始前用 `workitem manage_assignee` 把票分配给驱动地图的人（qinmian2023，member ID `ba375491-963b-4779-89b4-9dd43b6e3649`），并把状态设为 In Progress。未分配的开放票即未认领。
- **前沿查询**：`workitem list`，PQL 取地图的子项且状态组为开放、无负责人；再对每张票 `workitem_relation list`，剔除仍有未关闭 `blocked_by` 的票。
- **解决**：用 `workitem_comment create` 发布解决评论，状态设 Done；超出范围的票设 Cancelled。然后读回地图正文，在 Decisions so far 追加一行 `[票名](链接)：要点`，保留其他会话的改动。
- **资产**：调研结论写在 `research/<name>` 分支的 Markdown 里，并在票的评论中给出分支与文件路径；原型等资产同样只链接、不粘贴。

## 协作与标识

范围、决定与待完成工作留在 Plane，代码、PR 与交付验证留在 GitHub。相关提交标题包含完整 Plane 标识，例如 `WFM-2`。
