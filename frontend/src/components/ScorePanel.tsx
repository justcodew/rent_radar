import clsx from "clsx";
import type { ScoreDetail } from "../types";
import RiskTag from "./RiskTag";

const SUB_SCORE_LABELS: Record<string, string> = {
  poster_frequency: "发布频率",
  poster_age: "账号年龄",
  poster_diversity: "内容多样性",
  poster_contact_reuse: "联系方式复用",
  image_authenticity: "图片真实性",
  description: "描述详细度",
  price_reasonable: "价格合理性",
  info_completeness: "信息完整度",
};

const SUB_SCORE_MAX: Record<string, number> = {
  poster_frequency: 9,
  poster_age: 7.5,
  poster_diversity: 7.5,
  poster_contact_reuse: 6,
  image_authenticity: 17.5,
  description: 21,
  price_reasonable: 14,
  info_completeness: 17.5,
};

// 子项 key -> evidence 路径（rule_engine.py 中 evidence 结构）
// poster_* 嵌套在 evidence.poster 下；其他直接挂在 evidence 顶层。
const SUB_SCORE_EVIDENCE_PATH: Record<string, string> = {
  poster_frequency: "poster.frequency",
  poster_age: "poster.age",
  poster_diversity: "poster.diversity",
  poster_contact_reuse: "poster.contact_reuse",
  image_authenticity: "image_authenticity",
  description: "description_quality",
  price_reasonable: "price_reasonableness",
  info_completeness: "info_completeness",
};

function getNestedEvidence(evidence: any, path: string): any {
  if (!evidence || !path) return undefined;
  return path.split(".").reduce((o, k) => (o == null ? undefined : o[k]), evidence);
}

export default function ScorePanel({ score }: { score: ScoreDetail }) {
  return (
    <div className="card p-5 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-xs text-gray-500">好房指数</div>
          <div className="flex items-baseline gap-2">
            <span className="text-4xl font-bold text-gray-900">{score.general_score}</span>
            <span className="text-sm text-gray-500">/ 100</span>
          </div>
          <div className="mt-1">
            <span className="badge bg-brand-100 text-brand-700">{score.level}</span>
            <span className="ml-2 text-amber-400">
              {"★".repeat(score.stars)}
              <span className="text-gray-200">{"★".repeat(5 - score.stars)}</span>
            </span>
          </div>
        </div>
        <div className="text-right text-sm">
          <div className="text-gray-500">发布者 / 房源</div>
          <div className="font-semibold">
            <span className="text-blue-600">{score.poster_score}</span>
            <span className="text-gray-400 mx-1">/</span>
            <span className="text-emerald-600">{score.listing_score}</span>
          </div>
          <div className="text-xs text-gray-400 mt-1">评分版本 {score.score_version}</div>
        </div>
      </div>

      {/* 风险标签 */}
      {score.risk_tags?.length > 0 && (
        <div>
          <div className="text-sm text-gray-600 mb-2">风险提示</div>
          <div className="flex flex-wrap gap-2">
            {score.risk_tags.map((t) => <RiskTag key={t} tag={t} />)}
          </div>
        </div>
      )}

      {/* 子项分数 */}
      <div>
        <div className="text-sm text-gray-600 mb-3">评分细节（点击查看依据）</div>
        <div className="space-y-3">
          {Object.entries(SUB_SCORE_LABELS).map(([key, label]) => {
            const val = score.sub_scores?.[key] ?? 0;
            const max = SUB_SCORE_MAX[key] || 1;
            const pct = Math.min(100, (val / max) * 100);
            const ev = getNestedEvidence(score.evidence, SUB_SCORE_EVIDENCE_PATH[key]);

            return (
              <div key={key}>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-700">{label}</span>
                  <span className="text-gray-500">
                    {val} <span className="text-xs text-gray-400">/ {max}</span>
                  </span>
                </div>
                <div className="mt-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                  <div
                    className={clsx(
                      "h-full rounded-full",
                      pct >= 70 ? "bg-emerald-500" : pct >= 40 ? "bg-amber-500" : "bg-red-400"
                    )}
                    style={{ width: `${pct}%` }}
                  />
                </div>
                {ev?.level && (
                  <div className="text-xs text-gray-500 mt-0.5">{ev.level}</div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* 评分依据 */}
      {score.evidence && (
        <details className="border-t pt-3">
          <summary className="cursor-pointer text-sm text-brand-600">查看完整评分依据</summary>
          <pre className="mt-2 text-xs bg-gray-50 p-3 rounded-lg overflow-auto max-h-80">
{JSON.stringify(score.evidence, null, 2)}
          </pre>
        </details>
      )}
    </div>
  );
}
