"""
WebSocket 端点：实时推送 Agent 执行状态。
客户端连接 /ws/projects/{project_id}/generation 后，
生成任务通过 ConnectionManager.broadcast 推送状态变更。
"""
import asyncio
import json
from collections import defaultdict
from typing import Dict, List

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(tags=["websocket"])


class ConnectionManager:
    """管理 WebSocket 连接池，支持按 project_id 分组广播。"""

    def __init__(self):
        # {project_id: [WebSocket, ...]}
        self._connections: Dict[int, List[WebSocket]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, project_id: int) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections[project_id].append(websocket)

    async def disconnect(self, websocket: WebSocket, project_id: int) -> None:
        async with self._lock:
            conns = self._connections.get(project_id, [])
            if websocket in conns:
                conns.remove(websocket)

    async def broadcast(self, project_id: int, message: dict) -> None:
        """向该项目的所有连接推送消息，断开的连接自动清理。"""
        dead: List[WebSocket] = []
        data = json.dumps(message, ensure_ascii=False)

        for ws in list(self._connections.get(project_id, [])):
            try:
                await ws.send_text(data)
            except Exception:
                dead.append(ws)

        # 清理断开连接
        if dead:
            async with self._lock:
                for ws in dead:
                    try:
                        self._connections[project_id].remove(ws)
                    except ValueError:
                        pass


# 全局单例
manager = ConnectionManager()


@router.websocket("/ws/projects/{project_id}/generation")
async def generation_ws(websocket: WebSocket, project_id: int):
    await manager.connect(websocket, project_id)
    try:
        while True:
            # 保持连接，接收心跳 ping
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(websocket, project_id)
