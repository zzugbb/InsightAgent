import Link from "next/link";
import { GitFork, Waypoints } from "lucide-react";
import { repository } from "../lib/labels";
export function Header() {
  return (
    <header className="site-header">
      <div className="header-inner">
        <Link className="brand" href="/" aria-label="InsightAgent 首页">
          <Waypoints size={25} strokeWidth={1.7} />
          <span>InsightAgent</span>
        </Link>
        <nav aria-label="主导航">
          <Link href="/demo/">案例体验</Link>
          <a href={repository} target="_blank" rel="noopener noreferrer">
            <GitFork size={17} />
            源码<span className="sr-only">（新窗口）</span>
          </a>
        </nav>
      </div>
    </header>
  );
}
export function Footer() {
  return (
    <footer className="site-footer">
      <span>InsightAgent · 执行可观察，依据可复核。</span>
      <span>公开合成案例 · 静态回放 · MIT</span>
    </footer>
  );
}
