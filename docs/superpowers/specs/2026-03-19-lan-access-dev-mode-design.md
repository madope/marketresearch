# 局域网访问开发模式设计

## 目标

在不改变默认本地开发行为的前提下，增加一套可选的局域网访问启动方式，让同一局域网内的其他设备可以访问前端页面并正常调用后端接口。

## 方案

- 保留默认前端启动命令 `npm run dev`，继续绑定 `127.0.0.1`
- 新增前端启动命令 `npm run dev:lan`，绑定 `0.0.0.0`
- 将前端默认 API 地址改为相对路径 `/api`
- 由 Vite 开发服务器代理 `/api` 到本机后端 `http://127.0.0.1:8000`

## 设计理由

- 默认模式不变，避免日常开发时无意暴露服务
- 局域网模式只需要开放前端端口，后端仍可保持本机监听
- 通过相对路径和 Vite 代理，局域网访问、部署到 Nginx、以及本地开发都能共用同一套前端 API 配置

## 影响范围

- `frontend/package.json`
- `frontend/vite.config.ts`
- `frontend/vite.config.js`
- `frontend/src/features/research/api.ts`
- `README.md`
