# Stage Detail JSON Plan

1. 扩展后端模型与 schema
   - 为 `ResearchTaskStage` 增加 `detail_json`
   - 更新 API response schema

2. 扩展 stage 持久化
   - `running` stage 写入最小 `detail_json`
   - `completed/fallback/error` stage 写入结构化详情

3. 扩展工作流节点输出
   - 为价格研究节点和商业分析节点补充 `detail_json`
   - 为 LLM fallback/error stage 附带 provider / prompt / result 摘要

4. 更新前端详情面板
   - `查看详情` 优先渲染 `detail_json`
   - 无结构化详情时回退到 `stage.message`

5. 验证
   - 后端测试覆盖 stage 持久化与 API 返回
   - 前端测试覆盖详情展开显示结构化 JSON
   - 执行 Alembic migration 并重启服务
