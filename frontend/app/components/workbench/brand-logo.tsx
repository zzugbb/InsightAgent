/**
 * InsightAgent 品牌符号：左侧对话气泡 + 右侧轨迹节点，体现「对话为主、执行在轨迹中展开」。
 * 使用 currentColor，随侧栏/主题着色。
 */
type BrandLogoProps = {
  className?: string;
  /** 默认 40（展开侧栏）；折叠窄条用 28 */
  size?: number;
  /** 装饰性图标时隐藏无障碍树 */
  decorative?: boolean;
  /** 非装饰时作为图形 accessible name */
  title?: string;
};

export function BrandLogo({
  className,
  size = 40,
  decorative = true,
  title = "InsightAgent",
}: BrandLogoProps) {
  return (
    <svg
      className={className}
      width={size}
      height={size}
      viewBox="0 0 40 40"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden={decorative ? true : undefined}
      role={decorative ? undefined : "img"}
      aria-label={decorative ? undefined : title}
    >
      {!decorative ? <title>{title}</title> : null}
      {/* 对话气泡 */}
      <path
        d="M10 9h14.5a3.5 3.5 0 0 1 3.5 3.5v7.5a3.5 3.5 0 0 1-3.5 3.5h-6.2l-3.3 3.8V23.5H10a3.5 3.5 0 0 1-3.5-3.5V12.5A3.5 3.5 0 0 1 10 9Z"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinejoin="round"
      />
      {/* 轨迹：节点与连线 */}
      <circle cx="29" cy="11" r="2.25" fill="currentColor" />
      <path
        d="M29 13.5v6"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      />
      <circle cx="29" cy="22" r="2.25" fill="currentColor" />
      <path
        d="M29 24.5v6"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      />
      <circle cx="29" cy="31" r="2.25" fill="currentColor" />
      {/* 气泡内高光：暗示「洞察」 */}
      <circle cx="15" cy="16" r="2" fill="currentColor" opacity="0.35" />
    </svg>
  );
}
