import { Segmented, Select, Tag } from "antd";
import { useState } from "react";

import type { Messages } from "../../../lib/i18n/types";

import type { RagHit } from "./types";
import {
  filterRagHitsBySource,
  filterRagHitsByRecallQuality,
  formatRagRecallDistance,
  type RagRecallQualityFilter,
  resolveRagHitAttributionItems,
  resolveRagQueryInsight,
  resolveRagRecallQuality,
  resolveRagSourceFilterOptions,
} from "./runtime-debug-modal-utils";

type RuntimeDebugRagResultsProps = {
  hitCount: number;
  hits: RagHit[];
  t: Messages;
};

export function RuntimeDebugRagResults({
  hitCount,
  hits,
  t,
}: RuntimeDebugRagResultsProps) {
  const [qualityFilter, setQualityFilter] =
    useState<RagRecallQualityFilter>("all");
  const [sourceFilter, setSourceFilter] = useState("all");
  const queryInsight = resolveRagQueryInsight(hits);
  const sourceOptions = resolveRagSourceFilterOptions(hits);
  const activeSourceFilter =
    sourceFilter === "all" ||
    sourceOptions.some((option) => option.source === sourceFilter)
      ? sourceFilter
      : "all";
  const qualityFilteredHits = filterRagHitsByRecallQuality(hits, qualityFilter);
  const visibleHits = filterRagHitsBySource(
    qualityFilteredHits,
    activeSourceFilter,
  );

  return (
    <div
      className="memory-query-results"
      aria-live="polite"
      data-testid="inspector-rag-query-results"
    >
      <p className="memory-query-hits-label">
        {t.inspector.rag.queryHits(hitCount)}
      </p>
      {hitCount <= 0 ? (
        <p className="panel-note panel-note--muted">
          {t.inspector.rag.queryEmpty}
        </p>
      ) : (
        <>
          {queryInsight ? (
            <div
              className="rag-query-insight"
              data-testid="inspector-rag-query-insight"
            >
              <span className="rag-query-insight-label">
                {t.inspector.rag.queryInsightLabel}
              </span>
              {queryInsight.bestDistance ? (
                <span className="rag-query-insight-chip">
                  {t.inspector.rag.bestDistanceLabel}
                  <code>{queryInsight.bestDistance}</code>
                </span>
              ) : null}
              {queryInsight.bestQuality ? (
                <Tag
                  className={`rag-recall-quality-tag rag-recall-quality-tag--${queryInsight.bestQuality.tone}`}
                >
                  {t.inspector.rag[queryInsight.bestQuality.labelKey]}
                </Tag>
              ) : null}
              {queryInsight.topSource ? (
                <span className="rag-query-insight-chip">
                  {t.inspector.rag.topSourceLabel}
                  <code>{queryInsight.topSource}</code>
                </span>
              ) : null}
              <span
                className="rag-query-insight-chip"
                data-testid="inspector-rag-quality-mix"
              >
                {t.inspector.rag.qualityMixLabel}
                <code>
                  {[
                    `${t.inspector.rag.recallQualityStrong} ${queryInsight.qualityCounts.strong}`,
                    `${t.inspector.rag.recallQualityMedium} ${queryInsight.qualityCounts.medium}`,
                    `${t.inspector.rag.recallQualityWeak} ${queryInsight.qualityCounts.weak}`,
                  ].join(" · ")}
                </code>
              </span>
              <span className="rag-query-insight-chip">
                {t.inspector.rag.sourceCoverageLabel(
                  queryInsight.sourceCount,
                  queryInsight.documentCount,
                )}
              </span>
              {queryInsight.guidanceKey ? (
                <span
                  className="rag-query-insight-guidance"
                  data-testid="inspector-rag-query-guidance"
                >
                  {t.inspector.rag[queryInsight.guidanceKey]}
                </span>
              ) : null}
            </div>
          ) : null}
          {queryInsight ? (
            <div
              className="rag-quality-filter"
              data-testid="inspector-rag-quality-filter"
            >
              <span className="rag-quality-filter-label">
                {t.inspector.rag.qualityFilterLabel}
              </span>
              <Segmented
                size="small"
                value={qualityFilter}
                aria-label={t.inspector.rag.qualityFilterLabel}
                onChange={(value) =>
                  setQualityFilter(value as RagRecallQualityFilter)
                }
                options={[
                  {
                    label: t.inspector.rag.qualityFilterAll,
                    value: "all",
                  },
                  {
                    label: `${t.inspector.rag.recallQualityStrong} ${queryInsight.qualityCounts.strong}`,
                    value: "strong",
                  },
                  {
                    label: `${t.inspector.rag.recallQualityMedium} ${queryInsight.qualityCounts.medium}`,
                    value: "medium",
                  },
                  {
                    label: `${t.inspector.rag.recallQualityWeak} ${queryInsight.qualityCounts.weak}`,
                    value: "weak",
                  },
                ]}
              />
              <span
                className="rag-quality-filter-count"
                data-testid="inspector-rag-quality-filter-count"
              >
                {t.inspector.rag.qualityFilterShowing(
                  visibleHits.length,
                  hits.length,
                )}
              </span>
            </div>
          ) : null}
          {queryInsight && sourceOptions.length > 0 ? (
            <div
              className="rag-source-filter"
              data-testid="inspector-rag-source-filter"
            >
              <span className="rag-source-filter-label">
                {t.inspector.rag.sourceFilterLabel}
              </span>
              <Select
                size="small"
                value={activeSourceFilter}
                aria-label={t.inspector.rag.sourceFilterLabel}
                className="rag-source-filter-select"
                onChange={setSourceFilter}
                options={[
                  {
                    label: t.inspector.rag.sourceFilterAll,
                    value: "all",
                  },
                  ...sourceOptions.map((option) => ({
                    label: t.inspector.rag.sourceFilterOption(
                      option.source,
                      option.count,
                    ),
                    value: option.source,
                  })),
                ]}
              />
            </div>
          ) : null}
          {visibleHits.length === 0 ? (
            <p className="panel-note panel-note--muted">
              {t.inspector.rag.qualityFilterEmpty}
            </p>
          ) : (
            <ul className="memory-query-hit-list">
              {visibleHits.map((hit) => {
                const metaKeys = Object.keys(hit.metadata || {});
                const recallDistance = formatRagRecallDistance(hit.distance);
                const recallQuality = resolveRagRecallQuality(hit.distance);
                const attributionItems = resolveRagHitAttributionItems(
                  hit.metadata,
                );

                return (
                  <li key={hit.id} className="memory-query-hit-item">
                    <pre className="memory-query-hit-doc">{hit.content}</pre>
                    {attributionItems.length > 0 ? (
                      <div
                        className="rag-hit-attribution"
                        data-testid="inspector-rag-hit-attribution"
                      >
                        <span className="rag-hit-attribution-label">
                          {t.inspector.rag.hitAttributionLabel}
                        </span>
                        {attributionItems.map((item) => (
                          <span
                            key={`${item.labelKey}:${item.value}`}
                            className="rag-hit-attribution-chip"
                          >
                            <span>{t.inspector.rag[item.labelKey]}</span>
                            <code>{item.value}</code>
                          </span>
                        ))}
                      </div>
                    ) : null}
                    {metaKeys.length > 0 ? (
                      <pre className="memory-query-hit-meta">
                        {t.inspector.rag.hitMetadataLabel}:{"\n"}
                        {JSON.stringify(hit.metadata, null, 2)}
                      </pre>
                    ) : null}
                    {recallDistance ? (
                      <div
                        className="rag-recall-quality-row"
                        data-testid="inspector-rag-recall-quality"
                      >
                        <span className="memory-query-hit-dist">
                          {t.inspector.rag.distanceLabel}: {recallDistance}
                        </span>
                        {recallQuality ? (
                          <Tag
                            className={`rag-recall-quality-tag rag-recall-quality-tag--${recallQuality.tone}`}
                          >
                            {t.inspector.rag[recallQuality.labelKey]}
                          </Tag>
                        ) : null}
                        <span className="rag-recall-quality-hint">
                          {t.inspector.rag.recallDistanceHint}
                        </span>
                      </div>
                    ) : null}
                  </li>
                );
              })}
            </ul>
          )}
        </>
      )}
    </div>
  );
}
