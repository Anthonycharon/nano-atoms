"use client";

import { useEffect, useRef } from "react";
import { useWorkspaceStore } from "@/stores/workspaceStore";
import { AGENT_META } from "@/types/agent";
import type { WsMessage } from "@/types/agent";

const WS_BASE = process.env.NEXT_PUBLIC_WS_URL || "ws://127.0.0.1:8000";

export function useWebSocket(projectId: number | null) {
  const wsRef = useRef<WebSocket | null>(null);
  const { updateAgentStatus, setGenerationStatus, setCurrentVersion, addMessage } =
    useWorkspaceStore();

  useEffect(() => {
    if (!projectId) return;

    let active = true;
    const ws = new WebSocket(`${WS_BASE}/ws/projects/${projectId}/generation`);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      if (!active) return;
      try {
        const msg: WsMessage = JSON.parse(event.data);

        if (msg.type === "agent_status") {
          updateAgentStatus(msg.agent, msg.status, msg.summary);

          if (msg.status === "done") {
            const label = AGENT_META[msg.agent].label;
            const text = msg.summary
              ? `**${label}** 已完成：${msg.summary}`
              : `**${label}** 已完成`;
            addMessage("assistant", text);
          } else if (msg.status === "error") {
            const label = AGENT_META[msg.agent].label;
            const text = msg.summary
              ? `**${label}** 遇到问题：${msg.summary}`
              : `**${label}** 遇到问题，已跳过该步骤`;
            addMessage("assistant", text);
          }
        } else if (msg.type === "generation_status") {
          setGenerationStatus(
            msg.status === "completed"
              ? "completed"
              : msg.status === "failed"
                ? "failed"
                : "running"
          );

          if (msg.version_id && msg.status === "completed") {
            setCurrentVersion(msg.version_id);
            addMessage("assistant", "应用生成完成，可以在右侧预览和查看文件。");
          } else if (msg.status === "failed") {
            const errText = msg.error
              ? `应用生成失败：${msg.error}`
              : "应用生成失败，请稍后重试。";
            addMessage("assistant", errText);
          }
        }
      } catch {
        // Ignore non-JSON websocket payloads such as heartbeat responses.
      }
    };

    const pingInterval = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send("ping");
      }
    }, 30000);

    return () => {
      active = false;
      clearInterval(pingInterval);
      ws.close();
    };
  }, [
    projectId,
    updateAgentStatus,
    setGenerationStatus,
    setCurrentVersion,
    addMessage,
  ]);

  return wsRef;
}
