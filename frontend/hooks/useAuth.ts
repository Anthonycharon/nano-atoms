"use client";

import { useRouter } from "next/navigation";
import { authApi } from "@/lib/api";
import { useAuthStore } from "@/stores/authStore";

export function useAuth() {
  const router = useRouter();
  const { setAuth, logout, isAuthenticated, user } = useAuthStore();

  const register = async (email: string, password: string) => {
    const { data } = await authApi.register(email, password);
    // 先写入 localStorage，拦截器才能为后续请求附加 token
    localStorage.setItem("nano_token", data.access_token);
    const meRes = await authApi.me();
    setAuth(meRes.data, data.access_token);
    router.push("/dashboard");
  };

  const login = async (email: string, password: string) => {
    const { data } = await authApi.login(email, password);
    // 先写入 localStorage，拦截器才能为后续请求附加 token
    localStorage.setItem("nano_token", data.access_token);
    const meRes = await authApi.me();
    setAuth(meRes.data, data.access_token);
    router.push("/dashboard");
  };

  const logoutAndRedirect = () => {
    logout();
    router.push("/");
  };

  return { register, login, logout: logoutAndRedirect, isAuthenticated, user };
}
