import http from "./http";
import type {
  Listing, Paginated, Profile, ScoreDetail, TokenOut, User,
  InsightsResult, NeedMatchResult,
} from "../types";

// ===== Auth =====
export const authApi = {
  register: (data: { phone?: string; email?: string; nickname?: string; password: string }) =>
    http.post<unknown, TokenOut>("/auth/register", data),
  login: (data: { account: string; password: string }) =>
    http.post<unknown, TokenOut>("/auth/login", data),
};

// ===== Profile =====
export const profileApi = {
  list: () => http.get<unknown, Profile[]>("/profiles"),
  get: (id: string) => http.get<unknown, Profile>(`/profiles/${id}`),
  create: (data: Partial<Profile>) => http.post<unknown, Profile>("/profiles", data),
  update: (id: string, data: Partial<Profile>) => http.put<unknown, Profile>(`/profiles/${id}`, data),
  delete: (id: string) => http.delete<unknown, any>(`/profiles/${id}`),
};

// ===== Listings =====
export const listingApi = {
  list: (params: Record<string, any>) =>
    http.get<unknown, Paginated<Listing>>("/listings", { params }),
  get: (id: string) => http.get<unknown, Listing>(`/listings/${id}`),
};

// ===== Scores =====
export const scoreApi = {
  get: (listingId: string) => http.get<unknown, ScoreDetail>(`/scores/${listingId}`),
  recalc: (listingId: string) =>
    http.post<unknown, any>(`/scores/${listingId}/recalculate`),
  ai: (listingId: string, force = false) =>
    http.post<unknown, any>(`/scores/${listingId}/ai-analysis`, null, {
      params: { force },
    }),
  insights: (listingId: string, force = false) =>
    http.post<unknown, any>(`/scores/${listingId}/insights`, null, {
      params: { force },
    }),
};

// ===== Community insights（独立小区测评） =====
export const insightsApi = {
  community: (data: {
    community_name: string;
    city?: string;
    area_name?: string;
    layout?: string;
    price?: number;
    size_sqm?: number;
    floor_info?: string;
    orientation?: string;
    extra_note?: string;
    force?: boolean;
  }) => http.post<unknown, InsightsResult>("/insights/community", data),
  match: (data: {
    description: string;
    city?: string;
    limit?: number;
    force?: boolean;
  }) => http.post<unknown, NeedMatchResult>("/insights/match", data),
};

// ===== Search =====
export const searchApi = {
  search: (params: Record<string, any>) =>
    http.get<unknown, Paginated<Listing>>("/search", { params }),
};

// ===== Recommend =====
export const recommendApi = {
  recommend: (profileId: string, page = 1, pageSize = 20) =>
    http.get<unknown, Paginated<Listing>>("/recommend", {
      params: { profile_id: profileId, page, page_size: pageSize },
    }),
};

// ===== Favorites / Marks =====
export const favoriteApi = {
  list: (category?: string) =>
    http.get<unknown, { items: Listing[]; total: number }>("/favorites", {
      params: category ? { category } : {},
    }),
  add: (listingId: string, category = "待看", note?: string) =>
    http.post<unknown, any>("/favorites", { listing_id: listingId, category, note }),
  remove: (listingId: string) => http.delete<unknown, any>(`/favorites/${listingId}`),
};

export const markApi = {
  create: (listingId: string, markType: string, note?: string) =>
    http.post<unknown, any>("/marks", {
      listing_id: listingId,
      mark_type: markType,
      note,
    }),
};

// ===== Crawl(采集控制) =====
export const crawlApi = {
  platforms: () => http.get<unknown, { platforms: string[] }>("/crawl/platforms"),
  trigger: (params: { platform: string; keywords?: string; max_count?: number }) =>
    http.post<unknown, any>("/crawl/trigger", null, { params }),
  status: (taskId: string) => http.get<unknown, any>(`/crawl/status/${taskId}`),
  listings: (params: { platform: string; limit?: number; only_with_price?: boolean }) =>
    http.get<unknown, { platform: string; total: number; listings: any[] }>("/crawl/listings", { params }),
  ingest: (params: { platform: string; limit?: number }) =>
    http.post<unknown, any>("/crawl/ingest", null, { params }),
};

// ===== Prompts(提示词管理) =====
export const promptApi = {
  getCommunity: () => http.get<unknown, any>("/prompts/community"),
  updateCommunity: (data: { system?: string; user_template?: string }) =>
    http.put<unknown, any>("/prompts/community", data),
  resetCommunity: () => http.post<unknown, any>("/prompts/community/reset"),
};
