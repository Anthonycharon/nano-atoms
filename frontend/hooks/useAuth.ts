"use client";

import { useRouter } from "next/navigation";
import { authApi } from "@/lib/api";
import { useAuthStore } from "@/stores/authStore";

export function useAuth() {
  const router = useRouter();
  const { setAuth, logout, isAuthenticated, user } = useAuthStore();

  const register = async (
    email: string,
    password: string,
    verificationToken: string,
    verificationCode: string
  ) => {
    const { data } = await authApi.register(email, password, verificationToken, verificationCode);
    localStorage.setItem("nano_token", data.access_token);
    const meRes = await authApi.me();
    setAuth(meRes.data, data.access_token);
    router.push("/dashboard");
  };

  const login = async (
    email: string,
    password: string,
    captchaToken: string,
    captchaAnswer: string
  ) => {
    const { data } = await authApi.login(email, password, captchaToken, captchaAnswer);
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
