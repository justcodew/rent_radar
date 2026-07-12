// API 统一响应格式
export interface ApiResponse<T = any> {
  code: number;
  message: string;
  data: T;
  trace_id?: string;
}

export interface Paginated<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  has_more: boolean;
}

export interface User {
  id: string;
  phone?: string;
  email?: string;
  nickname?: string;
  created_at: string;
}

export interface TokenOut {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
}

export interface CommuteItem {
  location: string;
  mode?: string;
  max_time: number;
  weight?: number;
}

export interface Profile {
  id: string;
  user_id: string;
  name: string;
  city: string;
  budget_min: number;
  budget_max: number;
  occupants: number;
  move_in?: string;
  areas: string[];
  layouts: string[];
  rent_type?: string;
  size_range: number[];
  commute: CommuteItem[];
  environment: Record<string, any>;
  keywords: { must_have?: string[]; exclude?: string[] };
  preferences: Record<string, any>;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface Listing {
  id: string;
  source: string;
  source_url?: string;
  poster_id?: string;
  poster_name?: string;
  title?: string;
  content: string;
  price?: number;
  area_name?: string;
  location_detail?: string;
  layout?: string;
  size_sqm?: number;
  floor_info?: string;
  orientation?: string;
  contact_info?: Record<string, any>;
  image_urls: string[];
  posted_at?: string;
  created_at: string;
  // 评分相关（可选）
  general_score?: number;
  risk_tags?: string[];
  match_score?: number;
  personalized_score?: number;
  match_evidence?: Record<string, any>;
  evidence?: Record<string, any>;
  favorite_category?: string;
  favorited_at?: string;
}

export interface ScoreDetail {
  listing_id: string;
  general_score: number;
  level: string;
  stars: number;
  poster_score: number;
  listing_score: number;
  sub_scores: Record<string, number>;
  risk_tags: string[];
  evidence: Record<string, any>;
  ai_evidence?: any;
  ai_insights?: InsightsResult | null;
  score_version: string;
  calculated_at: string;
}

export interface SurroundingsItem {
  name: string;
  walk_min: number;
  type?: string;
  level?: string;
  line?: string;
  confidence?: number;
}

export interface Surroundings {
  subway?: SurroundingsItem[];
  school?: SurroundingsItem[];
  hospital?: SurroundingsItem[];
  mall?: SurroundingsItem[];
}

export interface InsightsResult {
  community_profile?: string;
  surroundings?: Surroundings;
  surroundings_confidence?: number;
  pros?: string[];
  cons?: string[];
  price_verdict?: string;
  tips?: string[];
  recommendation?: string;
  summary?: string;
  confidence?: number;
  area_avg_price?: number | null;
  model?: string;
  analyzed_at?: string;
  estimated_cost_cny?: number;
  from_cache?: boolean;
  skipped?: boolean;
  reason?: string;
}

export interface ExtractedNeed {
  budget_min?: number | null;
  budget_max?: number | null;
  areas?: string[];
  layouts?: string[];
  size_min?: number | null;
  size_max?: number | null;
  commute_target?: string;
  commute_max_min?: number | null;
  commute_mode?: string;
  must_have?: string[];
  exclude?: string[];
  lifestyle?: string;
}

export interface CommunityRecommendation {
  name: string;
  area?: string;
  est_price_range?: string;
  reason?: string;
  highlights?: string[];
  watch_outs?: string[];
}

export interface NeedMatchResult {
  extracted?: ExtractedNeed;
  communities?: CommunityRecommendation[];
  listings?: Listing[];
  city?: string;
  description?: string;
  model?: string;
  analyzed_at?: string;
  estimated_cost_cny?: number;
  from_cache?: boolean;
  skipped?: boolean;
  reason?: string;
}
