import type { Metadata } from "next";
import { ReplayWorkbench } from "../../components/replay-workbench";
export const metadata: Metadata = { title: "案例体验" };
export default function DemoPage() {
  return (
    <main id="main" className="demo-page">
      <ReplayWorkbench />
    </main>
  );
}
