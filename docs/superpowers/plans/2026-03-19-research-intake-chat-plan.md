# Research Intake Chat Plan

1. 新增后端 schema
- `IntakeMessage`
- `ResearchRequirementDraft`
- `ResearchIntakeChatRequest`
- `ResearchIntakeChatResponse`

2. 新增后端 service
- `research_intake_service.py`
- 负责：
  - 构造 intake prompt
  - 调 LLM
  - fallback 抽取
  - 统一输出结构

3. 新增后端接口
- `POST /api/research-intake/chat`

4. 前端接入 intake API
- 新增 intake 类型
- 新增 `chatResearchIntake(...)`

5. 前端状态改造
- 在 `App.tsx` 维护：
  - `intakeMessages`
  - `draftRequirement`
  - `missingFields`
  - `intakeReadyToStart`
  - `intakeFinalPrompt`

6. 前端 UI 改造
- 将“发起调研”卡片改为：
  - 对话消息区
  - 消息输入框
  - `发送`
  - `开始调研`
  - 当需求已明确时，由 assistant 对话消息提示用户开始调研

7. 验证
- `backend/tests/test_api.py`
- `frontend/tests/app.test.tsx`
- `npm run build`
