import type { Metadata } from "next";
import { Header, Footer } from "../components/site-shell";
import "./globals.css";
export const metadata: Metadata = {
  title: {
    default: "InsightAgent · 可视化 AI Agent 工作台",
    template: "%s · InsightAgent",
  },
  description:
    "查看 AI Agent 如何检索知识、调用工具和生成回答。通过预录案例交互回放，复核执行轨迹与引用依据。",
};
export default function Layout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN">
      <body>
        <a className="skip-link" href="#main">
          跳转到主要内容
        </a>
        <Header />
        {children}
        <Footer />
      </body>
    </html>
  );
}
