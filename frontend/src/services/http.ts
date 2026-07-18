import axios, { AxiosError, AxiosInstance } from "axios";
import type { ApiResponse } from "../types";
import { useAuthStore } from "../stores/auth";

const http: AxiosInstance = axios.create({
  baseURL: "/api/v1",
  timeout: 300000, // 5 分钟(采集等长操作需要)
});

// 请求拦截：自动加 token
http.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// 响应拦截：统一解包 + 错误处理
http.interceptors.response.use(
  (response) => {
    const body = response.data as ApiResponse;
    if (body && typeof body === "object" && "code" in body) {
      if (body.code === 0) {
        return body.data;
      }
      // 业务错误
      return Promise.reject(new Error(body.message || "请求失败"));
    }
    return response.data;
  },
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      useAuthStore.getState().logout();
      if (!window.location.pathname.startsWith("/login")) {
        window.location.href = "/login";
      }
    }
    const msg =
      (error.response?.data as ApiResponse)?.message ||
      error.message ||
      "网络错误";
    return Promise.reject(new Error(msg));
  }
);

export default http;
