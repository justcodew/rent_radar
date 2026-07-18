import { Link } from "react-router-dom";
import dayjs from "dayjs";
import type { Listing } from "../types";
import ScoreBadge from "./ScoreBadge";
import RiskTag from "./RiskTag";

interface Props {
  listing: Listing;
  matchScore?: number;
}

export default function ListingCard({ listing, matchScore }: Props) {
  const cover = listing.image_urls?.[0];
  const src = sourceMeta(listing.source);
  return (
    <Link
      to={`/listings/${listing.id}`}
      className="card overflow-hidden hover:shadow-md transition-shadow block"
    >
      <div className="aspect-video bg-gray-100 relative">
        {cover ? (
          <img src={cover} alt="" className="w-full h-full object-cover" />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-gray-300 text-sm">
            暂无图片
          </div>
        )}
        <div className="absolute top-2 left-2">
          <ScoreBadge score={listing.general_score} size="md" />
        </div>
        {matchScore != null && (
          <div className="absolute bottom-2 right-2 bg-white/95 px-2 py-1 rounded-md text-xs">
            <span className="text-gray-500">匹配</span>
            <span className="ml-1 font-semibold text-brand-600">{matchScore}</span>
          </div>
        )}
      </div>
      <div className="p-3">
        <div className="flex items-start justify-between gap-2">
          <h3 className="font-semibold text-gray-800 line-clamp-2 text-sm leading-5">
            {listing.title || "（无标题）"}
          </h3>
          {listing.price != null && (
            <div className="text-brand-600 font-bold whitespace-nowrap">
              ¥{listing.price}
              <span className="text-xs text-gray-400 font-normal">/月</span>
            </div>
          )}
        </div>

        <div className="mt-2 flex flex-wrap gap-1 text-xs text-gray-500">
          {listing.area_name && <span>{listing.area_name}</span>}
          {listing.layout && <span>· {listing.layout}</span>}
          {listing.size_sqm != null && <span>· {listing.size_sqm}㎡</span>}
          {listing.orientation && <span>· {listing.orientation}</span>}
        </div>

        {listing.risk_tags && listing.risk_tags.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1">
            {listing.risk_tags.slice(0, 3).map((t) => (
              <RiskTag key={t} tag={t} />
            ))}
          </div>
        )}

        {/* 中介标记 */}
        {listing.is_agent && (
          <div className="mt-2">
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-orange-100 text-orange-700">
              🏷️ {(listing as any).agent_level || "疑似中介"}
            </span>
          </div>
        )}
        {!listing.is_agent && (listing as any).agent_level && (listing as any).agent_level !== "个人房东" && (
          <div className="mt-2">
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs text-gray-500 bg-gray-100">
              ℹ️ {(listing as any).agent_level}
            </span>
          </div>
        )}

        <div className="mt-2 flex items-center justify-between text-xs text-gray-400">
          <span className={`inline-flex items-center gap-1 ${src.color}`}>
            <span>{src.icon}</span>
            <span>{src.label}</span>
          </span>
          {listing.posted_at && <span>{dayjs(listing.posted_at).format("MM-DD HH:mm")}</span>}
        </div>
      </div>
    </Link>
  );
}

function sourceMeta(source?: string) {
  switch (source) {
    case "douban":
      return { icon: "🎬", label: "豆瓣", color: "text-emerald-600" };
    case "xiaohongshu":
      return { icon: "📕", label: "小红书", color: "text-rose-500" };
    default:
      return { icon: "📄", label: source || "未知", color: "text-gray-400" };
  }
}
